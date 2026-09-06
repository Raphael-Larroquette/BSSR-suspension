#!/usr/bin/env python3
"""
Shared machinery for every characteristic report.

This module holds the parts that do not depend on what kind of suspension the
CSVs describe: reading a sweep file and its metadata header, checking solver
health, reducing a channel to design/min/max/range, drawing a figure, and
writing report.md.

What a suspension actually *is* lives in the reporter that imports this:

    susreport.py        two-wheel axle  (Aurora front)   columns are side-suffixed
    susreport_rear.py   single corner   (Aurora rear)    columns carry no suffix

Each reporter owns its channel catalogue, its sweep classification, its derived
channels and its report notes, because those are the parts that genuinely
differ. Everything here is the plumbing they share, so a fix to the CSV parser
or the solver-health check reaches both.

There are no default values anywhere. run.yaml is the single source of truth;
a missing setting is an error naming the key.
"""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

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
C_L = "#2f6fdb"   # left / primary
C_R = "#d1495b"   # right
C_N = "#5c6670"   # neutral / axle-level
C_D = "#8a94a6"   # reference lines


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
# Channel plumbing
#
# A "channel" is the config-facing name. It resolves to one CSV column, or to a
# left/right pair on an axle model. The catalogue itself lives in the reporter:
# an axle's columns are side-suffixed (`camber_left`) and a corner's are not
# (`camber`), which is the whole of the difference and is carried by the
# `side` string the reporter passes in ("_left", "_right", or "").
# ==========================================================================
@dataclass(frozen=True)
class Channel:
    """One config-facing characteristic and the CSV column(s) behind it."""

    key: str
    label: str
    kind: str            # "single" | "pair" | "axle"
    column: str          # template; "{side}" is substituted for sided channels
    note: str = ""

    def columns(self, side: str) -> list[tuple[str, str, str]]:
        """Return [(column, series label, colour)] for this channel.

        `side` is the suffix, not the word: "_left" on an axle, "" on a corner.
        """
        if self.kind == "pair":
            return [
                (self.column.format(side="_left"), "left", C_L),
                (self.column.format(side="_right"), "right", C_R),
            ]
        if self.kind == "single":
            return [(self.column.format(side=side), self.label, C_L)]
        return [(self.column, self.label, C_N)]


def single(key, label, column, note=""):
    """A per-corner channel: side-suffixed on an axle, bare on a corner."""
    return Channel(key, label, "single", column, note)


def pair(key, label, column, note=""):
    """A left-and-right channel. Axle models only."""
    return Channel(key, label, "pair", column, note)


def axle(key, label, column, note=""):
    """An axle-level channel with no per-corner variant."""
    return Channel(key, label, "axle", column, note)


def side_suffix(side: str | None) -> str:
    """Turn a configured side into the CSV column suffix."""
    return f"_{side}" if side else ""



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
            candidates = ["wheel_travel_left", "wheel_travel_right",
                          "wheel_travel", self.x_col]
        else:
            candidates = [self.x_col, "wheel_travel_left", "wheel_travel",
                          "rack_displacement", "target_rack", "roll"]
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
# 6. Characteristic extraction
# ==========================================================================
def summarise(sw: Sweep, side: str, keys: list[str],
              channels: dict[str, Channel]) -> pd.DataFrame:
    """Build a tidy summary table for one sweep, in the configured order.

    `side` is the column suffix ("_left", "_right", or "" for a corner model).
    """
    d = sw.data
    good = sw.good
    i0 = sw.design_index
    rows = []

    for key in keys:
        channel = channels.get(key)
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
def plot_sweep(sw: Sweep, side: str, keys: list[str],
               channels: dict[str, Channel], outdir: Path) -> list[Path]:
    """Emit one figure per sweep, one panel per requested channel."""
    d = sw.data
    if not keys:
        return []
    x = d[sw.x_col].astype(float) if sw.x_col in d.columns else d.index.to_series()

    panels: list[tuple[str, list[tuple[str, str, str]], str]] = []
    for key in keys:
        channel = channels.get(key)
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
                 out: Path, plots: list[Path], joints: list | None,
                 config: dict, problems: dict[str, list[str]],
                 title: str, notes: list[str]) -> Path:
    """Assemble report.md. `notes` is the reporter's conventions section."""
    from bearings import report_section as bearing_section

    joints = joints or []
    decimals = config["decimals"]
    report_cfg = config["report"]
    lines: list[str] = []
    lines.append(f"# {title}\n")

    first = sweeps[0]
    lines.append("## Provenance\n")
    lines.append(f"- geometry: `{first.meta.get('geometry_path','?')}`")
    lines.append(f"- geometry SHA-256: `{first.meta.get('geometry_hash','?')[:16]}...`")
    lines.append(f"- format version: {first.meta.get('format_version','?')}")
    if side:
        lines.append(f"- reported side: **{side.lstrip('_')}**")
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

    if report_cfg["notes"] and notes:
        lines.append("## Notes\n")
        lines += notes
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
        lines += bearing_section(joints)

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


