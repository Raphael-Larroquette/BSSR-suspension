#!/usr/bin/env python3
"""
susreport - turn a directory of Suspension Explorer sweep CSVs into a
characteristic report.

Usage:
    python susreport.py outputs/                       # uses run.yaml beside this file
    python susreport.py outputs/ --out report/
    python susreport.py outputs/ --config path/to/run.yaml
    python susreport.py outputs/ --resolved report/_resolved_run.json

There are no built-in defaults: a configuration is required, and a missing or
incomplete one is an error naming the key.

`run_all.py` imports this module and calls `run_report()` directly, so a
breakpoint here is hit by a normal `run_all.py` run. Calling this file as a
script is the same work on a folder of CSVs, and needs nothing from the
`kinematics` package except for the bearing-misalignment section.

What it does that the raw CSV does not:
  * parses the '#' metadata header (format_version, provenance hashes, units)
  * classifies each sweep by what its targets actually do
  * derives the quantities the solver does not export directly
      - road-relative camber          (chassis camber folded with body roll)
      - SIGNED scrub radius           (the exported one is an unsigned magnitude)
      - motion ratio and MR^2
      - Ackermann percentage and error
      - roll-centre migration rates
      - a unitless steering ratio when the geometry declares the rack travel
        per steering-wheel revolution
  * reports each requested channel at design condition and as a range
  * checks solver health and quarantines rows that did not converge
  * writes summary.csv, report.md, joints.csv and a plots/ directory

See RUNNING.md for the configuration keys and CHARACTERISTICS.md for what each
channel means and which sweep is the meaningful source for it.
"""

from __future__ import annotations

import argparse
import json
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Plot styling. Deliberately plain: these are engineering curves for
# cross-checking against another tool, not presentation graphics.
# --------------------------------------------------------------------------
INK = "#1f2933"
C_L = "#2f6fdb"   # left
C_R = "#d1495b"   # right
C_N = "#5c6670"   # neutral / axle-level
C_D = "#8a94a6"   # reference lines


# ==========================================================================
# 0. Configuration
#
# There are no default values in this file. run.yaml is the single source of
# truth for every setting, so a missing or incomplete configuration is an
# error naming the key rather than a silent fallback that makes the report
# disagree with the file you thought you were editing.
#
# The one thing that looks like a default and is not: `report: true` on a
# sweep selects DEFAULT_CHANNELS[<sweep kind>], which is a named preset of
# characteristics, not a fallback for a missing setting. Naming channels
# explicitly in run.yaml overrides it.
# ==========================================================================
REQUIRED_CONFIG = {
    "side": None,
    "decimals": ("mm", "deg", "ratio", "percent"),
    "report": ("joints", "notes", "plots", "gifs"),
    "solver": ("on_bad_solve", "residual_limit"),
    "sweeps": None,
}

# Keys every enabled sweep must carry. A sweep with `run: false` needs only
# `run`, so that switching one off stays a one-line edit.
REQUIRED_SWEEP_KEYS = ("run", "report", "plots")


def _require(config: dict, source: str) -> None:
    """Fail loudly, naming the key, when run.yaml is incomplete."""
    missing: list[str] = []
    for key, children in REQUIRED_CONFIG.items():
        if key not in config:
            missing.append(key)
            continue
        if children is None:
            continue
        if not isinstance(config[key], dict):
            missing.append(f"{key} (must be a mapping)")
            continue
        missing += [f"{key}.{child}" for child in children
                    if child not in config[key]]
    for name, sweep in (config.get("sweeps") or {}).items():
        if not isinstance(sweep, dict):
            missing.append(f"sweeps.{name} (must be a mapping)")
            continue
        if "run" not in sweep:
            missing.append(f"sweeps.{name}.run")
            continue
        if sweep.get("run") is False:
            continue
        missing += [f"sweeps.{name}.{key}" for key in REQUIRED_SWEEP_KEYS
                    if key not in sweep]
    if missing:
        raise SystemExit(
            f"{source}: missing required setting(s): {', '.join(missing)}.\n"
            "There are no built-in defaults - every setting must be present. "
            "See RUNNING.md for the key reference."
        )


def decimals_for_unit(unit: str, decimals: dict) -> int:
    """Map a channel's unit string onto one of the four decimal settings."""
    unit = (unit or "").strip()
    if unit == "mm":
        return int(decimals["mm"])
    if unit == "deg":
        return int(decimals["deg"])
    if unit == "%":
        return int(decimals["percent"])
    return int(decimals["ratio"])


def fmt(value: float | None, unit: str, decimals: dict) -> str:
    """Format one table cell, or '-' when there is nothing to show."""
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "-"
    return f"{value:.{decimals_for_unit(unit, decimals)}f}"


# ==========================================================================
# 1. Channel catalogue
#
# A "channel" is the config-facing name. It resolves to one column (corner
# channels are side-qualified, axle channels are not) or to a left/right pair.
# Adding a characteristic to the report means adding one entry here and
# naming it in run.yaml - nothing else.
# ==========================================================================
@dataclass(frozen=True)
class Channel:
    """One config-facing characteristic and the CSV column(s) behind it."""

    key: str
    label: str
    kind: str            # "corner" | "pair" | "axle"
    column: str          # template; "{side}" is substituted for corner channels
    note: str = ""

    def columns(self, side: str) -> list[tuple[str, str, str]]:
        """Return [(column, series label, colour)] for this channel."""
        if self.kind == "pair":
            return [
                (self.column.format(side="left"), "left", C_L),
                (self.column.format(side="right"), "right", C_R),
            ]
        if self.kind == "corner":
            return [(self.column.format(side=side), self.label, C_L)]
        return [(self.column, self.label, C_N)]


def _corner(key, label, column, note=""):
    return Channel(key, label, "corner", column, note)


def _pair(key, label, column, note=""):
    return Channel(key, label, "pair", column, note)


def _axle(key, label, column, note=""):
    return Channel(key, label, "axle", column, note)


