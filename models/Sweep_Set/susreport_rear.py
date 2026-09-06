#!/usr/bin/env python3
"""
susreport_rear - characteristic report for a SINGLE CORNER (Aurora rear).

    uv run python models/Sweep_Set/susreport_rear.py <outputs dir> --out <dir>

Aurora's rear is one trailing-arm corner on the centreline, not an axle, and
that changes what there is to report:

  * its CSV columns carry no side suffix - `camber`, not `camber_left`
  * there is no track, no body roll, no roll centre, no rack and no Ackermann,
    because every one of those is built from two wheels
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
    # --- alignment ------------------------------------------------------
    single("camber", "Camber", "camber{side}"),
    single("caster", "Caster", "caster{side}"),
    single("kpi", "Kingpin inclination", "kpi{side}"),
    single("toe", "Toe (positive = toe-in)", "toe_angle{side}"),
    single("steer_angle", "ISO steer angle", "steer_angle{side}"),
    single("scrub_signed", "Scrub radius (signed lateral)",
           "scrub_radius_signed{side}"),
    single("scrub_iso", "Scrub radius (ISO unsigned)", "scrub_radius{side}"),
    single("trail", "Mechanical trail", "mechanical_trail{side}"),
    single("half_track", "Half track", "half_track{side}"),

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

    # --- front view ------------------------------------------------------
    single("fvic_y", "FVIC lateral (y)", "fvic_y{side}"),
    single("fvic_z", "FVIC height (z)", "fvic_z{side}"),
    single("fvsa", "FVSA length", "fvsa_length{side}"),

    # --- gradients -------------------------------------------------------
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
]}


# Channel lists used when a sweep asks for `report: true` without naming any.
PRESETS: dict[str, list[str]] = {
    # Wheel travel commanded, damper read. The design reference for the arm.
    "heave": [
        "camber", "caster", "kpi", "toe", "scrub_signed", "trail",
        "half_track", "wheel_travel", "damper_length", "motion_ratio",
        "camber_gain", "bump_steer", "recession_rate",
        "svic_x", "svic_z", "svsa", "svsa_angle", "anti_squat", "anti_lift",
    ],
    # Damper length commanded, wheel read. Where the usable travel comes from.
    "damper_stroke": [
        "damper_length", "wheel_travel", "motion_ratio",
    ],
    "static": ["camber", "caster", "toe", "half_track"],
}

# Tabulated but never plotted: the instant centres run to +/-10^5 mm through
# the parallel-link singularity and flatten every other panel. Camber gain is
# FVSA's bounded equivalent; SVSA angle is SVSA's. Wheel travel is the x-axis.
NEVER_PLOT = {"fvic_y", "fvic_z", "fvsa", "svic_x", "svic_z", "svsa",
              "wheel_travel"}


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

    def varies(col: str) -> bool:
        return spans.get(col, 0.0) > threshold

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
    elif varies("target_rack"):
        sw.kind = "steer"
        sw.x_col = "target_rack"
        sw.x_label = "rack position [mm]"
    else:
        sw.kind = "static"
        sw.x_col = "step_index"
        sw.x_label = "step"

    if sw.kind != "steer" and varies("target_rack"):
        sw.notes.append("The rack moves in this sweep as well as the wheel.")
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
    d = sw.data
    # Roll-centre migration, camber recovery, Ackermann and the axle steering
    # ratio are all two-wheel constructions and have no corner equivalent, so
    # nothing is derived for them here. What a corner can add on its own is the
    # numerical wheel-travel gradient when the sweep was driven by the damper
    # and the analytic wrt_hub_z derivatives are therefore absent.
    if sw.kind == "damper_stroke" and {"wheel_travel", "camber"} <= set(d.columns):
        z = d["wheel_travel"].to_numpy(float)
        if np.ptp(z) > 1e-6:
            for stem, unit in (("camber", "deg/mm"), ("toe_angle", "deg/mm"),
                               ("caster", "deg/mm"), ("kpi", "deg/mm"),
                               ("half_track", "mm/mm")):
                target = f"deriv_{stem}_wrt_hub_z"
                if stem in d.columns and (
                        target not in d.columns or d[target].isna().all()):
                    d[target] = np.gradient(d[stem].to_numpy(float), z)
                    sw.units[target] = unit


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
        "- **Half track is measured from the vehicle centreline.** A rear "
        "wheel sitting on the centreline reports approximately zero, and the "
        "signs of scrub radius and FVSA follow the declared `side` rather than "
        "anything physical. Read their magnitudes, not their signs.",
        "- **Scrub radius** is reported as the signed lateral offset "
        "(`steering_axis_offset_ground`). The ISO `scrub_radius` column is an "
        "unsigned distance that includes mechanical trail.",
        "- **The steering axis of an unsteered corner is a construction, not "
        "a hinge.** Camber, caster, KPI, scrub and trail are all measured "
        "about the line the model calls the steering axis; on a trailing arm "
        "that is the line from the arm's outboard point to the axle inboard "
        "point. They still describe how the wheel is oriented, but nothing "
        "rotates about that line.",
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
        "- **FVIC and FVSA are tabulated but not plotted.** They pass through "
        "a singularity when the links go parallel and swing to 10^5 mm. "
        "Camber gain is FVSA's bounded equivalent "
        "(`camber_gain ~ -57.296 / FVSA` in deg/mm); SVSA angle is SVSA's.")
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