def channels_for(sw: Sweep, config: dict, channels: dict[str, Channel],
                 presets: dict[str, list[str]], never_plot: set[str],
                 preset_for: "Callable[[Sweep], list[str]]",
                 ) -> tuple[list[str], list[str]]:
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
        keys = preset_for(sw)
    else:
        keys = [str(k) for k in wanted]
    unknown = [k for k in keys if k not in channels]
    if unknown:
        # A front channel list pasted into a rear run.yaml would otherwise
        # produce a suspiciously short table with no explanation.
        print(f"      ! {sw.name}: not available on this model, skipped: "
              + ", ".join(unknown))
    keys = [k for k in keys if k in channels]

    master = str(report_cfg["plots"]).lower()
    if master in ("false", "none", "off"):
        return keys, []

    wanted_plots = sweep_cfg["plots"]
    if master in ("true", "all", "on"):
        wanted_plots = "all"
    if wanted_plots is False or wanted_plots == "none":
        return keys, []
    if wanted_plots is True or wanted_plots == "all":
        plot_keys = [k for k in keys if k not in never_plot]
    else:
        plot_keys = [str(k) for k in wanted_plots if str(k) in channels]
    return keys, plot_keys



# ==========================================================================
# Derived channels shared by every model
#
# These depend only on one corner's columns, so they are identical whether the
# corner belongs to an axle or stands alone. `sides` is the list of column
# suffixes to walk: ("_left", "_right") on an axle, ("",) on a corner.
# ==========================================================================
def add_corner_derived(sw: Sweep, sides: tuple[str, ...]) -> None:
    """Append the per-corner derived columns. See CHARACTERISTICS.md."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        _add_corner_derived(sw, sides)
    sw.data = sw.data.copy()


def _add_corner_derived(sw: Sweep, sides: tuple[str, ...]) -> None:
    d = sw.data
    for side in sides:
        cam = f"camber{side}"
        sao = f"steering_axis_offset_ground{side}"
        trail = f"mechanical_trail{side}"
        dmp = f"damper_length{side}"

        # --- Road-relative camber -------------------------------------
        # The solver exports camber relative to the CHASSIS. What the tyre
        # actually sees is folded with body roll. Only an axle model has a
        # roll column, so this is silently absent on a corner.
        if cam in d.columns and "roll" in d.columns:
            d[f"camber_road{side}"] = d[cam] - d["roll"]
            sw.units[f"camber_road{side}"] = "deg"

        # --- Signed scrub radius --------------------------------------
        # `scrub_radius` in the CSV is the ISO 8855 unsigned road-plane
        # DISTANCE, i.e. hypot(lateral offset, mechanical trail), so it is
        # inflated by caster trail and can never go negative. The number most
        # tools (and Milliken) call "scrub radius" is the signed LATERAL
        # component, positive when the steering axis meets the ground inboard
        # of the contact centre. `steering_axis_offset_ground` already uses
        # exactly that sign convention, so this is an alias, not a negation.
        if sao in d.columns:
            d[f"scrub_radius_signed{side}"] = d[sao]
            sw.units[f"scrub_radius_signed{side}"] = "mm"

        iso = f"scrub_radius{side}"
        if sao in d.columns and trail in d.columns and iso in d.columns:
            recon = np.hypot(d[sao], d[trail])
            err = float(np.nanmax(np.abs(recon - d[iso])))
            if err > 1e-3:
                sw.notes.append(
                    f"scrub_radius{side} does not reconstruct from "
                    f"hypot(offset, trail) (max err {err:.3g} mm)."
                )

        # --- Motion ratio ---------------------------------------------
        # MR = -d(damper length)/d(wheel centre z). Prefer the analytic
        # derivative; fall back to a numerical gradient.
        an = f"deriv_damper_length_wrt_hub_z{side}"
        if an in d.columns and not d[an].isna().all():
            d[f"motion_ratio{side}"] = -d[an]
            sw.units[f"motion_ratio{side}"] = "mm/mm"
        elif dmp in d.columns and f"wheel_travel{side}" in d.columns:
            z = d[f"wheel_travel{side}"].to_numpy(float)
            if np.ptp(z) > 1e-6:
                d[f"motion_ratio{side}"] = -np.gradient(
                    d[dmp].to_numpy(float), z)
                sw.units[f"motion_ratio{side}"] = "mm/mm"
        if f"motion_ratio{side}" in d.columns:
            # Spring/damper force and rate scale with MR^2 at the wheel.
            d[f"motion_ratio_sq{side}"] = d[f"motion_ratio{side}"] ** 2
            sw.units[f"motion_ratio_sq{side}"] = "-"


def _geometry_path(sw: Sweep) -> Path | None:
    """Best guess at the geometry file this sweep was run against."""
    declared = sw.meta.get("geometry_path", "")
    candidates = [Path(declared)]
    if declared:
        # The header may carry a Windows path from another machine.
        name = declared.replace("\\", "/").rsplit("/", 1)[-1]
        for parent in (sw.path.parent, sw.path.parent.parent,
                       sw.path.parent.parent.parent):
            candidates.append(parent / name)
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def load_geometry_dict(sw: Sweep) -> dict | None:
    """Load the geometry YAML this sweep names, when it can be found."""
    path = _geometry_path(sw)
    if path is None:
        return None
    try:
        import yaml
        return yaml.safe_load(path.read_text())
    except Exception:
        return None


def geometry_setting(geometry: dict | None, *names: str):
    """Look a key up in either an axle or a corner geometry's config block.

    An axle geometry keeps vehicle-level settings under `vehicle_config:`;
    a standalone corner keeps them under a flat `config:`. Callers should not
    have to know which they were handed.
    """
    if not isinstance(geometry, dict):
        return None
    containers = [geometry,
                  geometry.get("vehicle_config") or {},
                  geometry.get("config") or {}]
    for container in list(containers):
        if isinstance(container, dict):
            containers.append(container.get("steering") or {})
    for container in containers:
        if not isinstance(container, dict):
            continue
        for name in names:
            if container.get(name) is not None:
                return container[name]
    return None


def wheelbase_of(geometry: dict | None) -> float:
    """Wheelbase in mm, or NaN. Not exported by the solver."""
    value = geometry_setting(geometry, "wheelbase")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def rack_travel_per_turn(geometry: dict | None) -> float | None:
    """Rack millimetres per steering-wheel revolution, if the geometry says.

    Accepts either an explicit `rack_travel_per_turn` or a `pinion_radius`,
    from which the travel per revolution is 2*pi*r.
    """
    value = geometry_setting(geometry, "rack_travel_per_turn")
    if value:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    radius = geometry_setting(geometry, "pinion_radius")
    if radius:
        try:
            return 2.0 * math.pi * float(radius)
        except (TypeError, ValueError):
            pass
    return None


# ==========================================================================
# The orchestrator
# ==========================================================================
@dataclass(frozen=True)
class Reporter:
    """Everything that makes one kind of suspension's report what it is."""

    title: str
    scope: str                                   # "axle" | "corner"
    channels: dict[str, Channel]
    presets: dict[str, list[str]]
    never_plot: set[str]
    classify: Callable[[Sweep], None]
    add_derived: Callable[[Sweep, dict | None], None]
    preset_for: Callable[[Sweep], list[str]]
    notes: Callable[[list[Sweep], dict | None], list[str]]