CHANNELS: dict[str, Channel] = {c.key: c for c in [
    # --- corner, single side -------------------------------------------
    _corner("camber", "Camber", "camber_{side}"),
    _corner("camber_road", "Camber, road-relative", "camber_road_{side}"),
    _corner("caster", "Caster", "caster_{side}"),
    _corner("kpi", "Kingpin inclination", "kpi_{side}"),
    _corner("toe", "Toe (positive = toe-in)", "toe_angle_{side}"),
    _corner("steer_angle", "ISO steer angle", "steer_angle_{side}"),
    _corner("scrub_signed", "Scrub radius (signed lateral)",
            "scrub_radius_signed_{side}"),
    _corner("scrub_iso", "Scrub radius (ISO unsigned)", "scrub_radius_{side}"),
    _corner("trail", "Mechanical trail", "mechanical_trail_{side}"),
    _corner("half_track", "Half track", "half_track_{side}"),
    _corner("wheel_travel", "Wheel travel", "wheel_travel_{side}"),
    _corner("damper_length", "Damper length", "damper_length_{side}"),
    _corner("motion_ratio", "Motion ratio (damper/wheel)", "motion_ratio_{side}"),
    _corner("motion_ratio_sq", "Motion ratio squared", "motion_ratio_sq_{side}"),
    _corner("fvic_y", "FVIC lateral (y)", "fvic_y_{side}"),
    _corner("fvic_z", "FVIC height (z)", "fvic_z_{side}"),
    _corner("fvsa", "FVSA length", "fvsa_length_{side}"),
    _corner("svic_x", "SVIC longitudinal (x)", "svic_x_{side}"),
    _corner("svic_z", "SVIC height (z)", "svic_z_{side}"),
    _corner("svsa", "SVSA length", "svsa_length_{side}"),
    _corner("svsa_angle", "SVSA angle", "svsa_angle_{side}"),
    _corner("anti_dive", "Anti-dive", "anti_dive_{side}"),
    _corner("anti_lift", "Anti-lift", "anti_lift_{side}"),
    _corner("anti_squat", "Anti-squat", "anti_squat_{side}"),
    _corner("camber_recovery", "Camber recovery", "camber_recovery_{side}"),

    # --- corner gradients ----------------------------------------------
    _corner("camber_gain", "Camber gain", "deriv_camber_wrt_hub_z_{side}"),
    _corner("bump_steer", "Bump steer rate", "deriv_toe_angle_wrt_hub_z_{side}"),
    _corner("caster_gain", "Caster gain", "deriv_caster_wrt_hub_z_{side}"),
    _corner("kpi_gain", "KPI gain", "deriv_kpi_wrt_hub_z_{side}"),
    _corner("half_track_rate", "Half-track change rate",
            "deriv_half_track_wrt_hub_z_{side}"),
    _corner("recession_rate", "Wheel-centre recession rate",
            "deriv_wheel_center_x_wrt_hub_z_{side}"),
    _corner("damper_rate", "Damper rate vs wheel",
            "deriv_damper_length_wrt_hub_z_{side}"),
    _corner("toe_per_rack", "Toe per rack",
            "deriv_toe_angle_wrt_rack_displacement_{side}"),
    _corner("camber_per_rack", "Camber per rack",
            "deriv_camber_wrt_rack_displacement_{side}"),

    # --- left/right pairs (roll and steer sweeps) ----------------------
    _pair("camber_lr", "Camber (left/right)", "camber_{side}"),
    _pair("camber_road_lr", "Camber, road-relative (left/right)",
          "camber_road_{side}"),
    _pair("caster_lr", "Caster (left/right)", "caster_{side}"),
    _pair("kpi_lr", "Kingpin inclination (left/right)", "kpi_{side}"),
    _pair("toe_lr", "Toe (left/right)", "toe_angle_{side}"),
    _pair("steer_angle_lr", "ISO steer angle (left/right)", "steer_angle_{side}"),
    _pair("scrub_signed_lr", "Scrub radius, signed (left/right)",
          "scrub_radius_signed_{side}"),
    _pair("trail_lr", "Mechanical trail (left/right)", "mechanical_trail_{side}"),
    _pair("half_track_lr", "Half track (left/right)", "half_track_{side}"),
    _pair("wheel_travel_lr", "Wheel travel (left/right)", "wheel_travel_{side}"),
    _pair("damper_length_lr", "Damper length (left/right)", "damper_length_{side}"),
    _pair("motion_ratio_lr", "Motion ratio (left/right)", "motion_ratio_{side}"),
    _pair("camber_recovery_lr", "Camber recovery (left/right)",
          "camber_recovery_{side}"),

    # --- axle ------------------------------------------------------------
    _axle("track", "Track", "track"),
    _axle("track_change", "Track change", "track_change"),
    _axle("track_change_rate", "Track change rate", "track_change_rate"),
    _axle("rc_height", "Roll-centre height", "roll_center_z"),
    _axle("rc_lateral", "Roll-centre lateral position", "roll_center_y"),
    _axle("rc_migration", "Roll-centre migration vs travel", "rc_migration_rate"),
    _axle("rc_migration_roll", "Roll-centre migration vs roll",
          "rc_migration_rate_roll"),
    _axle("rc_lateral_roll", "Roll-centre lateral migration vs roll",
          "rc_lateral_rate_roll"),
    _axle("body_roll", "Body roll", "roll"),
    _axle("mean_wheel_travel", "Mean wheel-centre travel", "heave"),
    _axle("rack", "Rack displacement", "rack_displacement"),
    _axle("ackermann_error", "Ackermann error (inner - outer)", "ackermann_error"),
    _axle("ackermann", "Ackermann", "ackermann_percent"),
    _axle("steering_ratio", "Steering ratio (rack)", "steer_per_rack_abs"),
    _axle("steering_ratio_unitless", "Steering ratio (wheel : road wheel)",
          "steering_ratio_unitless"),
]}


