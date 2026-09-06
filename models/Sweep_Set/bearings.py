#!/usr/bin/env python3
"""
Bearing misalignment - shared by every report.

The sweeps export the relative rotation Q(t) of the two bodies meeting at each
declared joint, and Q(t) is independent of the bearing axes. So every question
about axes - what a declared one costs, what the best available one costs, how
a rod end should be clocked - is answered here from the CSVs alone, with no
re-solving.

This lives in its own module because it is the one part of a report that is
identical for every suspension: a spherical bearing on a trailing arm has the
same maths as one on a wishbone, and these are the numbers you take to a
catalogue. Two copies of this file would be two chances to fix a bug in only
one of them, and nothing in either report would tell you.

Corner models export joint columns without a side suffix; axle models suffix
them. `_joint_column` tolerates both, so a caller passes `side=""` for a corner.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


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



def joints_table(joints: list["JointResult"]) -> pd.DataFrame:
    """Flatten the joint results for joints.csv."""
    return pd.DataFrame(
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
    )


def report_section(joints: list["JointResult"]) -> list[str]:
    """Render the bearing misalignment section of report.md."""
    if not joints:
        return []
    lines = ["## Bearing misalignment\n"]
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
        locked = "-" if j.locked_required is None else f"{j.locked_required:.2f}"
        locked_clock = ("-" if j.locked_clocking_deg is None
                        else f"{j.locked_clocking_deg:.1f}")
        offset = "-" if j.install_offset is None else f"{j.install_offset:.2f}"
        best = "-" if j.optimal_required is None else f"{j.optimal_required:.2f}"
        clock = "-" if j.optimal_clocking is None else f"{j.optimal_clocking:.1f}"
        lines.append(f"| {j.label} | {j.type} | {required} | {where} | "
                     f"{locked} | {locked_clock} | {offset} | {best} | {clock} |")
    lines.append("")
    return lines
