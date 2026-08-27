#!/usr/bin/env python3
"""
susreport - turn a directory of Suspension Explorer sweep CSVs into a
SUSProg-style characteristic report.

Usage:
    python susreport.py outputs/                  # writes report/ alongside
    python susreport.py outputs/ --out report/
    python susreport.py outputs/ --side left      # default: left

What it does that the raw CSV does not:
  * parses the '#' metadata header (format_version, provenance hashes, units)
  * classifies each sweep by what its targets actually do
  * derives the quantities the solver does not export directly
      - road-relative camber          (chassis camber folded with body roll)
      - SIGNED scrub radius           (the exported one is an unsigned magnitude)
      - motion ratio and MR^2
      - Ackermann percentage and error
      - roll-centre migration rates
  * reports every gradient at design condition AND as a range over the sweep
  * writes summary.csv, report.md, and a plots/ directory
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
# 1. Loading
# ==========================================================================
@dataclass
class Sweep:
    """One parsed sweep CSV plus its metadata and classification."""

    path: Path
    name: str
    data: pd.DataFrame
    meta: dict[str, str]
    units: dict[str, str]
    kind: str = "unknown"
    x_col: str = ""
    x_label: str = ""
    notes: list[str] = field(default_factory=list)

    def unit(self, col: str) -> str:
        return self.units.get(col, "")

    def has(self, *cols: str) -> bool:
        return all(c in self.data.columns and not self.data[c].isna().all()
                   for c in cols)

    @property
    def design_index(self) -> int:
        """Row closest to the design condition.

        Design condition is where the SWEPT quantity passes through its
        authored zero. Picking a column that does not move (e.g. wheel travel
        during a pure steer sweep) would silently return row 0, so prefer the
        sweep's own independent variable and require that it actually varies.
        """
        d = self.data
        candidates = [self.x_col, "wheel_travel_left", "rack_displacement", "roll"]
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
            else:
                meta[key] = value

    data = pd.read_csv(path, comment="#")
    return Sweep(path=path, name=path.stem, data=data, meta=meta, units=units)


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
        sw.kind = "heave_at_steer"
        sw.x_col = "wheel_travel_left"
        sw.x_label = "left wheel travel [mm]"
    else:
        sw.kind = "static"
        sw.x_col = "step_index"
        sw.x_label = "step"

    # A steer sweep held off design height is still a steer sweep, but say so.
    if sw.kind == "steer" and zl in d.columns:
        held = float(d[zl].iloc[0])
        base = held - float(d[zl].iloc[0])  # placeholder, refined below
        if "wheel_travel_left" in d.columns:
            tv = float(d["wheel_travel_left"].iloc[0])
            if abs(tv) > 1e-3:
                sw.notes.append(f"Held at {tv:+.1f} mm wheel travel, not design height.")
    if sw.kind in ("heave", "single_wheel", "roll") and "rack_displacement" in d.columns:
        rd = float(d["rack_displacement"].mean())
        if abs(rd) > 1e-2:
            sw.kind = f"{sw.kind}_at_steer"
            sw.notes.append(f"Rack held at {rd:+.2f} mm - this is a STEERED sweep.")
    if sw.x_col not in d.columns:
        sw.x_col = "step_index"


# ==========================================================================
# 3. Derived channels the solver does not export
# ==========================================================================
def add_derived(sw: Sweep) -> None:
    """Append derived columns to the sweep's dataframe."""
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
        if sao in d.columns and trail in d.columns and f"scrub_radius_{side}" in d.columns:
            recon = np.hypot(d[sao], d[trail])
            err = float(np.nanmax(np.abs(recon - d[f"scrub_radius_{side}"])))
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
        if sw.kind.startswith(("heave","single_wheel")) and \
                "wheel_travel_left" in d.columns:
            z = d["wheel_travel_left"].to_numpy(float)
            if np.ptp(z) > 1e-6:
                d["rc_migration_rate"] = np.gradient(
                    d["roll_center_z"].to_numpy(float), z)
                sw.units["rc_migration_rate"] = "mm/mm"
        if sw.kind.startswith("roll") and "roll" in d.columns:
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
    if sw.kind.startswith("roll") and "roll" in d.columns:
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
    # = anti-Ackermann (inner steers less than the outer).
    if sw.kind == "steer" and {"steer_angle_left", "steer_angle_right"} <= set(d.columns):
        wb = _wheelbase_guess(sw)
        track = float(d["track"].iloc[0]) if "track" in d.columns else np.nan
        sl = d["steer_angle_left"].to_numpy(float)
        sr = d["steer_angle_right"].to_numpy(float)
        # Outer wheel is the one with the smaller magnitude in a real
        # Ackermann layout; identify by turn direction instead.
        inner = np.where(sl > 0, sl, sr)      # magnitude bookkeeping below
        outer = np.where(sl > 0, sr, sl)
        d["ackermann_error"] = np.abs(inner) - np.abs(outer)
        sw.units["ackermann_error"] = "deg"
        if np.isfinite(wb) and np.isfinite(track) and track > 0:
            with np.errstate(divide="ignore", invalid="ignore"):
                out_rad = np.radians(np.abs(outer))
                # Ideal inner angle for the same outer angle.
                ideal = np.arctan2(
                    wb, np.maximum(wb / np.tan(np.where(out_rad > 1e-6, out_rad, np.nan))
                                   - track, 1e-9))
                ideal_delta = np.degrees(ideal) - np.abs(outer)
                actual_delta = np.abs(inner) - np.abs(outer)
                pct = 100.0 * actual_delta / ideal_delta
            d["ackermann_percent"] = pct
            sw.units["ackermann_percent"] = "%"

    # --- Steering ratio -------------------------------------------------
    if "deriv_steer_angle_wrt_rack_displacement_left" in d.columns:
        d["steer_per_rack_left"] = d["deriv_steer_angle_wrt_rack_displacement_left"]
        sw.units["steer_per_rack_left"] = "deg/mm"