# Default channel list per sweep kind, used when a sweep asks for `report: true`
# without naming channels. These mirror the sets agreed for the Aurora front
# axle; override per sweep in run.yaml when you want something else.
DEFAULT_CHANNELS: dict[str, list[str]] = {
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
    "roll_ramp_at_steer": [
        "camber_lr", "caster_lr", "toe_lr", "scrub_signed", "half_track",
        "track_change", "motion_ratio", "camber_recovery", "rc_height",
        "rc_lateral", "rc_lateral_roll", "body_roll", "rack", "ackermann",
        "steering_ratio",
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
# 2. Loading
# ==========================================================================
@dataclass
class Sweep:
    """One parsed sweep CSV plus its metadata and classification."""

    path: Path
    name: str
    data: pd.DataFrame
    meta: dict[str, str]
    units: dict[str, str]
    joints: list[dict] = field(default_factory=list)
    kind: str = "unknown"
    x_col: str = ""
    x_label: str = ""
    notes: list[str] = field(default_factory=list)
    bad_rows: list[int] = field(default_factory=list)

    def unit(self, col: str) -> str:
        return self.units.get(col, "")

    def has(self, *cols: str) -> bool:
        return all(c in self.data.columns and not self.data[c].isna().all()
                   for c in cols)

    @property
    def good(self) -> pd.DataFrame:
        """The rows that are actually on the constraint manifold."""
        if not self.bad_rows:
            return self.data
        return self.data.drop(index=self.bad_rows)

    @property
    def design_index(self) -> int:
        """Row closest to the design condition.

        Design condition is where the SWEPT quantity passes through its
        authored zero. Picking a column that does not move (e.g. wheel travel
        during a pure steer sweep) would silently return row 0, so prefer the
        sweep's own independent variable and require that it actually varies.

        A damper-stroke sweep is the exception: its abscissa is an absolute
        length (~240 mm), which never passes through zero, so |x| would land on
        the shortest damper rather than the design pose. There the design row is
        the one at zero wheel travel.
        """
        d = self.data
        if self.kind == "damper_stroke":
            candidates = ["wheel_travel_left", "wheel_travel_right", self.x_col]
        else:
            candidates = [self.x_col, "wheel_travel_left", "rack_displacement",
                          "roll"]
        for col in candidates:
            if col and col in d.columns and not d[col].isna().all():
                s = d[col].astype(float)
                if float(s.max() - s.min()) > 1e-3:
                    return int(s.abs().idxmin())
        return len(d) // 2


def read_sweep(path: Path) -> Sweep:
    """Read one sweep CSV, including the '#' metadata header."""
    meta: dict[str, str] = {}
    units: dict[str, str] = {}
    joints: list[dict] = []
    with open(path) as fh:
        for line in fh:
            if not line.startswith("#"):
                break
            body = line[1:].strip()
            if not body or ":" not in body:
                continue
            key, value = body.split(":", 1)
            key, value = key.strip(), value.strip()
            if key == "column_units":
                try:
                    units = json.loads(value)
                except json.JSONDecodeError:
                    pass
            elif key == "joints":
                try:
                    joints = json.loads(value)
                except json.JSONDecodeError:
                    pass
            else:
                meta[key] = value

    data = pd.read_csv(path, comment="#")
    return Sweep(path=path, name=path.stem, data=data, meta=meta, units=units,
                 joints=joints)


# ==========================================================================
# 3. Classification - work out what the sweep actually does
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
                        f"({roll:+.2f} deg roll) - this is a ROLLED sweep."
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


def default_channels_for(sw: Sweep) -> list[str]:
    """The channel list a sweep gets when it says `report: true`."""
    # Longest/most specific kinds first: "steer_in_roll" must not be caught by
    # the "steer" prefix, and "roll_ramp_at_steer" must not be caught by "roll".
    for prefix in ("damper_stroke", "roll_ramp_at_steer", "heave_at_steer",
                   "steer_in_roll", "single_wheel", "steer", "roll", "heave"):
        if sw.kind.startswith(prefix):
            return list(DEFAULT_CHANNELS.get(prefix, DEFAULT_CHANNELS["static"]))
    return list(DEFAULT_CHANNELS["static"])


# ==========================================================================
# 4. Solver health
# ==========================================================================
def check_solver(sw: Sweep, solver_cfg: dict) -> list[str]:
    """Flag non-converged or high-residual rows. Returns human-readable problems.

    `residual_limit` is compared against `solver_max_residual`, the largest
    constraint violation left in that row after the solve, in the constraint's
    own units (mm for length constraints, deg for angular ones). A converged
    Aurora step sits at 1e-6 to 5e-6 mm, i.e. four orders below anything
    geometrically meaningful, so the default 1e-5 flags a solver that limped
    without firing on healthy rows. Rows past the limit are dropped from the
    min/max/range columns so a single bad step cannot set your design envelope,
    but they stay in the CSV.
    """
    mode = str(solver_cfg["on_bad_solve"]).lower()
    if mode == "off":
        return []

    limit = float(solver_cfg["residual_limit"])
    d = sw.data
    problems: list[str] = []
    bad = pd.Series(False, index=d.index)

    if "solver_converged" in d.columns:
        not_converged = ~d["solver_converged"].astype(bool)
        if not_converged.any():
            rows = list(d.index[not_converged])
            problems.append(
                f"{len(rows)} step(s) did not converge: "
                f"{_compact_rows(rows)}"
            )
            bad |= not_converged

    if "solver_max_residual" in d.columns:
        over = d["solver_max_residual"].astype(float) > limit
        over &= ~bad
        if over.any():
            rows = list(d.index[over])
            worst = float(d.loc[over, "solver_max_residual"].max())
            problems.append(
                f"{len(rows)} step(s) over the residual limit "
                f"({limit:g}, worst {worst:.2e}): {_compact_rows(rows)}"
            )
            bad |= over

    sw.bad_rows = list(d.index[bad])
    return problems


def _compact_rows(rows: list[int]) -> str:
    """Render a row-index list as compact ranges."""
    if not rows:
        return "-"
    parts, start, prev = [], rows[0], rows[0]
    for r in rows[1:] + [None]:
        if r is not None and r == prev + 1:
            prev = r
            continue
        parts.append(f"{start}" if start == prev else f"{start}-{prev}")
        if r is not None:
            start = prev = r
    shown = ", ".join(parts[:6])
    return shown + (" ..." if len(parts) > 6 else "")


# ==========================================================================
# 5. Derived channels the solver does not export
# ==========================================================================
def add_derived(sw: Sweep, geometry: dict | None = None) -> None:
    """Append derived columns to the sweep's dataframe."""
    # Columns are added one at a time and several read back the one before, so
    # the frame fragments as we go. That is fine at these sizes; defragment
    # once at the end rather than restructuring the derivation order.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        _add_derived(sw, geometry)
    sw.data = sw.data.copy()


def _add_derived(sw: Sweep, geometry: dict | None) -> None:
    d = sw.data

    for side in ("left", "right"):
        cam = f"camber_{side}"
        sao = f"steering_axis_offset_ground_{side}"
        trail = f"mechanical_trail_{side}"
        dmp = f"damper_length_{side}"

        # --- Road-relative camber -------------------------------------
        # The solver exports camber relative to the CHASSIS. What the tyre
        # actually sees is folded with body roll. Sign: a positive ISO roll
        # angle rolls the body, so the road-relative inclination of a wheel
        # is the chassis camber minus the roll angle.
        if cam in d.columns and "roll" in d.columns:
            d[f"camber_road_{side}"] = d[cam] - d["roll"]
            sw.units[f"camber_road_{side}"] = "deg"

        # --- Signed scrub radius --------------------------------------
        # `scrub_radius` in the CSV is the ISO 8855 unsigned road-plane
        # DISTANCE, i.e. hypot(lateral offset, mechanical trail), so it is
        # inflated by caster trail and can never go negative. The number most
        # tools (and Milliken) call "scrub radius" is the signed LATERAL
        # component, positive when the steering axis meets the ground inboard
        # of the contact centre. `steering_axis_offset_ground` already uses
        # exactly that sign convention, so this is an alias, not a negation.
        if sao in d.columns:
            d[f"scrub_radius_signed_{side}"] = d[sao]
            sw.units[f"scrub_radius_signed_{side}"] = "mm"

        # Consistency check on the two definitions.
        iso = f"scrub_radius_{side}"
        if sao in d.columns and trail in d.columns and iso in d.columns:
            recon = np.hypot(d[sao], d[trail])
            err = float(np.nanmax(np.abs(recon - d[iso])))
            if err > 1e-3:
                sw.notes.append(
                    f"scrub_radius_{side} does not reconstruct from "
                    f"hypot(offset, trail) (max err {err:.3g} mm)."
                )

        # --- Motion ratio ---------------------------------------------
        # MR = -d(damper length)/d(wheel centre z). Prefer the analytic
        # derivative; fall back to a numerical gradient.
        an = f"deriv_damper_length_wrt_hub_z_{side}"
        if an in d.columns and not d[an].isna().all():
            d[f"motion_ratio_{side}"] = -d[an]
            sw.units[f"motion_ratio_{side}"] = "mm/mm"
        elif dmp in d.columns and f"wheel_travel_{side}" in d.columns:
            z = d[f"wheel_travel_{side}"].to_numpy(float)
            if np.ptp(z) > 1e-6:
                d[f"motion_ratio_{side}"] = -np.gradient(
                    d[dmp].to_numpy(float), z)
                sw.units[f"motion_ratio_{side}"] = "mm/mm"
        if f"motion_ratio_{side}" in d.columns:
            # Spring/damper force and rate scale with MR^2 at the wheel.
            d[f"motion_ratio_sq_{side}"] = d[f"motion_ratio_{side}"] ** 2
            sw.units[f"motion_ratio_sq_{side}"] = "-"

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
        if "roll" in d.columns:
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
    if "roll" in d.columns:
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
        wb = _wheelbase_guess(sw, geometry)
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
        mm_per_turn = _rack_travel_per_turn(geometry)
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


def _geometry_path(sw: Sweep) -> Path | None:
    """Best guess at the geometry file this sweep was run against."""
    declared = sw.meta.get("geometry_path", "")
    candidates = [Path(declared)]
    if declared:
        # The header may carry a Windows path from another machine.
        name = declared.replace("\\", "/").rsplit("/", 1)[-1]
        candidates.append(sw.path.parent.parent / name)
    candidates.append(sw.path.parent.parent / "front.yaml")
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def load_geometry_dict(sw: Sweep) -> dict | None:
    """Load the geometry YAML next to the sweep, when it can be found."""
    path = _geometry_path(sw)
    if path is None:
        return None
    try:
        import yaml
        return yaml.safe_load(path.read_text())
    except Exception:
        return None


def _wheelbase_guess(sw: Sweep, geometry: dict | None) -> float:
    """Wheelbase is not exported; recover it from the geometry file."""
    if isinstance(geometry, dict):
        config = geometry.get("vehicle_config") or {}
        value = config.get("wheelbase")
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    path = _geometry_path(sw)
    if path is not None:
        try:
            for line in path.read_text().splitlines():
                if "wheelbase" in line:
                    return float(line.split(":")[1].split("#")[0].strip())
        except (OSError, ValueError, IndexError):
            pass
    return float("nan")


def _rack_travel_per_turn(geometry: dict | None) -> float | None:
    """Rack millimetres per steering-wheel revolution, if the geometry says.

    Accepts either an explicit `rack_travel_per_turn` or a `pinion_radius`,
    from which the travel per revolution is 2*pi*r.
    """
    if not isinstance(geometry, dict):
        return None
    for container in (geometry.get("vehicle_config") or {},
                      (geometry.get("vehicle_config") or {}).get("steering") or {},
                      geometry.get("steering") or {}):
        if not isinstance(container, dict):
            continue
        value = container.get("rack_travel_per_turn")
        if value:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
        radius = container.get("pinion_radius")
        if radius:
            try:
                return 2.0 * math.pi * float(radius)
            except (TypeError, ValueError):
                pass
    return None


# ==========================================================================
# 6. Characteristic extraction
# ==========================================================================
def summarise(sw: Sweep, side: str, keys: list[str]) -> pd.DataFrame:
    """Build a tidy summary table for one sweep, in the configured order."""
    d = sw.data
    good = sw.good
    i0 = sw.design_index
    rows = []

    for key in keys:
        channel = CHANNELS.get(key)
        if channel is None:
            continue
        for col, label, _colour in channel.columns(side):
            if col not in d.columns or d[col].isna().all():
                continue
            full = d[col].astype(float)
            clean = good[col].astype(float) if col in good.columns else full
            clean = clean.replace([np.inf, -np.inf], np.nan).dropna()
            if clean.empty:
                continue
            name = (f"{channel.label.split(' (left/right)')[0]} ({label})"
                    if channel.kind == "pair" else channel.label)
            at_design = full.iloc[i0] if i0 in full.index else np.nan
            rows.append({
                "channel": key,
                "characteristic": name,
                "column": col,
                "unit": sw.unit(col),
                "at_design": at_design,
                "min": clean.min(),
                "max": clean.max(),
                "range": clean.max() - clean.min(),
                "at_start": full.iloc[0],
                "at_end": full.iloc[-1],
            })

    out = pd.DataFrame(rows)
    if not out.empty:
        out.insert(0, "sweep", sw.name)
        out.insert(1, "kind", sw.kind)
    return out


# ==========================================================================
# 7. Plots
# ==========================================================================
def plot_sweep(sw: Sweep, side: str, keys: list[str], outdir: Path) -> list[Path]:
    """Emit one figure per sweep, one panel per requested channel."""
    d = sw.data
    if not keys:
        return []
    x = d[sw.x_col].astype(float) if sw.x_col in d.columns else d.index.to_series()

    panels: list[tuple[str, list[tuple[str, str, str]], str]] = []
    for key in keys:
        channel = CHANNELS.get(key)
        if channel is None:
            continue
        series = [s for s in channel.columns(side)
                  if s[0] in d.columns and not d[s[0]].isna().all()]
        if not series:
            continue
        title = channel.label.replace(" (left/right)", "")
        panels.append((title, series, sw.unit(series[0][0])))

    if not panels:
        return []

    ncol = 3
    nrow = math.ceil(len(panels) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.7 * ncol, 3.3 * nrow),
                             squeeze=False)
    fig.suptitle(f"{sw.name}  [{sw.kind}]", fontsize=13, color=INK)

    for ax, (title, series, unit) in zip(axes.flat, panels):
        for col, label, colour in series:
            ax.plot(x, d[col].astype(float), color=colour, lw=1.8, label=label)
        ax.set_title(title, fontsize=10, color=INK)
        ax.set_xlabel(sw.x_label, fontsize=8)
        ax.set_ylabel(unit, fontsize=8)
        ax.grid(True, alpha=0.25)
        # Only draw the zero line when zero is actually near the data, so a
        # channel like damper length is not squashed against the top of the
        # panel just to keep an irrelevant y=0 in frame.
        vals = np.concatenate([d[c].astype(float).dropna().to_numpy()
                               for c, _, _ in series]) if series else np.array([])
        vals = vals[np.isfinite(vals)]
        if vals.size and np.ptp(vals) > 0:
            pad = 0.15 * float(np.ptp(vals))
            if vals.min() - pad <= 0 <= vals.max() + pad:
                ax.axhline(0, color=C_D, lw=0.7)
        if len(series) > 1:
            ax.legend(fontsize=8)
    for ax in axes.flat[len(panels):]:
        ax.axis("off")

    fig.tight_layout()
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{sw.name}.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return [path]


# ==========================================================================
# 8. Bearing misalignment
#
# The sweeps export the relative rotation Q(t) of the two bodies meeting at
# each declared joint, which is independent of the bearing axes. So every
# question about axes -- what a declared one costs, what the best available
# one costs, how a rod end should be clocked -- is answered here from the CSVs
# alone, with no re-solving.
# ==========================================================================
@dataclass
class JointResult:
    """One joint's misalignment demand across every sweep in the set."""

    name: str
    label: str
    type: str
    side: str
    description: str
    install_offset: float | None
    required: float | None = None
    peak_sweep: str = ""
    peak_step: int = -1
    optimal_axis: np.ndarray | None = None
    optimal_required: float | None = None
    optimal_clocking: float | None = None
    locked_required: float | None = None
    locked_clocking_deg: float | None = None
    note: str = ""

    @property
    def demand_word(self) -> str:
        """Return what this part's reported angle is called."""
        return "conical deflection" if self.type == "bushing" else "misalignment"


def _joint_column(sweep: Sweep, stem: str, side: str) -> str | None:
    """Find a joint column, tolerating corner models that carry no side."""
    for candidate in (f"{stem}_{side}", stem):
        if candidate in sweep.data.columns:
            return candidate
    return None


def _relative_rotations(sweep: Sweep, name: str, side: str) -> np.ndarray | None:
    """Rebuild the per-step relative rotation stack for one joint."""
    from kinematics.core.joints import rotation_from_rotvec

    columns = [
        _joint_column(sweep, f"joint_{name}_r{axis}", side) for axis in "xyz"
    ]
    if any(column is None for column in columns):
        return None
    rotvecs = np.radians(sweep.data[columns].to_numpy(dtype=float))
    if not np.isfinite(rotvecs).all():
        return None
    return np.stack([rotation_from_rotvec(vector) for vector in rotvecs])


def analyse_joints(sweeps: list[Sweep], side: str) -> list[JointResult]:
    """Reduce every declared joint across the whole sweep set.

    The required angle is the worst the joint sees anywhere in the set, not
    per sweep: a bearing has to survive all of it. The optimiser runs over the
    same concatenated set for the same reason -- an axis chosen against one
    sweep is not a design answer. Sweeps switched off in run.yaml are not in
    this list, so turning a sweep off can lower a bearing requirement; check
    the "at" column to see which sweep is binding before you disable one.
    """
    from kinematics.core.joints import locked_clocking, optimize_bore_axis

    declared: dict[str, dict] = {}
    for sweep in sweeps:
        for entry in sweep.joints:
            if entry.get("side", side) != side and "side" in entry:
                continue
            declared.setdefault(entry["name"], entry)
    if not declared:
        return []

    results: list[JointResult] = []
    for name, entry in declared.items():
        result = JointResult(
            name=name,
            label=entry.get("label", name),
            type=entry.get("type", "spherical"),
            side=side,
            description=entry.get("description", ""),
            install_offset=entry.get("install_offset_deg"),
        )

        # Required angle against the declared axis, worst step of any sweep.
        column_stem = f"misalign_{name}"
        for sweep in sweeps:
            column = _joint_column(sweep, column_stem, side)
            if column is None:
                continue
            series = sweep.data[column].astype(float)
            if series.isna().all():
                continue
            peak = float(series.max())
            if result.required is None or peak > result.required:
                result.required = peak
                result.peak_sweep = sweep.name
                result.peak_step = int(series.idxmax())

        stacks = [
            stack
            for stack in (_relative_rotations(sweep, name, side) for sweep in sweeps)
            if stack is not None
        ]
        if not stacks:
            result.note = "no relative-rotation columns in these sweeps"
            results.append(result)
            continue
        relative = np.concatenate(stacks)

        housing_mode = entry.get("housing_mode", "centred")
        housing_axis = entry.get("housing_axis")
        spin_axis = entry.get("spin_axis")
        cone = float(entry.get("cone_deg", 90.0))

        # The best axis available, reported whether or not one was declared:
        # a bearing sized off a poorly chosen axis costs range for nothing.
        axis, best = optimize_bore_axis(
            relative,
            housing_mode,
            None if housing_axis is None else np.asarray(housing_axis, float),
            None if spin_axis is None else np.asarray(spin_axis, float),
            cone,
            entry.get("bore_perpendiculars") or (),
        )
        result.optimal_axis = axis
        result.optimal_required = best
        perpendiculars = entry.get("bore_perpendiculars") or ()
        if len(perpendiculars) == 1:
            pole = np.asarray(perpendiculars[0], float)
            result.optimal_clocking = _clocking_of(axis, pole, cone)

        # An indeterminate housing's own figure assumes the member spins
        # freely to the best position at every instant, which is a lower
        # bound. Pair it with the no-spin value so the band is visible.
        if housing_mode == "indeterminate" and entry.get("bore_axis") is not None:
            clocking, locked = locked_clocking(
                relative, np.asarray(entry["bore_axis"], float),
                np.asarray(spin_axis, float), cone,
            )
            result.locked_clocking_deg = clocking
            result.locked_required = locked

        results.append(result)
    return results


def _clocking_of(axis: np.ndarray, pole: np.ndarray, cone_deg: float) -> float:
    """Return the clocking angle of a direction on its cone, in degrees."""
    from kinematics.core.joints import circle_directions

    directions, clocking = circle_directions(pole, count=3600, cone_deg=cone_deg)
    return float(clocking[int(np.argmax(directions @ axis))])


# ==========================================================================
# 9. Report
# ==========================================================================
def _degenerate_side_view(sweeps: list[Sweep]) -> bool:
    """True when no sweep has a finite side-view instant centre."""
    seen = False
    for sw in sweeps:
        for col in ("svic_x_left", "svic_x_right", "svic_z_left", "svic_z_right"):
            if col in sw.data.columns:
                seen = True
                if not sw.data[col].isna().all():
                    return False
    return seen


def write_report(sweeps: list[Sweep], summary: pd.DataFrame, side: str,
                 out: Path, plots: list[Path], joints: list[JointResult] | None,
                 config: dict, problems: dict[str, list[str]]) -> Path:
    joints = joints or []
    decimals = config["decimals"]
    report_cfg = config["report"]
    lines: list[str] = []
    lines.append("# Suspension characteristic report\n")

    first = sweeps[0]
    lines.append("## Provenance\n")
    lines.append(f"- geometry: `{first.meta.get('geometry_path','?')}`")
    lines.append(f"- geometry SHA-256: `{first.meta.get('geometry_hash','?')[:16]}...`")
    lines.append(f"- format version: {first.meta.get('format_version','?')}")
    lines.append(f"- reported side: **{side}**")
    if config.get("config_path"):
        lines.append(f"- run configuration: `{config['config_path']}`")
    lines.append("")

    hashes = {s.meta.get("geometry_hash", "") for s in sweeps}
    if len(hashes) > 1:
        lines.append("> **WARNING:** these sweeps were not all run against the "
                     "same geometry file. The summary below mixes models.\n")

    flagged = {name: msgs for name, msgs in problems.items() if msgs}
    if flagged:
        lines.append("> **SOLVER WARNING** - some steps are not on the constraint "
                     "manifold. They stay in the CSV but are excluded from the "
                     "min/max/range columns below.\n")
        for name, msgs in flagged.items():
            for msg in msgs:
                lines.append(f"> - `{name}`: {msg}")
        lines.append("")

    lines.append("## Sweeps\n")
    lines.append("| file | kind | steps | converged | max residual | notes |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for s in sweeps:
        d = s.data
        conv = bool(d["solver_converged"].all()) if "solver_converged" in d else True
        res = (d["solver_max_residual"].max() if "solver_max_residual" in d
               else float("nan"))
        lines.append(f"| `{s.name}` | {s.kind} | {len(d)} | {conv} | "
                     f"{res:.2e} | {' '.join(s.notes) or '-'} |")
    lines.append("")

    if report_cfg["notes"]:
        lines.append("## Notes\n")
        lines.append(
            "Conventions, formulas and the meaningful source sweep for every "
            "channel are documented in `CHARACTERISTICS.md`. The ones that bite "
            "most often:\n"
        )
        lines.append(
            "- **Scrub radius** is reported as the signed lateral offset "
            "(`steering_axis_offset_ground`), which is what SUSProg calls scrub "
            "radius. The ISO `scrub_radius` column is an unsigned distance that "
            "includes mechanical trail."
        )
        lines.append(
            "- **Camber is chassis-relative.** The road-relative channel folds "
            "in body roll and is the one the tyre sees."
        )
        lines.append(
            "- **Steering ratio** is |d(ISO steer)/d(rack y)| in deg/mm. The raw "
            "derivative is negative because rack +y is toward the left of the "
            "car, which steers the wheels right. A unitless steering-wheel ratio "
            "is reported only when the geometry declares "
            "`rack_travel_per_turn` or `pinion_radius`."
        )
        lines.append(
            "- **Ackermann is only defined where the rack moves.** With the rack "
            "centred the actual and ideal inner-minus-outer differences are both "
            "zero, so the percentage is 0/0 and is not reported."
        )
        lines.append(
            "- **Body roll** is a kinematic axle attitude, "
            "`atan2(dz between wheel centres, their horizontal spacing)`, not a "
            "solved sprung-mass attitude. It is identically zero in a parallel "
            "bump sweep and is only reported where the axle actually rolls."
        )
        lines.append(
            "- **Mean wheel-centre travel** (the `heave` column) is the average "
            "of the two wheel-centre vertical displacements. It is not CG "
            "vertical motion, which a grounded-chassis kinematic model cannot "
            "produce. It is reported only where both wheels move equally, where "
            "it equals wheel travel."
        )
        if _degenerate_side_view(sweeps):
            lines.append(
                "- **No side-view instant centre on this geometry.** Both "
                "wishbone inboard axes are parallel in side view, so the SVIC is "
                "at infinity and SVSA, anti-dive, anti-lift and anti-squat are "
                "all undefined. That is the correct answer for level arms, not a "
                "failure; tilt an inboard axis and these channels populate. "
                "Anti-dive additionally needs `front_brake_bias` in "
                "`vehicle_config`."
            )
        lines.append(
            "- **FVIC and FVSA are tabulated but not plotted.** They pass "
            "through a singularity when the wishbones go parallel and swing to "
            "10^5 mm. Camber gain is their bounded equivalent "
            "(`camber_gain ~ -57.296 / FVSA` in deg/mm) and is plotted instead."
        )
        lines.append("")

    for s in sweeps:
        sub = summary[summary["sweep"] == s.name] if not summary.empty else summary
        if sub.empty:
            continue
        lines.append(f"## {s.name}  ({s.kind})\n")
        lines.append("| characteristic | unit | at design | min | max | range |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for _, r in sub.iterrows():
            unit = r["unit"]
            lines.append(
                f"| {r['characteristic']} | {unit} | "
                f"{fmt(r['at_design'], unit, decimals)} | "
                f"{fmt(r['min'], unit, decimals)} | "
                f"{fmt(r['max'], unit, decimals)} | "
                f"{fmt(r['range'], unit, decimals)} |")
        lines.append("")
        figure = out / "plots" / f"{s.name}.png"
        if figure.exists():
            lines.append(f"Plots: `plots/{figure.name}`\n")

    if joints and report_cfg["joints"]:
        lines.append("## Bearing misalignment\n")
        lines.append(
            "Required angle is the worst value anywhere in this sweep set, not "
            "per sweep, and only over the sweeps that actually ran. Install "
            "offset is the angle between the housing and bore directions at the "
            "neutral pose: non-zero means the bearing is fitted deliberately off "
            "centre and starts already eating part of its cone. Best available "
            "is what the joint would need if its bore axis were chosen to "
            "minimise the worst case.\n"
        )
        lines.append(
            "**Size against `required (locked)` where it is populated.** Those "
            "housings ride a two-point member whose roll about its own axis no "
            "kinematic model can determine. The plain `required` column is a "
            "lower bound that assumes the member turns freely to the best "
            "position at every instant; the locked column assumes it never "
            "turns, so one clocking chosen at assembly serves the whole sweep.\n"
        )
        lines.append(
            "| joint | part | required (deg) | at | required (locked) (deg) "
            "| locked clocking (deg) | install offset (deg) "
            "| best available (deg) | clocking (deg) |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for j in joints:
            required = "-" if j.required is None else f"{j.required:.2f}"
            where = f"`{j.peak_sweep}` step {j.peak_step}" if j.peak_sweep else "-"
            locked = ("-" if j.locked_required is None
                      else f"{j.locked_required:.2f}")
            locked_clock = ("-" if j.locked_clocking_deg is None
                            else f"{j.locked_clocking_deg:.1f}")
            offset = "-" if j.install_offset is None else f"{j.install_offset:.2f}"
            best = "-" if j.optimal_required is None else f"{j.optimal_required:.2f}"
            clock = "-" if j.optimal_clocking is None else f"{j.optimal_clocking:.1f}"
            lines.append(f"| {j.label} | {j.type} | {required} | {where} | "
                         f"{locked} | {locked_clock} | {offset} | {best} | {clock} |")
        lines.append("")

    if plots:
        lines.append("## Plots\n")
        for p in plots:
            lines.append(f"- `plots/{p.name}`")
        lines.append("")

    path = out / "report.md"
    path.write_text("\n".join(lines))
    return path


# ==========================================================================
# 10. Configuration loading
# ==========================================================================
def load_config(config_path: Path | None, resolved_path: Path | None) -> dict:
    """Load and validate the configuration. There is no implicit fallback.

    `--resolved` is the JSON that run_all writes after merging run.yaml with
    the command-line overrides; it is the authoritative record of what actually
    ran. `--config` reads run.yaml directly and is the hand-invocation path.
    With neither given, run.yaml beside this script is used. With no
    configuration at all this raises, rather than inventing values.
    """
    source: Path | None = None
    raw: dict | None = None

    if resolved_path is not None:
        if not resolved_path.is_file():
            raise SystemExit(f"resolved configuration not found: {resolved_path}")
        source = resolved_path
        raw = json.loads(resolved_path.read_text())
    else:
        source = config_path if config_path is not None else HERE / "run.yaml"
        if not source.is_file():
            raise SystemExit(
                f"configuration not found: {source}\n"
                "susreport has no built-in defaults. Pass --config with a "
                "run.yaml, or --resolved with the JSON run_all writes."
            )
        import yaml
        raw = yaml.safe_load(source.read_text()) or {}

    if not isinstance(raw, dict):
        raise SystemExit(f"{source}: configuration must be a mapping")

    config = dict(raw)
    config["config_path"] = str(source)
    config.setdefault("sweeps", {})
    # Name run.yaml in the error, not the generated JSON: run.yaml is the file
    # the reader would have to edit to fix it.
    _require(config, str(config.get("source_config") or source))
    return config


def channels_for(sw: Sweep, config: dict) -> tuple[list[str], list[str]]:
    """Return (report channels, plot channels) for one sweep."""
    sweep_cfg = (config.get("sweeps") or {}).get(sw.name) or {}
    report_cfg = config["report"]

    # A sweep marked `run: false` may still have a stale CSV on disk from an
    # earlier run. run_all filters those out by its `ran` list, but susreport
    # called by hand has only run.yaml to go on - so honour `run` here too.
    if sweep_cfg.get("run") is False:
        return [], []

    wanted = sweep_cfg["report"]
    if wanted is False or wanted == "none":
        return [], []
    if wanted is True or wanted == "all":
        keys = default_channels_for(sw)
    else:
        keys = [str(k) for k in wanted]
    keys = [k for k in keys if k in CHANNELS]

    master = str(report_cfg["plots"]).lower()
    if master in ("false", "none", "off"):
        return keys, []

    wanted_plots = sweep_cfg["plots"]
    if master in ("true", "all", "on"):
        wanted_plots = "all"
    if wanted_plots is False or wanted_plots == "none":
        return keys, []
    if wanted_plots is True or wanted_plots == "all":
        plot_keys = [k for k in keys if k not in NEVER_PLOT]
    else:
        plot_keys = [str(k) for k in wanted_plots if str(k) in CHANNELS]
    return keys, plot_keys


# ==========================================================================
# 11. Entry point
# ==========================================================================
def run_report(indir: Path, out: Path, config: dict,
               side: str | None = None) -> Path:
    """Build the report from a directory of sweep CSVs. Returns report.md.

    This is the whole of susreport's work, callable directly: `run_all.py`
    imports it rather than launching a second Python, so tracebacks and
    breakpoints land in the calling process.

    Args:
        indir: directory of solved sweep CSVs.
        out: directory to write report.md, summary.csv, joints.csv and plots/.
        config: a validated configuration from `load_config`.
        side: override the configured reported corner.
    """
    side = side or config["side"]
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(indir.glob("*.csv"))
    # A sweep switched off in run.yaml leaves its old CSV on disk. Reporting it
    # would quietly resurrect stale numbers and, worse, let a disabled sweep
    # keep setting bearing requirements - so honour the list of sweeps that
    # actually ran when run_all supplied one.
    ran = config.get("ran")
    if ran:
        files = [f for f in files if f.stem in set(ran)]
    if not files:
        raise SystemExit(f"no CSVs in {indir}")

    sweeps: list[Sweep] = []
    frames: list[pd.DataFrame] = []
    plots: list[Path] = []
    problems: dict[str, list[str]] = {}
    fail_mode = str(config["solver"]["on_bad_solve"]).lower() == "fail"

    for f in files:
        sw = read_sweep(f)
        classify(sw)
        problems[sw.name] = check_solver(sw, config["solver"])
        add_derived(sw, load_geometry_dict(sw))
        sweeps.append(sw)

        report_keys, plot_keys = channels_for(sw, config)
        if report_keys:
            frames.append(summarise(sw, side, report_keys))
        if plot_keys:
            plots += plot_sweep(sw, side, plot_keys, out / "plots")
        shown = "reported" if report_keys else "solved only"
        print(f"  {f.name:30s} -> {sw.kind:22s} ({shown})")
        for msg in problems[sw.name]:
            print(f"      ! {msg}")

    if fail_mode and any(problems.values()):
        raise SystemExit(
            "solver.on_bad_solve is 'fail' and at least one sweep has bad steps."
        )

    non_empty = [f for f in frames if not f.empty]
    summary = (pd.concat(non_empty, ignore_index=True) if non_empty
               else pd.DataFrame())
    summary.to_csv(out / "summary.csv", index=False)

    joints: list[JointResult] = []
    if config["report"]["joints"]:
        try:
            joints = analyse_joints(sweeps, side)
        except ImportError as error:
            print(f"  ! bearing misalignment skipped: {error}")
    if joints:
        pd.DataFrame(
            [
                {
                    "joint": j.label,
                    "name": j.name,
                    "type": j.type,
                    "side": j.side,
                    "required_deg": j.required,
                    "peak_sweep": j.peak_sweep,
                    "peak_step": j.peak_step,
                    "install_offset_deg": j.install_offset,
                    "best_available_deg": j.optimal_required,
                    "best_available_clocking_deg": j.optimal_clocking,
                    "best_available_axis": None
                    if j.optimal_axis is None
                    else ",".join(f"{c:.6f}" for c in j.optimal_axis),
                    "locked_required_deg": j.locked_required,
                    "locked_clocking_deg": j.locked_clocking_deg,
                    "resolution": j.description,
                    "note": j.note,
                }
                for j in joints
            ]
        ).to_csv(out / "joints.csv", index=False)

    report = write_report(sweeps, summary, side, out, plots, joints, config,
                          problems)

    print(f"\n  {len(summary)} characteristics extracted")
    print(f"  summary : {out/'summary.csv'}")
    print(f"  report  : {report}")
    print(f"  plots   : {out/'plots'} ({len(plots)} figures)")
    if joints:
        print(f"  joints  : {out/'joints.csv'} ({len(joints)} declared)")
    return report


# ==========================================================================
# 12. Command-line entry point
# ==========================================================================
def main() -> None:
    """Parse arguments, load the configuration, and build the report."""
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("indir", type=Path, help="directory of sweep CSVs")
    ap.add_argument("--out", type=Path, default=None, help="output directory")
    ap.add_argument("--side", default=None, choices=("left", "right"))
    ap.add_argument("--config", type=Path, default=None,
                    help="run.yaml to read channel selection and formatting "
                         "from (default: run.yaml beside this script)")
    ap.add_argument("--resolved", type=Path, default=None,
                    help="resolved JSON configuration written by run_all.py")
    ap.add_argument("--no-joints", action="store_true",
                    help="skip the bearing misalignment section")
    args = ap.parse_args()

    config = load_config(args.config, args.resolved)
    if args.no_joints:
        config["report"]["joints"] = False
    out = args.out or args.indir.parent / "report"
    run_report(args.indir, out, config, side=args.side)


if __name__ == "__main__":
    main()