def run_report(indir: Path, out: Path, config: dict, reporter: Reporter,
               side: str | None = None) -> Path:
    """Build the report from a directory of sweep CSVs. Returns report.md.

    `run_all.py` imports this rather than launching a second Python, so
    tracebacks and breakpoints land in the calling process.
    """
    import bearings

    configured_side = side if side is not None else config["side"]
    suffix = side_suffix(configured_side) if reporter.scope == "axle" else ""
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
    geometry: dict | None = None
    fail_mode = str(config["solver"]["on_bad_solve"]).lower() == "fail"

    for path in files:
        sw = read_sweep(path)
        reporter.classify(sw)
        problems[sw.name] = check_solver(sw, config["solver"])
        if geometry is None:
            geometry = load_geometry_dict(sw)
        reporter.add_derived(sw, geometry)
        sweeps.append(sw)

        report_keys, plot_keys = channels_for(
            sw, config, reporter.channels, reporter.presets,
            reporter.never_plot, reporter.preset_for)
        if report_keys:
            frames.append(summarise(sw, suffix, report_keys, reporter.channels))
        if plot_keys:
            plots += plot_sweep(sw, suffix, plot_keys, reporter.channels,
                                out / "plots")
        shown = "reported" if report_keys else "solved only"
        print(f"  {path.name:30s} -> {sw.kind:22s} ({shown})")
        for message in problems[sw.name]:
            print(f"      ! {message}")

    if fail_mode and any(problems.values()):
        raise SystemExit(
            "solver.on_bad_solve is 'fail' and at least one sweep has bad steps."
        )

    non_empty = [f for f in frames if not f.empty]
    summary = (pd.concat(non_empty, ignore_index=True) if non_empty
               else pd.DataFrame())
    summary.to_csv(out / "summary.csv", index=False)

    joints: list = []
    if config["report"]["joints"]:
        try:
            joints = bearings.analyse_joints(sweeps, configured_side or "")
        except ImportError as error:
            print(f"  ! bearing misalignment skipped: {error}")
    if joints:
        bearings.joints_table(joints).to_csv(out / "joints.csv", index=False)

    report = write_report(sweeps, summary, suffix, out, plots, joints, config,
                          problems, reporter.title,
                          reporter.notes(sweeps, geometry))

    print(f"\n  {len(summary)} characteristics extracted")
    print(f"  summary : {out/'summary.csv'}")
    print(f"  report  : {report}")
    print(f"  plots   : {out/'plots'} ({len(plots)} figures)")
    if joints:
        print(f"  joints  : {out/'joints.csv'} ({len(joints)} declared)")
    return report


def main(reporter: Reporter, argv: list[str] | None = None) -> None:
    """Shared command-line entry point for a reporter module."""
    import argparse

    ap = argparse.ArgumentParser(
        description=f"{reporter.title} - build report.md from sweep CSVs.")
    ap.add_argument("indir", type=Path, help="directory of sweep CSVs")
    ap.add_argument("--out", type=Path, default=None, help="output directory")
    ap.add_argument("--side", default=None, choices=("left", "right"),
                    help="reported corner (axle models only)")
    ap.add_argument("--config", type=Path, default=None,
                    help="run.yaml to read channel selection and formatting from")
    ap.add_argument("--resolved", type=Path, default=None,
                    help="resolved JSON configuration written by run_all.py")
    ap.add_argument("--no-joints", action="store_true",
                    help="skip the bearing misalignment section")
    args = ap.parse_args(argv)

    config = load_config(args.config, args.resolved)
    if args.no_joints:
        config["report"]["joints"] = False
    out = args.out or args.indir.parent / "report"
    run_report(args.indir, out, config, reporter, side=args.side)