def _wheelbase_guess(sw: Sweep) -> float:
    """Wheelbase is not exported; recover it from the geometry file if next to us."""
    geo = sw.meta.get("geometry_path", "")
    for candidate in (Path(geo), sw.path.parent.parent / Path(geo).name,
                      sw.path.parent.parent / "front.yaml"):
        try:
            if candidate.is_file():
                for line in candidate.read_text().splitlines():
                    if "wheelbase" in line:
                        return float(line.split(":")[1].split("#")[0].strip())
        except (OSError, ValueError, IndexError):
            continue
    return float("nan")


# ==========================================================================
# 4. Characteristic extraction
# ==========================================================================
# (column, pretty label) -- reported at design condition and across range.
POINT_CHANNELS = [
    ("camber", "Camber"),
    ("caster", "Caster"),
    ("kpi", "Kingpin inclination"),
    ("toe_angle", "Toe (positive = toe-in)"),
    ("steer_angle", "ISO steer angle"),
    ("scrub_radius", "Scrub radius (ISO unsigned)"),
    ("scrub_radius_signed", "Scrub radius (signed lateral)"),
    ("steering_axis_offset_ground", "Steering-axis offset at ground"),
    ("mechanical_trail", "Mechanical trail"),
    ("half_track", "Half track"),
    ("wheel_travel", "Wheel travel"),
    ("damper_length", "Damper length"),
    ("motion_ratio", "Motion ratio (damper/wheel)"),
    ("motion_ratio_sq", "Motion ratio squared"),
    ("fvic_y", "Front-view IC, y"),
    ("fvic_z", "Front-view IC, z"),
    ("fvsa_length", "Front-view swing-arm length"),
    ("svic_x", "Side-view IC, x"),
    ("svic_z", "Side-view IC, z"),
    ("svsa_length", "Side-view swing-arm length"),
    ("svsa_angle", "Side-view swing-arm angle"),
    ("anti_dive", "Anti-dive"),
    ("anti_lift", "Anti-lift"),
    ("anti_squat", "Anti-squat"),
    ("camber_road", "Camber, road-relative"),
    ("camber_recovery", "Camber recovery"),
]

