#!/usr/bin/env python3
"""
susreport - characteristic report for a TWO-WHEEL AXLE (Aurora front).

    uv run python models/Sweep_Set/susreport.py <outputs dir> --out <report dir>

Its CSV columns are side-suffixed (`camber_left`) and it carries axle-level
channels - track, body roll, roll centre, rack, Ackermann - that a single
corner does not have. The rear's single trailing arm is a different object with
a different set of meaningful characteristics, so it has its own reporter:
`susreport_rear.py`. What the two share - CSV parsing, solver health, tables,
plots, report assembly - lives in `susreport_common.py`, and the bearing
misalignment analysis lives in `bearings.py`.

There are no built-in defaults: a configuration is required, and a missing or
incomplete one is an error naming the key. `run_all.py` imports `run_report`
from the common module rather than launching a second Python, so a breakpoint
here is hit by an ordinary run_all.py run.

See RUNNING.md for the configuration keys and CHARACTERISTICS.md for what each
channel means and which sweep is the meaningful source for it.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

import susreport_common as C
from susreport_common import Channel, Sweep, axle, pair, single

TITLE = "Front axle characteristic report"

# The Ackermann percentage divides by the IDEAL inner-minus-outer difference,
# which is second order in the steer angle and so vanishes far faster than the
# numerator near centre: on Aurora it is only 0.007 deg at 1 deg of outer
# steer, against which a few hundredths of a degree of roll steer reads as
# several hundred percent. Blank the ratio until the denominator is big enough
# to divide by. 0.25 deg corresponds to roughly 6 deg of outer steer here.
ACKERMANN_MIN_IDEAL_DELTA_DEG = 0.25


# ==========================================================================
# 1. Channel catalogue
#
# The config-facing names. "{side}" is substituted with "_left" or "_right".
# Adding a characteristic to the report means adding one entry here and naming
# it in run.yaml - nothing else.
# ==========================================================================
CHANNELS: dict[str, Channel] = {c.key: c for c in [
    # --- corner, single side -------------------------------------------
    single("camber", "Camber", "camber{side}"),
    single("camber_road", "Camber, road-relative", "camber_road{side}"),
    single("caster", "Caster", "caster{side}"),
    single("kpi", "Kingpin inclination", "kpi{side}"),
    single("toe", "Toe (positive = toe-in)", "toe_angle{side}"),
    single("steer_angle", "ISO steer angle", "steer_angle{side}"),
    single("scrub_signed", "Scrub radius (signed lateral)",
            "scrub_radius_signed{side}"),
    single("scrub_iso", "Scrub radius (ISO unsigned)", "scrub_radius{side}"),
    single("trail", "Mechanical trail", "mechanical_trail{side}"),
    single("half_track", "Half track", "half_track{side}"),
    single("wheel_travel", "Wheel travel", "wheel_travel{side}"),
    single("damper_length", "Damper length", "damper_length{side}"),
    single("motion_ratio", "Motion ratio (damper/wheel)", "motion_ratio{side}"),
    single("motion_ratio_sq", "Motion ratio squared", "motion_ratio_sq{side}"),
    single("fvic_y", "FVIC lateral (y)", "fvic_y{side}"),
    single("fvic_z", "FVIC height (z)", "fvic_z{side}"),
    single("fvsa", "FVSA length", "fvsa_length{side}"),
    single("svic_x", "SVIC longitudinal (x)", "svic_x{side}"),
    single("svic_z", "SVIC height (z)", "svic_z{side}"),
    single("svsa", "SVSA length", "svsa_length{side}"),
    single("svsa_angle", "SVSA angle", "svsa_angle{side}"),
    single("anti_dive", "Anti-dive", "anti_dive{side}"),
    single("anti_lift", "Anti-lift", "anti_lift{side}"),
    single("anti_squat", "Anti-squat", "anti_squat{side}"),
    single("camber_recovery", "Camber recovery", "camber_recovery{side}"),

    # --- corner gradients ----------------------------------------------
    single("camber_gain", "Camber gain", "deriv_camber_wrt_hub_z{side}"),
    single("bump_steer", "Bump steer rate", "deriv_toe_angle_wrt_hub_z{side}"),
    single("caster_gain", "Caster gain", "deriv_caster_wrt_hub_z{side}"),
    single("kpi_gain", "KPI gain", "deriv_kpi_wrt_hub_z{side}"),
    single("half_track_rate", "Half-track change rate",
            "deriv_half_track_wrt_hub_z{side}"),
    single("recession_rate", "Wheel-centre recession rate",
            "deriv_wheel_center_x_wrt_hub_z{side}"),
    single("damper_rate", "Damper rate vs wheel",
            "deriv_damper_length_wrt_hub_z{side}"),
    single("toe_per_rack", "Toe per rack",
            "deriv_toe_angle_wrt_rack_displacement{side}"),
    single("camber_per_rack", "Camber per rack",
            "deriv_camber_wrt_rack_displacement{side}"),

    # --- left/right pairs (roll and steer sweeps) ----------------------
    pair("camber_lr", "Camber (left/right)", "camber{side}"),
    pair("camber_road_lr", "Camber, road-relative (left/right)",
          "camber_road{side}"),
    pair("caster_lr", "Caster (left/right)", "caster{side}"),
    pair("kpi_lr", "Kingpin inclination (left/right)", "kpi{side}"),
    pair("toe_lr", "Toe (left/right)", "toe_angle{side}"),
    pair("steer_angle_lr", "ISO steer angle (left/right)", "steer_angle{side}"),
    pair("scrub_signed_lr", "Scrub radius, signed (left/right)",
          "scrub_radius_signed{side}"),
    pair("trail_lr", "Mechanical trail (left/right)", "mechanical_trail{side}"),
    pair("half_track_lr", "Half track (left/right)", "half_track{side}"),
    pair("wheel_travel_lr", "Wheel travel (left/right)", "wheel_travel{side}"),
    pair("damper_length_lr", "Damper length (left/right)", "damper_length{side}"),
    pair("motion_ratio_lr", "Motion ratio (left/right)", "motion_ratio{side}"),
    pair("camber_recovery_lr", "Camber recovery (left/right)",
          "camber_recovery{side}"),

    # --- axle ------------------------------------------------------------
    axle("track", "Track", "track"),
    axle("track_change", "Track change", "track_change"),
    axle("track_change_rate", "Track change rate", "track_change_rate"),
    axle("rc_height", "Roll-centre height", "roll_center_z"),
    axle("rc_lateral", "Roll-centre lateral position", "roll_center_y"),
    axle("rc_migration", "Roll-centre migration vs travel", "rc_migration_rate"),
    axle("rc_migration_roll", "Roll-centre migration vs roll",
          "rc_migration_rate_roll"),
    axle("rc_lateral_roll", "Roll-centre lateral migration vs roll",
          "rc_lateral_rate_roll"),
    axle("body_roll", "Body roll", "roll"),
    axle("mean_wheel_travel", "Mean wheel-centre travel", "heave"),
    axle("rack", "Rack displacement", "rack_displacement"),
    axle("ackermann_error", "Ackermann error (inner - outer)", "ackermann_error"),
    axle("ackermann", "Ackermann", "ackermann_percent"),
    axle("steering_ratio", "Steering ratio (rack)", "steer_per_rack_abs"),
    axle("steering_ratio_unitless", "Steering ratio (wheel : road wheel)",
          "steering_ratio_unitless"),
]}



# Default channel list per sweep kind, used when a sweep asks for `report: true`
# without naming channels. These mirror the sets agreed for the Aurora front
# axle; override per sweep in run.yaml when you want something else.
PRESETS: dict[str, list[str]] = {
    "heave": [
        "camber", "caster", "toe", "scrub_signed", "trail", "half_track",
        "wheel_travel", "damper_length", "motion_ratio", "rc_height",
        "fvic_y", "fvic_z", "fvsa", "track_change", "steering_ratio",
        "camber_gain",
    ],
    "roll": [
        "camber_lr", "caster_lr", "toe_lr", "scrub_signed", "half_track",
        "track_change", "motion_ratio", "camber_recovery", "rc_height",
        "rc_lateral_roll", "body_roll", "steering_ratio",
    ],
    "single_wheel": [
        "camber", "caster", "toe", "scrub_signed", "half_track",
        "wheel_travel", "damper_length", "motion_ratio", "rc_height",
    ],
    "steer": [
        "camber", "caster", "toe", "scrub_signed", "trail", "half_track",
        "track_change", "damper_length", "rc_height", "rc_lateral",
        "fvic_y", "fvic_z", "fvsa", "rack", "ackermann", "steering_ratio",
    ],
    "heave_at_steer": [
        "camber", "caster", "toe", "scrub_signed", "trail", "half_track",
        "wheel_travel", "damper_length", "motion_ratio", "rc_height",
        "track_change", "ackermann", "steering_ratio", "camber_gain",
    ],
    # 09: a steer sweep held at a roll attitude. Same channels as a steer
    # sweep plus the roll-specific ones, since the axle is rolled throughout.
    "steer_in_roll": [
        "camber_lr", "caster_lr", "toe_lr", "scrub_signed", "trail",
        "half_track", "track_change", "damper_length", "rc_height",
        "rc_lateral", "body_roll", "rack", "ackermann", "steering_ratio",
    ],
    # 10: roll and steer ramp together, so both families are meaningful and
    # the abscissa is the rack.
    # Camber recovery and the roll-centre roll-migration rates are deliberately
    # absent: with roll and rack ramping together they would be derivatives
    # along the path, not with respect to roll. Take those from 02.
    "roll_ramp_at_steer": [
        "camber_lr", "caster_lr", "toe_lr", "scrub_signed", "half_track",
        "track_change", "motion_ratio", "rc_height", "rc_lateral",
        "body_roll", "rack", "ackermann", "steering_ratio",
    ],
    "damper_stroke": [
        "damper_length", "wheel_travel_lr", "motion_ratio",
    ],
    "static": ["camber", "caster", "toe", "half_track"],
}

# Channels that should never be plotted even when `plots: all` is set, because
# the curve is unreadable or the value is constant. FVIC/FVSA pass through a
# singularity when the wishbones go parallel, so they swing to +/- 10^5 mm and
# flatten every other feature; camber gain is their bounded equivalent
# (camber_gain ~ -57.296 / FVSA) and is plotted instead. See CHARACTERISTICS.md.
NEVER_PLOT = {"fvic_y", "fvic_z", "fvsa", "svic_x", "svic_z", "svsa",
              "track", "rack", "wheel_travel", "wheel_travel_lr"}



# ==========================================================================
# 2. Classification - work out what the sweep actually does
# ==========================================================================
def classify(sw: Sweep) -> None:
    """Infer the sweep type from how its target columns vary."""
    d = sw.data
    targets = [c for c in d.columns if c.startswith("target_")]

    # The exported target_* columns are the MEASURED coordinates, so a target
    # that was commanded to hold still still wobbles by ~1e-6 of solver noise.
    # Classify against the largest mover rather than an absolute epsilon.
    spans = {c: float(d[c].max() - d[c].min()) for c in targets
             if not d[c].isna().all()}
    biggest = max(spans.values(), default=0.0)
    threshold = max(1e-2, 0.01 * biggest)

    def varies(col: str) -> bool:
        return spans.get(col, 0.0) > threshold

    zl, zr = "target_wheel_center_z_left", "target_wheel_center_z_right"
    dl, dr = "target_damper_length_left", "target_damper_length_right"
    rack = "target_rack"

    if varies(dl) or varies(dr):
        sw.kind = "damper_stroke"
        sw.x_col = "damper_length_left"
        sw.x_label = "damper length [mm]"
        sw.notes.append(
            "Driven by damper length, so the wrt_hub_z analytic derivatives are "
            "absent. Gradients here are finite-differenced by this parser."
        )
        return

    z_moves = varies(zl) or varies(zr)
    rack_moves = varies(rack)

    if z_moves and not rack_moves:
        if varies(zl) and varies(zr):
            same = np.corrcoef(d[zl], d[zr])[0, 1] > 0
            sw.kind = "heave" if same else "roll"
        else:
            sw.kind = "single_wheel"
        sw.x_col = "roll" if sw.kind == "roll" else "wheel_travel_left"
        sw.x_label = ("body roll [deg]" if sw.kind == "roll"
                      else "left wheel travel [mm]")
    elif rack_moves and not z_moves:
        sw.kind = "steer"
        sw.x_col = "rack_displacement"
        sw.x_label = "rack displacement [mm]"
    elif rack_moves and z_moves:
        # Both move. If the two wheels move oppositely this is a roll-and-steer
        # ramp (sweep 10); the rack is still the more readable abscissa.
        opposed = (varies(zl) and varies(zr)
                   and np.corrcoef(d[zl], d[zr])[0, 1] < 0)
        sw.kind = "roll_ramp_at_steer" if opposed else "heave_at_steer"
        sw.x_col = "rack_displacement" if opposed else "wheel_travel_left"
        sw.x_label = ("rack displacement [mm]" if opposed
                      else "left wheel travel [mm]")
    else:
        sw.kind = "static"
        sw.x_col = "step_index"
        sw.x_label = "step"

    # A steer sweep held off design height is still a steer sweep, but say so.
    if sw.kind == "steer" and zl in d.columns:
        if "wheel_travel_left" in d.columns:
            tv_l = float(d["wheel_travel_left"].iloc[0])
            tv_r = (float(d["wheel_travel_right"].iloc[0])
                    if "wheel_travel_right" in d.columns else tv_l)
            if abs(tv_l) > 1e-3 or abs(tv_r) > 1e-3:
                if abs(tv_l + tv_r) < 1e-3 and abs(tv_l) > 1e-3:
                    roll = (float(d["roll"].iloc[0]) if "roll" in d.columns
                            else float("nan"))
                    sw.kind = "steer_in_roll"
                    sw.notes.append(
                        f"Held at {tv_l:+.1f}/{tv_r:+.1f} mm wheel travel "
                        f"({roll:+.2f} deg roll) - this is a ROLLED sweep. "
                        "Roll is held in ONE direction while the rack sweeps "
                        "both, so only the half that steers into the roll is a "
                        "real cornering state; the other half is the car "
                        "rolled one way and steered the other, which happens "
                        "only in a transient. Expect the two halves to "
                        "disagree - that asymmetry is the point of the sweep, "
                        "not an error."
                    )
                else:
                    sw.notes.append(
                        f"Held at {tv_l:+.1f} mm wheel travel, not design height."
                    )
    unsteered = sw.kind in ("heave", "single_wheel", "roll")
    if unsteered and "rack_displacement" in d.columns:
        rd = float(d["rack_displacement"].mean())
        if abs(rd) > 1e-2:
            sw.kind = f"{sw.kind}_at_steer"
            sw.notes.append(f"Rack held at {rd:+.2f} mm - this is a STEERED sweep.")
    if sw.x_col not in d.columns:
        sw.x_col = "step_index"


def preset_for(sw: Sweep) -> list[str]:
    """The channel list a sweep gets when it says `report: true`."""
    # Longest/most specific kinds first: "steer_in_roll" must not be caught by
    # the "steer" prefix, and "roll_ramp_at_steer" must not be caught by "roll".
    for prefix in ("damper_stroke", "roll_ramp_at_steer", "heave_at_steer",
                   "steer_in_roll", "single_wheel", "steer", "roll", "heave"):
        if sw.kind.startswith(prefix):
            return list(PRESETS.get(prefix, PRESETS["static"]))
    return list(PRESETS["static"])



# ==========================================================================
# 3. Derived channels the solver does not export
# ==========================================================================
def add_derived(sw: Sweep, geometry: dict | None = None) -> None:
    """Append the derived columns an axle model can produce."""
    C.add_corner_derived(sw, ("_left", "_right"))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        _add_axle_derived(sw, geometry)
    sw.data = sw.data.copy()


def _add_axle_derived(sw: Sweep, geometry: dict | None) -> None:
    d = sw.data

    # --- Track change rate --------------------------------------------
    if "deriv_half_track_wrt_hub_z_left" in d.columns:
        d["track_change_rate"] = 2.0 * d["deriv_half_track_wrt_hub_z_left"]
        sw.units["track_change_rate"] = "mm/mm"

    # --- Roll-centre migration ----------------------------------------
    if "roll_center_z" in d.columns:
        if sw.kind.startswith(("heave", "single_wheel")) and \
                "wheel_travel_left" in d.columns:
            z = d["wheel_travel_left"].to_numpy(float)
            if np.ptp(z) > 1e-6:
                d["rc_migration_rate"] = np.gradient(
                    d["roll_center_z"].to_numpy(float), z)
                sw.units["rc_migration_rate"] = "mm/mm"
        # Same caveat as camber recovery: a roll derivative is only a roll
        # derivative when the rack is stationary.
        if "roll" in d.columns and not _steers(sw):
            r = d["roll"].to_numpy(float)
            if np.ptp(r) > 1e-6:
                d["rc_migration_rate_roll"] = np.gradient(
                    d["roll_center_z"].to_numpy(float), r)
                sw.units["rc_migration_rate_roll"] = "mm/deg"
                if "roll_center_y" in d.columns:
                    d["rc_lateral_rate_roll"] = np.gradient(
                        d["roll_center_y"].to_numpy(float), r)
                    sw.units["rc_lateral_rate_roll"] = "mm/deg"

    # --- Camber recovery in roll --------------------------------------
    # Recovery is d(camber)/d(body roll), so it exists only where the axle
    # actually rolls. In parallel bump the roll angle is identically zero and
    # the derivative does not exist; camber gain (deg/mm) is the bump
    # equivalent and is reported there instead.
    #
    # It also requires roll to be the ONLY thing moving. In a sweep where the
    # rack ramps alongside the roll (10_corner_ramp), np.gradient(camber, roll)
    # is a derivative along the path, dominated by the camber change from
    # steering about the KPI/caster axis rather than by roll. On Aurora that
    # reads +1.25 deg/deg against the -0.07 the roll sweep gives - a different
    # quantity wearing the same name. So skip it when the rack moves.
    if "roll" in d.columns and not _steers(sw):
        r = d["roll"].to_numpy(float)
        if np.ptp(r) > 1e-6:
            for side in ("left", "right"):
                if f"camber_{side}" in d.columns:
                    d[f"camber_recovery_{side}"] = np.gradient(
                        d[f"camber_{side}"].to_numpy(float), r)
                    sw.units[f"camber_recovery_{side}"] = "deg/deg"

    # --- Ackermann -----------------------------------------------------
    # Compare the solved inner/outer pair against the geometric ideal for the
    # same outer angle. 100% = true Ackermann, 0% = parallel steer, negative
    # = anti-Ackermann (inner steers less than the outer). Only defined where
    # the rack actually moves: with the rack centred both the actual and the
    # ideal inner-minus-outer difference are zero, so the ratio is 0/0.
    steering = _steers(sw)
    if steering and {"steer_angle_left", "steer_angle_right"} <= set(d.columns):
        wb = C.wheelbase_of(geometry)
        track = float(d["track"].iloc[0]) if "track" in d.columns else np.nan
        sl = d["steer_angle_left"].to_numpy(float)
        sr = d["steer_angle_right"].to_numpy(float)
        inner = np.where(sl > 0, sl, sr)
        outer = np.where(sl > 0, sr, sl)
        d["ackermann_error"] = np.abs(inner) - np.abs(outer)
        sw.units["ackermann_error"] = "deg"
        if np.isfinite(wb) and np.isfinite(track) and track > 0:
            with np.errstate(divide="ignore", invalid="ignore"):
                out_rad = np.radians(np.abs(outer))
                safe = np.where(out_rad > 1e-6, out_rad, np.nan)
                inner_arm = np.maximum(wb / np.tan(safe) - track, 1e-9)
                ideal = np.arctan2(wb, inner_arm)
                ideal_delta = np.degrees(ideal) - np.abs(outer)
                actual_delta = np.abs(inner) - np.abs(outer)
                pct = 100.0 * actual_delta / ideal_delta
            # Blank the ratio wherever the denominator is too small to carry
            # it, rather than reporting noise amplified to six figures. Read
            # the range over real lock, not the value near centre.
            pct = np.where(np.abs(ideal_delta) >= ACKERMANN_MIN_IDEAL_DELTA_DEG,
                           pct, np.nan)
            d["ackermann_percent"] = pct
            sw.units["ackermann_percent"] = "%"

    # --- Steering ratio -------------------------------------------------
    # The exported derivative is d(ISO steer)/d(rack y) for one wheel, in
    # deg/mm. Rack +y is toward the left of the car, which steers the wheels
    # right, i.e. to a negative ISO angle - so the raw number is negative by
    # convention, not by error. The report takes its magnitude.
    left_deriv = "deriv_steer_angle_wrt_rack_displacement_left"
    if left_deriv in d.columns and not d[left_deriv].isna().all():
        d["steer_per_rack_abs"] = d[left_deriv].abs()
        sw.units["steer_per_rack_abs"] = "deg/mm"

        # A true steering ratio is unitless: steering-wheel degrees per road-
        # wheel degree. It needs the rack travel per steering-wheel revolution,
        # which is a hardware fact the kinematic model does not know. Report it
        # only when the geometry declares it; stay silent otherwise.
        mm_per_turn = C.rack_travel_per_turn(geometry)
        if mm_per_turn:
            with np.errstate(divide="ignore", invalid="ignore"):
                d["steering_ratio_unitless"] = 360.0 / (
                    mm_per_turn * d["steer_per_rack_abs"].to_numpy(float))
            sw.units["steering_ratio_unitless"] = "-"


def _steers(sw: Sweep) -> bool:
    """Whether the rack actually moves in this sweep."""
    d = sw.data
    if "rack_displacement" not in d.columns or d["rack_displacement"].isna().all():
        return False
    return float(np.ptp(d["rack_displacement"].to_numpy(float))) > 1e-2




# ==========================================================================
# 5. Report notes
# ==========================================================================
def notes(sweeps: list[Sweep], geometry: dict | None) -> list[str]:
    """The conventions section of report.md, for an axle model."""
    out = [
        "Conventions, formulas and the meaningful source sweep for every "
        "channel are documented in `CHARACTERISTICS.md`. The ones that bite "
        "most often:\n",
        "- **Scrub radius** is reported as the signed lateral offset "
        "(`steering_axis_offset_ground`), which is what SUSProg calls scrub "
        "radius. The ISO `scrub_radius` column is an unsigned distance that "
        "includes mechanical trail.",
        "- **Camber is chassis-relative.** The road-relative channel folds "
        "in body roll and is the one the tyre sees.",
        "- **Steering ratio** is |d(ISO steer)/d(rack y)| in deg/mm. The raw "
        "derivative is negative because rack +y is toward the left of the "
        "car, which steers the wheels right. A unitless steering-wheel ratio "
        "is reported only when the geometry declares `rack_travel_per_turn` "
        "or `pinion_radius`.",
        "- **Ackermann is only defined where the rack moves, and only away "
        "from centre.** The formula divides by the ideal inner-minus-outer "
        "difference, which is second order in steer angle and vanishes "
        "straight-ahead, so the percentage is blanked until that difference "
        f"reaches {ACKERMANN_MIN_IDEAL_DELTA_DEG:g} deg (about 6 deg of outer "
        "steer on this geometry). Read the range over real lock, not the "
        "value at design.",
        "- **A roll derivative needs roll to be the only thing moving.** "
        "Camber recovery and the roll-centre migration rates are computed "
        "only where the rack is stationary. In a sweep that ramps roll and "
        "steer together they would be derivatives along the path, dominated "
        "by the camber change from steering rather than by roll, so they are "
        "not reported there. Take them from the roll sweep.",
        "- **Body roll** is a kinematic axle attitude, `atan2(dz between "
        "wheel centres, their horizontal spacing)`, not a solved sprung-mass "
        "attitude. It is identically zero in a parallel bump sweep and is "
        "only reported where the axle actually rolls.",
        "- **Mean wheel-centre travel** (the `heave` column) is the average "
        "of the two wheel-centre vertical displacements. It is not CG "
        "vertical motion, which a grounded-chassis kinematic model cannot "
        "produce. It is reported only where both wheels move equally, where "
        "it equals wheel travel.",
    ]
    if C._degenerate_side_view(sweeps):
        out.append(
            "- **No side-view instant centre on this geometry.** Both "
            "wishbone inboard axes are parallel in side view, so the SVIC is "
            "at infinity and SVSA, anti-dive, anti-lift and anti-squat are "
            "all undefined. That is the correct answer for level arms, not a "
            "failure; tilt an inboard axis and these channels populate. "
            "Anti-dive additionally needs `front_brake_bias` in "
            "`vehicle_config`.")
    out.append(
        "- **FVIC and FVSA are tabulated but not plotted.** They pass "
        "through a singularity when the wishbones go parallel and swing to "
        "10^5 mm. Camber gain is their bounded equivalent "
        "(`camber_gain ~ -57.296 / FVSA` in deg/mm) and is plotted instead.")
    return out


REPORTER = C.Reporter(
    title=TITLE,
    scope="axle",
    channels=CHANNELS,
    presets=PRESETS,
    never_plot=NEVER_PLOT,
    classify=classify,
    add_derived=add_derived,
    preset_for=preset_for,
    notes=notes,
)


if __name__ == "__main__":
    C.main(REPORTER)
