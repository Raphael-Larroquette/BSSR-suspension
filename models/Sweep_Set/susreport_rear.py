#!/usr/bin/env python3
"""
susreport_rear - characteristic report for a SINGLE CORNER (Aurora rear).

    uv run python models/Sweep_Set/susreport_rear.py <outputs dir> --out <dir>

Aurora's rear is one trailing-arm corner on the vehicle centreline, not an
axle, and that changes what there is to report:

  * its CSV columns carry no side suffix - `damper_length`, not
    `damper_length_left`
  * there is no track, no body roll, no roll centre, no rack and no Ackermann,
    because every one of those is built from two wheels
  * a wheel on the centreline has no inboard or outboard, so the solver emits
    no camber, toe, caster, KPI, scrub radius, half track or front-view swing
    arm for it at all - those columns are absent from the CSV, not blank
  * the side-view family - SVIC, SVSA, anti-squat, anti-lift - finally means
    something, because a trailing arm's side-view instant centre IS its pivot
    axis. On the front's exactly-parallel wishbones those are all undefined.

So this is a different report, not the front's with rows removed. What it
shares with the front - CSV parsing, solver health, tables, plots, report
assembly - lives in `susreport_common.py`, and the bearing misalignment
analysis lives in `bearings.py`, so a fix there reaches both.

There are no built-in defaults: a configuration is required, and a missing or
incomplete one is an error naming the key.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

import susreport_common as C
from susreport_common import Channel, Sweep, single

TITLE = "Rear corner characteristic report"


# ==========================================================================
# 1. Channel catalogue
#
# A corner's columns are unsuffixed, so "{side}" always resolves to "". The
# template is kept for symmetry with the axle catalogue and so that a future
# sided corner needs no change here.
# ==========================================================================
CHANNELS: dict[str, Channel] = {c.key: c for c in [
    # --- travel and springing -------------------------------------------
    single("wheel_travel", "Wheel travel", "wheel_travel{side}"),
    single("damper_length", "Damper length", "damper_length{side}"),
    single("motion_ratio", "Motion ratio (damper/wheel)", "motion_ratio{side}"),
    single("motion_ratio_sq", "Motion ratio squared", "motion_ratio_sq{side}"),

    # --- side view: the reason this model is interesting -----------------
    single("svic_x", "SVIC longitudinal (x)", "svic_x{side}"),
    single("svic_z", "SVIC height (z)", "svic_z{side}"),
    single("svsa", "SVSA length", "svsa_length{side}"),
    single("svsa_angle", "SVSA angle", "svsa_angle{side}"),
    single("anti_squat", "Anti-squat", "anti_squat{side}"),
    single("anti_lift", "Anti-lift", "anti_lift{side}"),
    single("anti_dive", "Anti-dive", "anti_dive{side}"),

    # --- gradients -------------------------------------------------------
    single("recession_rate", "Wheel-centre recession rate",
           "deriv_wheel_center_x_wrt_hub_z{side}"),
    single("damper_rate", "Damper rate vs wheel",
           "deriv_damper_length_wrt_hub_z{side}"),
]}


# Channel lists used when a sweep asks for `report: true` without naming any.
PRESETS: dict[str, list[str]] = {
    # Wheel travel commanded, damper read. The design reference for the arm.
    "heave": [
        "wheel_travel", "damper_length", "motion_ratio",
        "recession_rate",
        "svic_x", "svic_z", "svsa", "svsa_angle", "anti_squat", "anti_lift",
    ],
    # Damper length commanded, wheel read. Where the usable travel comes from.
    "damper_stroke": [
        "damper_length", "wheel_travel", "motion_ratio",
    ],
    "static": ["wheel_travel", "damper_length", "svsa_angle"],
}

# Tabulated but never plotted: the instant centres are a fixed point on the
# pivot axis and plot as flat lines, and SVSA length is SVSA angle's unbounded
# twin. Wheel travel is the x-axis of every heave plot.
NEVER_PLOT = {"svic_x", "svic_z", "svsa", "wheel_travel"}


# ==========================================================================
# 2. Classification
#
# A corner's target columns carry no side. An unsteered corner has exactly one
# degree of freedom, so in practice there are two sweeps: drive the wheel and
# read the damper, or drive the damper and read the wheel.
# ==========================================================================
def classify(sw: Sweep) -> None:
    """Infer the sweep type from how its target columns vary."""
    d = sw.data
    targets = [c for c in d.columns if c.startswith("target_")]
    spans = {c: float(d[c].max() - d[c].min()) for c in targets
             if not d[c].isna().all()}
    biggest = max(spans.values(), default=0.0)
    threshold = max(1e-2, 0.01 * biggest)

    def varies(coordinate: str) -> bool:
        """Whether the named target coordinate moves in this sweep.

        Some target columns are exported with the side the geometry publishes
        the coordinate on appended (`target_damper_length_center`) and some
        without it, so match on the coordinate name and ignore any suffix.
        """
        return any(
            span > threshold
            for column, span in spans.items()
            if column == coordinate or column.startswith(coordinate + "_")
        )

    if varies("target_damper_length"):
        sw.kind = "damper_stroke"
        sw.x_col = "damper_length"
        sw.x_label = "damper length [mm]"
        sw.notes.append(
            "Driven by damper length, so the wrt_hub_z analytic derivatives "
            "are absent. Gradients here are finite-differenced by this parser."
        )
    elif varies("target_wheel_center_z"):
        sw.kind = "heave"
        sw.x_col = "wheel_travel"
        sw.x_label = "wheel travel [mm]"
    else:
        sw.kind = "static"
        sw.x_col = "step_index"
        sw.x_label = "step"

    if sw.x_col not in d.columns:
        sw.x_col = "step_index"


def preset_for(sw: Sweep) -> list[str]:
    """The channel list a sweep gets when it says `report: true`."""
    return list(PRESETS.get(sw.kind, PRESETS["static"]))


# ==========================================================================
# 3. Derived channels
# ==========================================================================
def add_derived(sw: Sweep, geometry: dict | None = None) -> None:
    """Append the derived columns a single corner can produce."""
    C.add_corner_derived(sw, ("",))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        _add_corner_extras(sw)
    sw.data = sw.data.copy()


def _add_corner_extras(sw: Sweep) -> None:
    """Finite-difference the wrt_hub_z gradients a damper-driven sweep lacks."""
    # Roll-centre migration, Ackermann and the axle steering ratio are all
    # two-wheel constructions and have no corner equivalent, so nothing is
    # derived for them here. Motion ratio is handled by the shared corner
    # derivation. What is left is wheel-centre recession, which the solver
    # exports analytically only when the sweep is driven by the wheel.
    d = sw.data
    if sw.kind != "damper_stroke":
        return
    target = "deriv_wheel_center_x_wrt_hub_z"
    if "wheel_travel" not in d.columns or "wheel_center_x" not in d.columns:
        return
    if target in d.columns and not d[target].isna().all():
        return
    z = d["wheel_travel"].to_numpy(float)
    if np.ptp(z) <= 1e-6:
        return
    d[target] = np.gradient(d["wheel_center_x"].to_numpy(float), z)
    sw.units[target] = "mm/mm"


# ==========================================================================
# 4. Report notes
# ==========================================================================
def notes(sweeps: list[Sweep], geometry: dict | None) -> list[str]:
    """The conventions section of report.md, for a single corner."""
    out = [
        "Conventions and formulas are documented in `CHARACTERISTICS.md`. "
        "What is specific to a single-corner model:\n",
        "- **This is one corner, not an axle.** Track, body roll, roll-centre "
        "height and lateral migration, Ackermann and rack displacement are all "
        "two-wheel constructions and are absent by definition, not by "
        "omission. On a three-wheel car the rear has no roll centre at all, so "
        "there is no roll axis and the front roll-centre height carries "
        "essentially the whole geometric lateral load transfer.",
        "- **The wheel is on the vehicle centreline, so it has no inboard or "
        "outboard.** Camber, toe, caster, KPI, scrub radius, mechanical trail, "
        "half track and the front-view swing arm all measure against a lateral "
        "datum that a centreline wheel does not have, so the solver emits none "
        "of them: those columns are absent from the CSV rather than blank or "
        "signed by an arbitrary convention. Naming them in run.yaml will not "
        "bring them back.",
        "- **The arm pivot is transverse, so the carrier does not tilt.** Both "
        "arm mounts share an X, the wheel swings in a plane, and the spin axis "
        "keeps its design orientation through the whole travel. Camber and toe "
        "change are what arm-axis obliquity in plan buys you, and this "
        "geometry deliberately has none.",
    ]
    if C._degenerate_side_view(sweeps):
        out.append(
            "- **No side-view instant centre on this geometry**, so SVSA, "
            "anti-squat, anti-lift and anti-dive are undefined. On a trailing "
            "arm that should not happen - the SVIC is the pivot axis - so "
            "check the arm pivot hardpoints if you see this.")
    else:
        out.append(
            "- **The side-view family is the reason this model earns its own "
            "report.** A trailing arm's SVIC is its pivot axis, so SVSA, its "
            "angle and the anti percentages are all well defined here, unlike "
            "on the front. Anti-squat additionally needs the driven axle "
            "declared, and anti-lift needs `front_brake_bias`.")
    out.append(
        "- **Anti-squat depends on where the drive torque is reacted**, which "
        "the geometry declares as `drive_torque_reaction`. A hub motor "
        "(`unsprung`) reacts it through the arm, so the force line runs from "
        "the contact patch; an inboard motor through halfshafts (`sprung`) "
        "leaves only the longitudinal force at the wheel centre. The two "
        "differ by a tyre radius of leverage and can be hundreds of percent "
        "apart on the same geometry. The column is blank if the setting is "
        "absent, rather than guessing one.")
    out.append(
        "- **The SVIC and SVSA length are tabulated but not plotted.** On a "
        "trailing arm the instant centre is the fixed pivot axis, so both plot "
        "as flat lines. SVSA angle carries the same information in a bounded "
        "form and is plotted instead.")
    return out


REPORTER = C.Reporter(
    title=TITLE,
    scope="corner",
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