AXLE_CHANNELS = [
    ("track", "Track"),
    ("track_change", "Track change"),
    ("track_change_rate", "Track change rate"),
    ("roll_center_z", "Roll-centre height"),
    ("roll_center_y", "Roll-centre lateral position"),
    ("rc_migration_rate", "Roll-centre migration vs travel"),
    ("rc_migration_rate_roll", "Roll-centre migration vs roll"),
    ("rc_lateral_rate_roll", "Roll-centre lateral migration vs roll"),
    ("roll", "Body roll"),
    ("heave", "Heave"),
    ("ride_height_change", "Ride-height change"),
    ("rack_displacement", "Rack displacement"),
    ("ackermann_error", "Ackermann error (inner - outer)"),
    ("ackermann_percent", "Ackermann"),
    ("steer_per_rack_left", "Steering ratio"),
]

DERIV_CHANNELS = [
    ("deriv_camber_wrt_hub_z", "Camber gain"),
    ("deriv_toe_angle_wrt_hub_z", "Bump steer rate"),
    ("deriv_steer_angle_wrt_hub_z", "ISO steer gain in bump"),
    ("deriv_caster_wrt_hub_z", "Caster gain"),
    ("deriv_kpi_wrt_hub_z", "KPI gain"),
    ("deriv_half_track_wrt_hub_z", "Half-track change rate"),
    ("deriv_wheel_center_x_wrt_hub_z", "Wheel-centre recession rate"),
    ("deriv_damper_length_wrt_hub_z", "Damper rate vs wheel"),
    ("deriv_toe_angle_wrt_rack_displacement", "Toe per rack"),
    ("deriv_steer_angle_wrt_rack_displacement", "Steer per rack"),
    ("deriv_camber_wrt_rack_displacement", "Camber per rack"),
]


def summarise(sw: Sweep, side: str) -> pd.DataFrame:
    """Build a tidy summary table for one sweep."""
    d = sw.data
    i0 = sw.design_index
    rows = []

    def add(col: str, label: str, group: str) -> None:
        if col not in d.columns or d[col].isna().all():
            return
        s = d[col].astype(float)
        rows.append({
            "group": group,
            "characteristic": label,
            "column": col,
            "unit": sw.unit(col),
            "at_design": s.iloc[i0],
            "min": s.min(),
            "max": s.max(),
            "range": s.max() - s.min(),
            "at_start": s.iloc[0],
            "at_end": s.iloc[-1],
        })

    for col, label in POINT_CHANNELS:
        add(f"{col}_{side}", label, "corner")
    for col, label in AXLE_CHANNELS:
        add(col, label, "axle")
    for col, label in DERIV_CHANNELS:
        add(f"{col}_{side}", label, "gradient")

    out = pd.DataFrame(rows)
    if not out.empty:
        out.insert(0, "sweep", sw.name)
        out.insert(1, "kind", sw.kind)
    return out


