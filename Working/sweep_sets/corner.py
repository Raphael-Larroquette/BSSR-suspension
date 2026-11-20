#!/usr/bin/env python3
"""
Quasi-static steady-state corner: the rack and wheel travels of a constant-speed turn.

A sweep with a `corner:` block in run.yaml is not generated from ranges. For each
step of a curvature ramp at constant speed, this module works out the rack
position and the two front wheel travels that hold the car in steady circular
motion. It returns an ORDINARY sweep spec with explicit `values:` lists for those
three targets, so the solve, CSV, report, plots and animation are exactly those
of any other sweep (tasks.py), and the optimiser solves the same spec for each
candidate (opt/solve.py).

    from corner import parse_settings, load_vehicle, resolve
    result = resolve(suspension, geometry_data, vehicle, settings)
    result.spec      -> {"version": 1, "steps": N, "targets": [...]}
    result.rows      -> one dict per step (accelerations, loads, iterations)
    result.warnings  -> reader-ready strings (wheel lift, grip, non-convergence)

The suspension is represented by a constant WHEEL RATE k_w: a vertical spring at
each front wheel centre, preloaded so that z = 0 is static ride height. Spring
rate, damper length and install ratio are not used.

    fast  Roll-centre method, closed form. The only solves are the design state
          and one steer table (rack sweep at zero travel).
              dF_el = m_c (h_c - h_ra) (a_y + g sin phi) / t0
              z_o,i = (+-dF_el + dF_pitch) / k_w
    full  Starts from the fast answer, then re-solves the whole sweep with rack
          and travel targets until they stop changing. Each pass: rack by
          secant on the effective steer angle; tyre loads by whole-car statics;
          travel by virtual work at each wheel of the solved state
              k_w z = F_z + sigma F_y d(half_track)/dz - m_uf g - W_sc
          (sigma = -1 outer, +1 inner), so no roll centre is needed.

Derivation, variables and flow: project doc claude/quasi-static-corner-sweep-plan.md
and docs/reference/sweeps.md ("Quasi-static corner").

FRAME AND SIGNS
    Tool frame: x forward, y left, z up, millimetres. "Outer" is the wheel on
    the outside of the turn (the left wheel in a right turn). Loads and angles
    below are magnitudes with that meaning; corners map to left/right only when
    the targets are written.

ASSUMPTIONS (all of them; docs/reference/sweeps.md repeats this list)
    Vehicle motion
     1. Each step is a steady state: constant speed and radius, no yaw
        acceleration, no turn-in transient, damper force zero.
     2. Flat, level road. Rigid chassis.
     3. Speed and radius are those of the total CG, which is fixed in the body
        (it does not move with roll except through the roll-gravity term).
     4. No tyre slip: the turn centre is on the rear-axle line, and the front
        steer follows Ackermann geometry, cot(d_eff) = (cot d_o + cot d_i)/2.
        This is neutral steer (understeer gradient K = 0). With Aurora's
        non-100 % Ackermann the two front wheels would fight; not modelled.
    Tyres
     5. Rigid tyres, point contact, constant loaded radius, no camber thrust.
        Grip (a_y <= mu g) and inner-wheel lift are checked, not modelled.
     6. Front lateral force is the front axle's share by statics, split between
        the two front tyres in proportion to F_z (or equally: `fy_split`).
    Masses
     7. Point masses: front unsprung at the design wheel centres, rear unsprung
        at (x_front - L, 0, rear tyre design radius), sprung at the CG that
        makes the total come out at the geometry's cg_position. Rotational
        inertia, products of inertia and wheel gyroscopics are ignored.
     8. The rear unsprung mass rolls with the body (transverse trailing-arm
        pivot), so the rolling mass is m_s + m_ur.
    Springs
     9. Constant wheel rate k_w, vertical at the wheel centre, same both sides;
        no rising rate, bump stops or droop limiter. z = 0 is static
        equilibrium on each side (preload = static sprung corner load).
    10. Only the front springs resist roll (no anti-roll bar; the single rear
        wheel has no roll stiffness).
    Load transfer, fast
    11. Roll-centre model with the DESIGN roll centre, h_rc = (t0/2) s_y0, and
        a straight roll axis from it to the rear contact patch. Track t0 is
        frozen at design. Unsprung and geometric transfer go to the tyres
        without compressing the springs (textbook split). Jacking is ignored.
        Full mode does not make the unsprung assumption: by virtual work most
        of the front unsprung transfer does reach an independent corner's
        spring, so the modes differ by about m_uf h_uf / (m_c (h_c - h_ra))
        even at small a_y (about 6 % with Aurora's placeholder masses).
    12. Pitch: forward inertia (turn centre behind the CG) moves load to the
        front axle; its sprung part is taken as fully elastic (no anti-dive).
    Load transfer, full
    13. Virtual work for a wheel moved up by dz with chassis and rack held:
        links and rack do no work; d(z_contact)/dz = 1; the tyre F_x and the
        unsprung-inertia lateral term (m_uf a_y d(y_wheel_centre)/dz) are
        dropped. Track, scrub and steer are read from the solved state.
    Both
    14. Roll angle phi = atan((z_o - z_i) / t). Roll-gravity shifts the rolling
        CG sideways by (h_c - h_ra) sin phi, using the design roll axis.
    15. The front-axle model holds the chassis fixed: body attitude comes from
        the front wheel travels only; tyre deflection and rear pitch do not.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import numpy as np
import yaml

MODES = ("fast", "full")
TURNS = ("right", "left")
FY_SPLITS = ("load", "equal")

#: Every key the `corner:` block must state. No defaults, like the rest of run.yaml.
REQUIRED_KEYS = (
    "mode", "turn", "speed", "radius", "steps", "rack_limit", "roll_gravity",
    "pitch", "fy_split", "mu", "tolerance", "max_iterations",
)  # fmt: skip

#: Steps in the steer table (rack sweep at zero travel). Interpolated linearly.
TABLE_STEPS = 21

#: |vehicle.mass - (sprung + unsprung)| above this, in kg, is reported.
MASS_MISMATCH_KG = 0.5

SIDES = ("left", "right")


class CornerError(ValueError):
    """A corner sweep cannot be configured or has no steady-state answer."""


# ==========================================================================
# Inputs
# ==========================================================================
@dataclass(frozen=True)
class CornerSettings:
    """The `corner:` block of one run.yaml sweep."""

    mode: str
    turn: str
    speed: float  # m/s, at the CG
    radius: tuple[float, float]  # m, CG path radius, start and end (inf allowed)
    steps: int
    rack_limit: float  # mm, |rack| the steer table covers
    roll_gravity: bool
    pitch: bool
    fy_split: str
    mu: float  # grip check only
    tol_travel: float  # mm
    tol_rack: float  # mm
    max_iterations: int


def parse_settings(name: str, block) -> CornerSettings:
    """Validate a sweep's `corner:` block. Raises CornerError naming the key."""
    where = f"sweep '{name}': corner"
    if not isinstance(block, dict):
        raise CornerError(f"{where} must be a mapping of settings, got {block!r}")
    missing = [k for k in REQUIRED_KEYS if k not in block]
    if missing:
        raise CornerError(
            f"{where} is missing {', '.join(missing)}. Every key is required; "
            "see docs/reference/sweeps.md (Quasi-static corner)."
        )
    unknown = sorted(set(block) - set(REQUIRED_KEYS))
    if unknown:
        raise CornerError(f"{where} has unknown key(s) {', '.join(unknown)}.")

    def number(key):
        try:
            value = float(block[key])
        except (TypeError, ValueError):
            raise CornerError(f"{where}.{key} must be a number") from None
        if not value > 0:
            raise CornerError(f"{where}.{key} must be greater than zero, got {value}")
        return value

    def choice(key, options):
        value = str(block[key]).strip().lower()
        if value not in options:
            raise CornerError(f"{where}.{key} must be one of {', '.join(options)}")
        return value

    def flag(key):
        if not isinstance(block[key], bool):
            raise CornerError(f"{where}.{key} must be true or false")
        return block[key]

    def whole(key, low):
        value = block[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < low:
            raise CornerError(f"{where}.{key} must be a whole number >= {low}")
        return value

    radius = block["radius"]
    try:
        radius = (float(radius[0]), float(radius[1]))
        assert len(block["radius"]) == 2
    except (TypeError, ValueError, AssertionError, IndexError, KeyError):
        raise CornerError(f"{where}.radius must be [start, end] in m") from None
    if not all(r > 0 for r in radius) or math.isinf(radius[1]):
        raise CornerError(
            f"{where}.radius must be positive with a finite end; "
            "start may be .inf (straight)."
        )
    tolerance = block["tolerance"]
    if not isinstance(tolerance, dict) or set(tolerance) != {"travel", "rack"}:
        raise CornerError(f"{where}.tolerance must be {{travel: mm, rack: mm}}")

    return CornerSettings(
        mode=choice("mode", MODES),
        turn=choice("turn", TURNS),
        speed=number("speed"),
        radius=radius,
        steps=whole("steps", 2),
        rack_limit=number("rack_limit"),
        roll_gravity=flag("roll_gravity"),
        pitch=flag("pitch"),
        fy_split=choice("fy_split", FY_SPLITS),
        mu=number("mu"),
        tol_travel=float(tolerance["travel"]),
        tol_rack=float(tolerance["rack"]),
        max_iterations=whole("max_iterations", 1),
    )


@dataclass(frozen=True)
class Vehicle:
    """Everything the corner needs that is not a hardpoint."""

    g: float
    m_s: float  # sprung, excludes every wheel and suspension part
    m_uf: float  # front unsprung, per wheel
    m_ur: float  # rear unsprung (single wheel)
    k_w: float  # front wheel rate, N/mm, vertical at the wheel centre
    cg: tuple[float, float, float]  # total CG, mm, tool frame
    wheelbase: float  # mm
    h_ur: float  # rear wheel-centre height, mm
    warnings: tuple[str, ...] = ()


def load_vehicle(geometry_data: Mapping, forces_path: Path) -> Vehicle:
    """Masses and wheel rate from forces.yaml; CG and wheelbase from the geometry.

    `geometry_data` is the decoded front geometry (front.yaml as a dict); the
    optimiser passes its patched candidate, the reports the file.
    """
    from kinematics.core.input import parse_geometry_spec
    from kinematics.core.schema.config import TireConfig
    from kinematics.core.schema.loads import VehicleMassConfig

    forces_path = Path(forces_path)
    if not forces_path.is_file():
        raise CornerError(f"corner sweep needs {forces_path}; not found.")
    forces = yaml.safe_load(forces_path.read_text(encoding="utf-8")) or {}
    vehicle = VehicleMassConfig.model_validate(forces.get("vehicle") or {})
    keys = ("sprung_mass", "unsprung_mass_front", "unsprung_mass_rear",
            "wheel_rate_front")  # fmt: skip
    missing = [key for key in keys if getattr(vehicle, key) is None]
    if missing:
        raise CornerError(
            f"{forces_path.name} vehicle: is missing {', '.join(missing)}, which "
            "the corner sweep needs (kg, per-wheel front unsprung; N/mm)."
        )

    spec = parse_geometry_spec(geometry_data)
    config = getattr(spec, "vehicle_config", None)
    if config is None or config.cg_position is None or config.wheelbase is None:
        raise CornerError("the front geometry needs vehicle_config cg and wheelbase.")

    rear_name = (forces.get("geometry") or {}).get("rear")
    if not rear_name:
        raise CornerError(f"{forces_path.name} names no geometry.rear.")
    rear_path = (forces_path.parent / rear_name).resolve()
    rear = yaml.safe_load(rear_path.read_text(encoding="utf-8")) or {}
    wheel = next(
        (
            block["wheel"]
            for key, block in rear.items()
            if (key == "config" or key.endswith("_config"))
            and isinstance(block, dict)
            and "wheel" in block
        ),
        None,
    )
    if wheel is None or "tire" not in wheel:
        raise CornerError(f"{rear_path.name} declares no wheel tire (rear height).")

    warnings = []
    parts = (
        vehicle.sprung_mass
        + 2 * vehicle.unsprung_mass_front
        + vehicle.unsprung_mass_rear
    )
    if abs(parts - vehicle.mass) > MASS_MISMATCH_KG:
        warnings.append(
            f"sprung + unsprung = {parts:.1f} kg but vehicle.mass = "
            f"{vehicle.mass:.1f} kg; the corner sweep uses the sum of the parts."
        )
    cg = config.cg_position
    return Vehicle(
        g=vehicle.g,
        m_s=vehicle.sprung_mass,
        m_uf=vehicle.unsprung_mass_front,
        m_ur=vehicle.unsprung_mass_rear,
        k_w=vehicle.wheel_rate_front,
        cg=(float(cg[0]), float(cg[1]), float(cg[2])),
        wheelbase=float(config.wheelbase),
        h_ur=float(TireConfig(**wheel["tire"]).design_radius),
        warnings=tuple(warnings),
    )


# ==========================================================================
# Solving through the existing sweep machinery
# ==========================================================================
def _targets(rack, travel) -> list[dict]:
    """Explicit-value targets in run.yaml's own vocabulary (relative mode)."""
    targets = [
        {"type": "point", "point": "wheel_center", "side": side,
         "direction": {"axis": "z"}, "mode": "relative",
         "values": [float(v) for v in travel[side]]}
        for side in SIDES
    ]  # fmt: skip
    targets.append(
        {"type": "actuator_position", "actuator": "rack",
         "direction": {"axis": "y"}, "mode": "relative",
         "values": [float(v) for v in rack]}
    )  # fmt: skip
    return targets


def _solve(suspension, rack, travel) -> dict:
    """Solve one explicit-value sweep; return the channels this module reads."""
    from kinematics.core.analysis import analyze_sweep
    from kinematics.core.input import build_sweep

    targets = _targets(rack, travel)
    spec = {"version": 1, "steps": len(targets[0]["values"]), "targets": targets}
    frames = analyze_sweep(suspension, build_sweep(spec, suspension)).frames

    def column(side, key):
        values = [frame.corner_metrics[side].get(key) for frame in frames]
        return np.array([np.nan if v is None else float(v) for v in values])

    out = {
        side: {
            "steer": column(side, "steer_angle"),
            "scrub": column(side, "deriv_half_track_wrt_hub_z"),
            "travel": column(side, "wheel_travel"),
            "steer_per_rack": column(side, "deriv_steer_angle_wrt_rack_displacement"),
        }
        for side in SIDES
    }
    out["track"] = np.array([float(frame.metrics["track"]) for frame in frames])
    out["wheel_center"] = [
        {side: frame.positions[f"{side}_wheel_center"] for side in SIDES}
        for frame in frames
    ]
    return out


def _effective_steer(delta_o, delta_i):
    """Bicycle-equivalent steer (rad): cot(d_eff) = (cot d_o + cot d_i)/2."""
    t_o, t_i = np.tan(delta_o), np.tan(delta_i)
    total = t_o + t_i
    with np.errstate(divide="ignore", invalid="ignore"):
        tan_eff = np.where(np.abs(total) > 1e-12, 2 * t_o * t_i / total, 0.5 * total)
    return np.arctan(tan_eff)


# ==========================================================================
# The model
# ==========================================================================
@dataclass
class _Model:
    """Masses, CGs and design state, worked out once per resolve()."""

    v: Vehicle
    s: CornerSettings
    outer: str
    inner: str
    turn_sign: float  # +1 left turn, -1 right turn (ISO steer sign)
    m: float
    b: float  # total CG ahead of the rear axle, mm
    h: float  # total CG height, mm
    y_out: float  # total CG lateral offset toward the outer wheel, mm
    b_s: float  # sprung CG ahead of the rear axle
    h_s: float
    m_c: float  # rolling mass, sprung + rear unsprung
    b_c: float
    h_c: float
    b_uf: float  # front wheel centres ahead of the rear axle
    h_uf: float
    t0: float  # design track at the contact patches
    h_rc0: float  # design front roll-centre height
    w_sc: dict  # static load on each front spring (preload), per side
    steer: dict  # steer table: rack and effective steer
    warnings: list = field(default_factory=list)

    @property
    def h_ra(self) -> float:
        """Roll-axis height under the rolling CG (front RC to rear contact)."""
        return self.h_rc0 * self.b_c / self.v.wheelbase


def _build_model(suspension, vehicle: Vehicle, settings: CornerSettings) -> _Model:
    if not getattr(suspension, "is_axle", False):
        raise CornerError("the corner sweep needs a two-corner front axle geometry.")
    v, L = vehicle, vehicle.wheelbase
    design = _solve(suspension, [0.0, 0.0], {side: [0.0, 0.0] for side in SIDES})
    wc = design["wheel_center"][0]
    x_f = float(np.mean([wc[side][0] for side in SIDES]))
    h_uf = float(np.mean([wc[side][2] for side in SIDES]))
    x_r = x_f - L

    m = v.m_s + 2 * v.m_uf + v.m_ur
    cg = np.array(v.cg)
    r_rear = np.array([x_r, 0.0, v.h_ur])
    front = np.array(wc["left"], float) + np.array(wc["right"], float)
    r_s = (m * cg - v.m_uf * front - v.m_ur * r_rear) / v.m_s
    m_c = v.m_s + v.m_ur
    r_c = (v.m_s * r_s + v.m_ur * r_rear) / m_c

    outer, inner = ("left", "right") if settings.turn == "right" else ("right", "left")
    turn_sign = -1.0 if settings.turn == "right" else 1.0
    per_rack = float(design["left"]["steer_per_rack"][0])
    if not per_rack or not math.isfinite(per_rack):
        raise CornerError("the steering does not respond to the rack at design.")
    rack_sign = math.copysign(1.0, turn_sign / per_rack)

    t0 = float(design["track"][0])
    # Roll-centre height from the scrub derivative: h_rc = (t/2) d(half_track)/dz.
    h_rc0 = float(np.mean([t0 / 2 * design[side]["scrub"][0] for side in SIDES]))
    b = float(cg[0] - x_r)
    y_out = float(cg[1]) if outer == "left" else -float(cg[1])
    base = 0.5 * m * v.g * b / L
    w_sc = {
        outer: base + m * v.g * y_out / t0 - v.m_uf * v.g,
        inner: base - m * v.g * y_out / t0 - v.m_uf * v.g,
    }

    # Steer table: rack from 0 toward the turn, at zero travel.
    rack = np.linspace(0.0, rack_sign * settings.rack_limit, TABLE_STEPS)
    table = _solve(suspension, rack, {side: np.zeros(TABLE_STEPS) for side in SIDES})
    delta = {side: np.radians(turn_sign * table[side]["steer"]) for side in SIDES}
    effective = _effective_steer(delta[outer], delta[inner])
    if not np.all(np.diff(effective) > 0):
        raise CornerError(
            "the effective steer angle is not monotonic over rack_limit; "
            "reduce rack_limit to where the steering does not reverse."
        )
    return _Model(
        v=v, s=settings, outer=outer, inner=inner, turn_sign=turn_sign, m=m,
        b=b, h=float(cg[2]), y_out=y_out,
        b_s=float(r_s[0] - x_r), h_s=float(r_s[2]),
        m_c=m_c, b_c=float(r_c[0] - x_r), h_c=float(r_c[2]),
        b_uf=float(x_f - x_r), h_uf=h_uf, t0=t0, h_rc0=h_rc0, w_sc=w_sc,
        steer={"rack": rack, "effective": effective},
        warnings=list(v.warnings),
    )  # fmt: skip


def _turn_kinematics(model: _Model) -> list[dict]:
    """Stage A: per step, from radius and speed only."""
    s, L = model.s, model.v.wheelbase
    kappa = np.linspace(1.0 / s.radius[0], 1.0 / s.radius[1], s.steps)  # 1/m
    steps = []
    for k, curvature in enumerate(kappa):
        if curvature <= 0:
            steps.append(dict(kappa=0.0, radius=math.inf, r_rear=math.inf,
                              omega=0.0, a_y=0.0, delta_target=0.0))  # fmt: skip
            continue
        radius_mm = 1000.0 / curvature
        if not radius_mm > model.b:
            raise CornerError(
                f"step {k + 1}: radius {radius_mm / 1000:.3f} m is not larger than "
                f"the CG's distance ahead of the rear axle ({model.b / 1000:.3f} m); "
                "no steady turn exists."
            )
        r_rear = math.sqrt(radius_mm**2 - model.b**2)  # turn centre to rear contact
        omega = s.speed / (radius_mm / 1000.0)
        steps.append(
            dict(kappa=float(curvature), radius=radius_mm / 1000.0,
                 r_rear=r_rear / 1000.0, omega=omega,
                 a_y=omega**2 * r_rear / 1000.0,  # same for every centreline point
                 delta_target=math.atan(L / r_rear))
        )  # fmt: skip
    return steps


def _tyre_loads(model: _Model, step: dict, phi: float, track: float) -> dict:
    """Front tyre loads from whole-car statics about the rear contact line."""
    v, L = model.v, model.v.wheelbase
    a_y, omega = step["a_y"], step["omega"]
    y_out = model.y_out
    if model.s.roll_gravity:
        y_out += model.m_c * (model.h_c - model.h_ra) * math.sin(phi) / model.m
    pitch = 0.0  # front-axle load from forward inertia, sum m_i Omega^2 d_i h_i / L
    if model.s.pitch:
        moment = v.m_s * model.b_s * model.h_s + 2 * v.m_uf * model.b_uf * model.h_uf
        pitch = omega**2 * moment / 1000.0 / L
    base = 0.5 * model.m * v.g * model.b / L
    lateral = (model.m * v.g * y_out + model.m * a_y * model.h) / track
    fz = {
        model.outer: base + lateral + pitch / 2,
        model.inner: base - lateral + pitch / 2,
    }
    fy_front = a_y * (v.m_s * model.b_s + 2 * v.m_uf * model.b_uf) / L
    if model.s.fy_split == "equal":
        fy = {side: fy_front / 2 for side in SIDES}
    else:
        fy = {side: fy_front * fz[side] / (fz[model.outer] + fz[model.inner])
              for side in SIDES}  # fmt: skip
    return {"fz": fz, "fy": fy}


def _check_step(model: _Model, k: int, step: dict, loads: dict, warnings: list):
    g = model.v.g
    fz_inner = loads["fz"][model.inner]
    if fz_inner <= 0:
        warnings.append(
            f"step {k + 1} (R {step['radius']:.2f} m, a_y {step['a_y'] / g:.3f} g): "
            f"inner front tyre load {fz_inner:.0f} N - the wheel lifts."
        )
    if step["a_y"] > model.s.mu * g:
        warnings.append(
            f"step {k + 1}: a_y {step['a_y'] / g:.3f} g exceeds mu = {model.s.mu}."
        )


def _row(model, k, step, rack, z, phi, loads, **extra) -> dict:
    row = dict(
        step=k + 1, kappa=step["kappa"], radius_m=step["radius"],
        rear_radius_m=step["r_rear"], yaw_rate=step["omega"], a_y=step["a_y"],
        a_y_g=step["a_y"] / model.v.g,
        steer_target_deg=math.degrees(step["delta_target"]),
        rack=rack, roll_deg=math.degrees(phi),
    )  # fmt: skip
    for side in SIDES:
        row[f"role_{side}"] = "outer" if side == model.outer else "inner"
        row[f"travel_{side}"] = z[side]
        row[f"spring_load_{side}"] = model.w_sc[side] + model.v.k_w * z[side]
        row[f"tyre_fz_{side}"] = loads["fz"][side]
        row[f"tyre_fy_{side}"] = loads["fy"][side]
    row.update(extra)
    return {key: (float(value) if isinstance(value, np.floating) else value)
            for key, value in row.items()}  # fmt: skip


# ---------------------------------------------------------------- fast ----
def _fast(model: _Model, steps: list[dict]):
    """Roll-centre method, closed form (plus the roll-gravity loop)."""
    v, s, table = model.v, model.s, model.steer
    arm = model.m_c * (model.h_c - model.h_ra)  # kg mm, rolling mass above axis
    rows, warnings = [], []
    for k, step in enumerate(steps):
        if step["delta_target"] > table["effective"][-1]:
            raise CornerError(
                f"step {k + 1}: R {step['radius']:.2f} m needs "
                f"{math.degrees(step['delta_target']):.2f} deg of effective steer, "
                f"more than rack_limit gives "
                f"({math.degrees(table['effective'][-1]):.2f} deg)."
            )
        rack = float(np.interp(step["delta_target"], table["effective"], table["rack"]))
        pitch_el = 0.0
        if s.pitch:
            pitch_el = step["omega"] ** 2 * v.m_s * model.b_s * model.h_s
            pitch_el /= 1000.0 * 2 * v.wheelbase
        phi = 0.0
        for _ in range(200):
            accel = step["a_y"] + (v.g * math.sin(phi) if s.roll_gravity else 0.0)
            d_el = arm * accel / model.t0
            z = {
                model.outer: (d_el + pitch_el) / v.k_w,
                model.inner: (-d_el + pitch_el) / v.k_w,
            }
            new_phi = math.atan((z[model.outer] - z[model.inner]) / model.t0)
            done = not s.roll_gravity or abs(new_phi - phi) < 1e-10
            phi = new_phi
            if done:
                break
        else:
            raise CornerError(
                f"step {k + 1}: roll does not settle; the wheel rate is too low "
                "for the roll-gravity moment (k_w t0^2 / 2 <= m_c g (h_c - h_ra))."
            )
        loads = _tyre_loads(model, step, phi, model.t0)
        _check_step(model, k, step, loads, warnings)
        rows.append(_row(
            model, k, step, rack, z, phi, loads,
            dF_elastic=d_el, dF_pitch_elastic=pitch_el,
            dF_geometric=model.m_c * step["a_y"] * model.b_c / v.wheelbase
            * model.h_rc0 / model.t0,
            dF_unsprung=2 * v.m_uf * step["a_y"] * model.h_uf / model.t0,
            iterations=0,
        ))  # fmt: skip
    return rows, warnings


# ---------------------------------------------------------------- full ----
def _full(suspension, model: _Model, steps: list[dict], fast_rows: list[dict]):
    """Iterate rack and wheel travel until the solved state is in equilibrium."""
    v, s, table = model.v, model.s, model.steer
    rack = np.array([row["rack"] for row in fast_rows])
    travel = {side: np.array([row[f"travel_{side}"] for row in fast_rows])
              for side in SIDES}  # fmt: skip
    target = np.array([step["delta_target"] for step in steps])
    slope_table = np.gradient(table["effective"], table["rack"])  # first secant step
    prev_rack = prev_err = None
    for iteration in range(1, s.max_iterations + 1):
        solved = _solve(suspension, rack, travel)
        delta = {side: np.radians(model.turn_sign * solved[side]["steer"])
                 for side in SIDES}  # fmt: skip
        err = _effective_steer(delta[model.outer], delta[model.inner]) - target
        slope = np.interp(rack, table["rack"], slope_table)
        if prev_rack is not None:
            dx = rack - prev_rack
            with np.errstate(divide="ignore", invalid="ignore"):
                slope = np.where(np.abs(dx) > 1e-9, (err - prev_err) / dx, slope)
        new_rack = np.where(target > 0, rack - err / slope, 0.0)

        new_travel = {side: np.empty(len(steps)) for side in SIDES}
        rows, warnings = [], []
        for k, step in enumerate(steps):
            track = float(solved["track"][k])
            z = {side: float(solved[side]["travel"][k]) for side in SIDES}
            phi = math.atan((z[model.outer] - z[model.inner]) / track)
            loads = _tyre_loads(model, step, phi, track)
            for side in SIDES:
                # Virtual work, wheel up by dz, chassis and rack held. The tyre's
                # lateral force points toward the turn centre: inward on the
                # outer wheel (against outward scrub), outward on the inner.
                sigma = -1.0 if side == model.outer else 1.0
                scrub = float(solved[side]["scrub"][k])
                wheel = loads["fz"][side] + sigma * loads["fy"][side] * scrub
                wheel -= v.m_uf * v.g
                new_travel[side][k] = (wheel - model.w_sc[side]) / v.k_w
            _check_step(model, k, step, loads, warnings)
            rows.append(_row(
                model, k, step, float(rack[k]), z, phi, loads,
                steer_error_deg=math.degrees(float(err[k])),
                scrub_left=float(solved["left"]["scrub"][k]),
                scrub_right=float(solved["right"]["scrub"][k]),
                iterations=iteration,
            ))  # fmt: skip

        change_z = max(float(np.max(np.abs(new_travel[sd] - travel[sd])))
                       for sd in SIDES)  # fmt: skip
        change_x = float(np.max(np.abs(new_rack - rack)))
        if change_z < s.tol_travel and change_x < s.tol_rack:
            return rows, warnings
        prev_rack, prev_err = rack, err
        rack, travel = new_rack, new_travel
    warnings.append(
        f"full mode did not converge in {s.max_iterations} iterations "
        f"(last change: travel {change_z:.4f} mm, rack {change_x:.4f} mm)."
    )
    return rows, warnings


# ---------------------------------------------------------------- entry ---
@dataclass(frozen=True)
class CornerResult:
    """What resolve() returns: the sweep to solve, and why."""

    spec: dict
    rows: list[dict]
    warnings: list[str]
    mode: str


def resolve(
    suspension,
    geometry_data: Mapping,
    vehicle: Vehicle,
    settings: CornerSettings,
    mode: str | None = None,
) -> CornerResult:
    """Work out one corner sweep's rack and wheel travels.

    `mode` overrides settings.mode (the optimiser forces "fast"). Both modes
    write the result as wheel-travel and rack targets.
    """
    mode = (mode or settings.mode).lower()
    if mode not in MODES:
        raise CornerError(f"mode must be one of {', '.join(MODES)}, got {mode!r}")
    model = _build_model(suspension, vehicle, settings)
    steps = _turn_kinematics(model)
    rows, warnings = _fast(model, steps)
    if mode == "full":
        rows, warnings = _full(suspension, model, steps, rows)
    travel = {side: [row[f"travel_{side}"] for row in rows] for side in SIDES}
    rack = [row["rack"] for row in rows]
    spec = {"version": 1, "steps": len(rows), "targets": _targets(rack, travel)}
    if len(warnings) > 3:
        warnings = warnings[:3] + [f"(+{len(warnings) - 3} more)"]
    return CornerResult(spec, rows, model.warnings + warnings, mode)


def write_rows(path: Path, rows: list[dict]) -> None:
    """The per-step quasi-static table, beside the sweep CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