# ==========================================================================
# 5. Plots
# ==========================================================================
def plot_sweep(sw: Sweep, side: str, outdir: Path) -> list[Path]:
    """Emit one figure per sweep with the channels that matter for its kind."""
    d = sw.data
    x = d[sw.x_col].astype(float) if sw.x_col in d.columns else d.index.to_series()

    panels: list[tuple[str, list[tuple[str, str, str]]]] = []

    if sw.kind.startswith(("heave","single_wheel")):
        panels = [
            ("Camber", [(f"camber_{side}", "camber", C_L)]),
            ("Bump steer (toe)", [(f"toe_angle_{side}", "toe", C_L)]),
            ("Motion ratio", [(f"motion_ratio_{side}", "MR", C_L)]),
            ("Caster / KPI", [(f"caster_{side}", "caster", C_L),
                              (f"kpi_{side}", "KPI", C_R)]),
            ("Half track", [(f"half_track_{side}", "half track", C_L)]),
            ("Roll-centre height", [("roll_center_z", "RC z", C_N)]),
            ("Scrub radius (signed)", [(f"scrub_radius_signed_{side}", "scrub", C_L)]),
            ("Damper length", [(f"damper_length_{side}", "damper", C_L)]),
            ("Anti-dive", [(f"anti_dive_{side}", "anti-dive", C_N)]),
        ]
    elif sw.kind.startswith("roll"):
        panels = [
            ("Camber (chassis)", [("camber_left", "left", C_L),
                                  ("camber_right", "right", C_R)]),
            ("Camber (road-relative)", [("camber_road_left", "left", C_L),
                                        ("camber_road_right", "right", C_R)]),
            ("Camber recovery", [(f"camber_recovery_{side}", "d cam / d roll", C_L)]),
            ("Roll-centre height", [("roll_center_z", "RC z", C_N)]),
            ("Roll-centre lateral", [("roll_center_y", "RC y", C_N)]),
            ("Roll steer (toe)", [("toe_angle_left", "left", C_L),
                                  ("toe_angle_right", "right", C_R)]),
            ("Track change", [("track_change", "track change", C_N)]),
            ("Heave (should be ~0)", [("heave", "heave", C_D)]),
        ]
    elif sw.kind.startswith("steer"):
        panels = [
            ("Steer angles", [("steer_angle_left", "left", C_L),
                              ("steer_angle_right", "right", C_R)]),
            ("Ackermann error", [("ackermann_error", "inner - outer", C_N)]),
            ("Ackermann %", [("ackermann_percent", "%", C_N)]),
            ("Camber vs steer", [("camber_left", "left", C_L),
                                 ("camber_right", "right", C_R)]),
            ("Caster vs steer", [("caster_left", "left", C_L),
                                 ("caster_right", "right", C_R)]),
            ("KPI vs steer", [("kpi_left", "left", C_L),
                              ("kpi_right", "right", C_R)]),
            ("Scrub (signed)", [("scrub_radius_signed_left", "left", C_L),
                                ("scrub_radius_signed_right", "right", C_R)]),
            ("Mechanical trail", [("mechanical_trail_left", "left", C_L),
                                  ("mechanical_trail_right", "right", C_R)]),
        ]
    elif sw.kind == "damper_stroke":
        panels = [
            ("Wheel travel vs damper", [(f"wheel_travel_{side}", "travel", C_L)]),
            ("Camber", [(f"camber_{side}", "camber", C_L)]),
            ("Motion ratio", [(f"motion_ratio_{side}", "MR", C_L)]),
            ("Roll-centre height", [("roll_center_z", "RC z", C_N)]),
        ]

    panels = [(t, [s for s in series if s[0] in d.columns
                   and not d[s[0]].isna().all()])
              for t, series in panels]
    panels = [(t, s) for t, s in panels if s]
    if not panels:
        return []

    ncol = 3
    nrow = math.ceil(len(panels) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.7 * ncol, 3.3 * nrow),
                             squeeze=False)
    fig.suptitle(f"{sw.name}  [{sw.kind}]", fontsize=13, color=INK)

    for ax, (title, series) in zip(axes.flat, panels):
        for col, label, colour in series:
            ax.plot(x, d[col].astype(float), color=colour, lw=1.8, label=label)
        ax.set_title(title, fontsize=10, color=INK)
        ax.set_xlabel(sw.x_label, fontsize=8)
        unit = sw.unit(series[0][0])
        ax.set_ylabel(unit, fontsize=8)
        ax.grid(True, alpha=0.25)
        # Only draw the zero line when zero is actually near the data, so a
        # channel like damper length is not squashed against the top of the
        # panel just to keep an irrelevant y=0 in frame.
        vals = np.concatenate([d[c].astype(float).dropna().to_numpy()
                               for c, _, _ in series]) if series else np.array([])
        if vals.size and vals.min() - 0.15 * np.ptp(vals) <= 0 <= vals.max() + 0.15 * np.ptp(vals):
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
# 6. Report
# ==========================================================================
def write_report(sweeps: list[Sweep], summary: pd.DataFrame,
                 side: str, out: Path, plots: list[Path]) -> Path:
    lines: list[str] = []
    lines.append("# Suspension characteristic report\n")

    first = sweeps[0]
    lines.append("## Provenance\n")
    lines.append(f"- geometry: `{first.meta.get('geometry_path','?')}`")
    lines.append(f"- geometry SHA-256: `{first.meta.get('geometry_hash','?')[:16]}...`")
    lines.append(f"- format version: {first.meta.get('format_version','?')}")
    lines.append(f"- reported side: **{side}**\n")

    hashes = {s.meta.get("geometry_hash", "") for s in sweeps}
    if len(hashes) > 1:
        lines.append("> **WARNING:** these sweeps were not all run against the "
                     "same geometry file. The summary below mixes models.\n")

    lines.append("## Sweeps\n")
    lines.append("| file | kind | steps | converged | max residual | notes |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for s in sweeps:
        d = s.data
        conv = bool(d["solver_converged"].all()) if "solver_converged" in d else True
        res = d["solver_max_residual"].max() if "solver_max_residual" in d else float("nan")
        lines.append(f"| `{s.name}` | {s.kind} | {len(d)} | {conv} | "
                     f"{res:.2e} | {' '.join(s.notes) or '-'} |")
    lines.append("")

    for s in sweeps:
        sub = summary[summary["sweep"] == s.name]
        if sub.empty:
            continue
        lines.append(f"## {s.name}  ({s.kind})\n")
        for group, heading in (("corner", "Corner characteristics"),
                               ("axle", "Axle characteristics"),
                               ("gradient", "Gradients (analytic unless noted)")):
            g = sub[sub["group"] == group]
            if g.empty:
                continue
            lines.append(f"### {heading}\n")
            lines.append("| characteristic | unit | at design | min | max | range |")
            lines.append("| --- | --- | --- | --- | --- | --- |")
            for _, r in g.iterrows():
                lines.append(
                    f"| {r['characteristic']} | {r['unit']} | {r['at_design']:.4f} | "
                    f"{r['min']:.4f} | {r['max']:.4f} | {r['range']:.4f} |")
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
# 7. Entry point
# ==========================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("indir", type=Path, help="directory of sweep CSVs")
    ap.add_argument("--out", type=Path, default=None, help="output directory")
    ap.add_argument("--side", default="left", choices=("left", "right"))
    args = ap.parse_args()

    out = args.out or args.indir.parent / "report"
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(args.indir.glob("*.csv"))
    if not files:
        raise SystemExit(f"no CSVs in {args.indir}")

    sweeps, frames, plots = [], [], []
    for f in files:
        sw = read_sweep(f)
        classify(sw)
        add_derived(sw)
        sweeps.append(sw)
        frames.append(summarise(sw, args.side))
        plots += plot_sweep(sw, args.side, out / "plots")
        print(f"  {f.name:30s} -> {sw.kind}")

    summary = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    summary.to_csv(out / "summary.csv", index=False)
    report = write_report(sweeps, summary, args.side, out, plots)

    print(f"\n  {len(summary)} characteristics extracted")
    print(f"  summary : {out/'summary.csv'}")
    print(f"  report  : {report}")
    print(f"  plots   : {out/'plots'} ({len(plots)} figures)")


if __name__ == "__main__":
    main()
