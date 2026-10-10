#!/usr/bin/env python3
"""
The entry point for everything under Working/: the kinematic sweep sets, the
static force solve, the reports and the animations, for one model or a whole
folder of them. Cross-platform, and independent of your current directory.

    uv run python Working/run_all.py                          Aurora, everything
    uv run python Working/run_all.py --model aurora_evo       another model
    uv run python Working/run_all.py --sets front --no-forces one sweep set only
    uv run python Working/run_all.py --batch opt_2026-10-02_1430 --sets front
                                                              every model in a folder

A MODEL is a folder under Working/models/ holding front.yaml and/or rear.yaml,
and optionally forces.yaml. Load cases are shared: Working/cases.csv. Everything
a run writes lands inside the model folder:

    models/<model>/sweep_outputs/<set>/   one CSV per sweep, and the animations
    models/<model>/report/<set>/          report.md, solve_status.csv, plots
    models/<model>/forces/                forces.csv, load_transfer.csv
    models/<model>/logs/                  one log per task (tracebacks live here)
    models/<model>/run.log                one line per task, newest run only

and a batch also writes <batch>/batch_summary.md and .csv.

HOW A RUN GOES

    1. plan     every (model, sweep set) is validated and its sweep files are
                generated. Nothing is solved yet.
    2. solve    every sweep of every model, and every force solve, on one pool
                of worker processes sized to this machine.
    3. report   each set's report (built from the sweeps that solved) and an
       animate  animation for every sweep that solved and asked for one, on a
                second pool.
    4. summary  a table of what solved, what failed, and where.

A sweep that fails never stops the others: its report says it is missing, and
the summary says at which step and pose it stopped. See sweep_sets/scheduler.py
for how the pool is sized from the cores and memory available.

THIS IS THE ONLY COMMAND; sweep_sets/runner.py, scheduler.py and tasks.py are
libraries this file uses. A sweep set is chosen with --sets (folder name) or
--config (path); every other flag narrows what runs inside the sets chosen.

Forces run by default, because a sweep set and the force solve read the SAME
geometry: a hardpoint edit invalidates both. A model without a forces.yaml is
skipped for forces, with a note.

See the repository README.md for the workflow, sweep_sets/RUNNING.md for the
run.yaml keys, and FORCES.md for the force solve.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent  # Working/
SWEEP_SETS_DIR = HERE / "sweep_sets"
MODELS_DIR = HERE / "models"

# The libraries live beside the sweep sets. Pool workers inherit this path.
if str(SWEEP_SETS_DIR) not in sys.path:
    sys.path.insert(0, str(SWEEP_SETS_DIR))

import scheduler  # noqa: E402 - stdlib only; must precede anything importing numpy

# One BLAS thread per process, in this process and every worker it starts. Must
# happen before numpy is first imported. See scheduler.py.
scheduler.pin_threads()

# A sweep set is a folder with a run.yaml.
SWEEP_SET_GLOB = "*/run.yaml"

# A model's force configuration, beside its geometry.
FORCES_CONFIG_NAME = "forces.yaml"

# Geometry files that make a folder a model.
GEOMETRY_NAMES = ("front.yaml", "rear.yaml")

# The load cases every model's force solve uses (a forces.yaml with its own
# `cases:` key overrides this for that model).
CASES_FILE = HERE / "cases.csv"

# What each run writes inside a model folder, and beside a batch.
RUN_LOG_NAME = "run.log"
LOGS_DIRNAME = "logs"
BATCH_SUMMARY_NAME = "batch_summary"

# Overrides that describe ONE set and cannot mean anything across several.
PER_SET_FLAGS = ("geometry", "side")

# Flags that no longer exist, and what replaced them.
REMOVED_FLAGS = {
    "--parallel": "--workers (one pool now serves every model)",
    "--gif-workers": "--workers (each animation is one task on the shared pool)",
    "--jobs": "--workers (one pool now serves every model and sweep)",
}

# Starting memory budget per worker, MB. Replaced by measured peaks as tasks
# finish; generous so the first wave never over-commits.
SOLVE_WORKER_MB = 600.0
RENDER_WORKER_MB = 900.0

# Recycle render workers after this many tasks, so a slow matplotlib leak
# cannot grow across a 400-animation batch.
RENDER_TASKS_PER_WORKER = 25

# One letter per status, for the console and summary matrices (ASCII, so a
# Windows console prints it).
STATUS_LETTER = {
    "ok": ".", "warn": "w", "lockout": "L", "geometry": "G", "resource": "M",
    "error": "E", "skipped": "s", "missing": "?",
}
GOOD = ("ok", "warn", "skipped")


# ==========================================================================
# Discovery
# ==========================================================================
def discover_sweep_sets() -> list[Path]:
    """Return every sweep set's run.yaml, in folder-name order."""
    return sorted(SWEEP_SETS_DIR.glob(SWEEP_SET_GLOB))


def label(config: Path) -> str:
    """Name a sweep set by its folder, which is what --sets matches."""
    return config.parent.name


def natural_key(path: Path):
    """Sort pareto2 before pareto10."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.name)]


def is_model(folder: Path) -> bool:
    """A model is a folder holding front.yaml and/or rear.yaml."""
    return folder.is_dir() and any((folder / n).is_file() for n in GEOMETRY_NAMES)


def resolve_folder(value: Path, kind: str) -> Path:
    """A folder given on the command line: a path, or a name under models/."""
    for candidate in (value.expanduser(), MODELS_DIR / value):
        if candidate.is_dir():
            return candidate.resolve()
    available = sorted(p.name for p in MODELS_DIR.iterdir() if p.is_dir())
    sys.exit(f"{kind} not found: {value}\n"
             f"It is neither a folder nor a name under {MODELS_DIR}, which holds: "
             f"{', '.join(available)}")


def resolve_model(value: Path) -> Path:
    """The --model folder, which must be a model rather than a batch of them."""
    folder = resolve_folder(value, "model")
    if not is_model(folder):
        sys.exit(f"{folder} is not a model: it holds neither "
                 f"{' nor '.join(GEOMETRY_NAMES)}.\n"
                 "To run every model inside a folder, use --batch.")
    return folder


def discover_batch(folder: Path) -> list[Path]:
    """Every model folder directly inside `folder`, in natural order."""
    return sorted((p for p in folder.iterdir() if is_model(p)), key=natural_key)


def select(configs: list[Path], wanted: list[str] | None, kind: str) -> list[Path]:
    """Filter discovered configurations by folder name.

    An unmatched name is an error, not an empty run: a typo must not look like
    a clean "nothing to do".
    """
    if wanted is None:
        return configs
    known = {label(config): config for config in configs}
    missing = [name for name in wanted if name not in known]
    if missing:
        sys.exit(
            f"unknown {kind}: {', '.join(missing)}.\n"
            f"Available: {', '.join(known) or '(none found)'}"
        )
    return [known[name] for name in wanted]


def parse_list(value: str | None) -> list[str] | None:
    """Split a comma-separated CLI list, tolerating spaces."""
    if value is None:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def default_geometry(config: Path) -> Path:
    """The geometry a sweep set's run.yaml names, resolved against run.yaml."""
    import yaml

    raw = yaml.safe_load(config.read_text()) or {}
    geometry = Path(str(raw.get("geometry", "")))
    if not geometry.is_absolute():
        geometry = (config.parent / geometry).resolve()
    return geometry


# ==========================================================================
# Planning
# ==========================================================================
@dataclass
class ModelRun:
    """One model folder and everything planned against it."""

    folder: Path
    name: str
    sets: list  # runner.SetPlan
    forces: Path | None
    plan_errors: list[str]


def forces_cases(config: Path) -> Path | None:
    """The shared cases.csv, unless this forces.yaml names its own."""
    import yaml

    if (yaml.safe_load(config.read_text()) or {}).get("cases") is None:
        return CASES_FILE
    return None


def plan_models(args, models: list[Path | None], sweep_sets: list[Path],
                selected_sets: list[Path], runner) -> list[ModelRun]:
    """Plan every (model, set). A set that will not plan is recorded, not fatal."""
    runs: dict[Path, ModelRun] = {}

    def run_for(folder: Path) -> ModelRun:
        if folder not in runs:
            runs[folder] = ModelRun(folder, folder.name, [], None, [])
        return runs[folder]

    def options(geometry: Path | None):
        return runner.SweepOptions(
            geometry=geometry,
            side=args.side,
            only=parse_list(args.only),
            skip=parse_list(args.skip) or [],
            plots=parse_list(args.plots),
            gifs=parse_list(args.gifs),
            no_plots=args.no_plots,
            no_gifs=args.no_gifs,
            no_joints=args.no_joints,
            report_only=args.report_only,
            solve_only=args.solve_only,
            dry_run=args.dry_run,
            on_bad_solve=args.on_bad_solve,
        )

    for model in models:
        for config in sweep_sets:
            if model is not None:
                geometry = model / default_geometry(config).name
                if not geometry.is_file():
                    run_for(model)  # a front-only model is normal: note, not fail
                    continue
            else:
                geometry = args.geometry or default_geometry(config)
            folder = geometry.parent
            try:
                plan = runner.plan_sweep_set(config, options(geometry))
            except runner.SweepSetError as error:
                run_for(folder).plan_errors.append(f"{label(config)}: {error}")
                continue
            run_for(plan.model).sets.append(plan)

        if args.no_forces:
            continue
        if model is not None:
            folders = [model]
        elif args.geometry is not None:
            folders = [args.geometry.parent]
        else:
            # Forces follow the geometry each selected set names, even with
            # --no-sweeps.
            folders = list(dict.fromkeys(default_geometry(c).parent
                                         for c in selected_sets))
        for folder in folders:
            config = folder / FORCES_CONFIG_NAME
            if config.is_file():
                run_for(folder).forces = config

    return list(runs.values())


# ==========================================================================
# Tasks
# ==========================================================================
def identity(run: ModelRun, set_name: str, sweep: str, kind: str) -> dict:
    """The fields every result of this task carries back, whatever happens."""
    return {"model": run.name, "folder": str(run.folder), "set": set_name,
            "sweep": sweep, "kind": kind}


def solve_tasks(runs: list[ModelRun], report_only: bool) -> list:
    """Phase 2: every sweep of every model, and every force solve."""
    tasks = []
    for run in runs:
        logs = run.folder / LOGS_DIRNAME
        if not report_only:
            for plan in run.sets:
                for sweep in plan.sweeps:
                    ident = identity(run, plan.name, sweep.name, "solve")
                    tasks.append(scheduler.Task(
                        key=f"solve|{run.folder}|{plan.name}|{sweep.name}",
                        weight=float(sweep.steps or 1),
                        payload={
                            "kind": "solve", "identity": ident,
                            "geometry": str(plan.geometry),
                            "sweep": str(sweep.resolved),
                            "csv": str(sweep.csv),
                            "frames": str(sweep.frames) if sweep.animate else "",
                            "log": str(logs / plan.name / f"{sweep.name}.log"),
                        }))
        if run.forces is not None:
            cases = forces_cases(run.forces)
            tasks.append(scheduler.Task(
                key=f"forces|{run.folder}",
                weight=1000.0,  # the longest single task; start it first
                payload={
                    "kind": "forces",
                    "identity": identity(run, "", "", "forces"),
                    "config": str(run.forces),
                    "cases": str(cases) if cases else "",
                    "log": str(logs / "forces.log"),
                }))
    return tasks


def existing_results(run: ModelRun, plan) -> list[dict]:
    """--report-only: treat each planned sweep's CSV on disk as its result."""
    out = []
    for sweep in plan.sweeps:
        status = "ok" if sweep.csv.is_file() else "missing"
        out.append({**identity(run, plan.name, sweep.name, "solve"),
                    "status": status,
                    "message": "" if status == "ok" else "no CSV on disk"})
    return out


def render_tasks(runs: list[ModelRun], solved: dict, args) -> list:
    """Phase 3: each set's report, and an animation per sweep that solved."""
    tasks = []
    for run in runs:
        logs = run.folder / LOGS_DIRNAME
        for plan in run.sets:
            results = [solved.get((str(run.folder), plan.name, s.name))
                       for s in plan.sweeps]
            results = [r for r in results if r is not None]
            if args.report_only:
                results = existing_results(run, plan)
            if plan.report_wanted:
                tasks.append(scheduler.Task(
                    key=f"report|{run.folder}|{plan.name}",
                    weight=1e6,  # reports are what matters most; run them first
                    payload={
                        "kind": "report",
                        "identity": identity(run, plan.name, "", "report"),
                        "resolved_config": str(plan.resolved_config),
                        "outputs": str(plan.outputs),
                        "report": str(plan.report),
                        "reporter": plan.reporter,
                        "results": results,
                        "log": str(logs / plan.name / "_report.log"),
                    }))
            if args.report_only:
                continue
            ok = {r["sweep"] for r in results if r.get("status") in ("ok", "warn")}
            for sweep in plan.sweeps:
                if not sweep.animate or sweep.name not in ok:
                    continue
                tasks.append(scheduler.Task(
                    key=f"animate|{run.folder}|{plan.name}|{sweep.name}",
                    weight=2.0 * (sweep.steps or 1),
                    payload={
                        "kind": "animate",
                        "identity": identity(run, plan.name, sweep.name, "animate"),
                        "geometry": str(plan.geometry),
                        "frames": str(sweep.frames),
                        "out": str(sweep.animation),
                        "fps": sweep.fps,
                        "dpi": sweep.dpi,
                        "log": str(logs / plan.name / f"{sweep.name}.animate.log"),
                    }))
    return tasks


# ==========================================================================
# Reporting what happened
# ==========================================================================
def describe(result: dict) -> str:
    """One line: what failed and where, or nothing for a clean result."""
    import runner

    status = result.get("status", "?")
    if status == "ok":
        return ""
    parts = [runner.describe_failure(result), result.get("message", "")]
    return "; ".join(p for p in parts if p)


def task_name(result: dict) -> str:
    """How a task is named in the console, run.log and the summary."""
    kind = result.get("kind", "?")
    if kind == "forces":
        return "forces"
    if kind == "report":
        return f"{result.get('set')} report"
    name = f"{result.get('set')}/{result.get('sweep')}"
    return name + (" (animation)" if kind == "animate" else "")


class Progress:
    """Prints one line per finished task."""

    def __init__(self, total: int, show_model: bool):
        self.total = total
        self.done = 0
        self.show_model = show_model
        self.width = len(str(total))

    def __call__(self, result: dict) -> None:
        self.done += 1
        where = f"{result.get('model', ''):14s} " if self.show_model else ""
        detail = describe(result)
        line = (f"   [{self.done:>{self.width}}/{self.total}] {where}"
                f"{task_name(result):34s} {result.get('status', '?'):8s} "
                f"{result.get('seconds', 0):6.1f} s")
        if detail:
            line += f"  {detail}"
        print(line[:240], flush=True)


def write_run_log(run: ModelRun, results: list[dict], header: list[str]) -> Path:
    """<model>/run.log: one line per task of this model, newest run only."""
    lines = list(header)
    for message in run.plan_errors:
        lines.append(f"PLAN FAILED  {message}")
    if run.plan_errors:
        lines.append("")
    lines.append(f"{'task':40s} {'status':9s} {'time':>8s}  detail")
    for r in results:
        lines.append(f"{task_name(r):40s} {r.get('status', '?'):9s} "
                     f"{r.get('seconds', 0):7.1f}s  {describe(r)}")
        if r.get("status") not in GOOD and r.get("log"):
            lines.append(f"{'':40s} log: {r['log']}")
    path = run.folder / RUN_LOG_NAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def summary_matrix(
    runs: list[ModelRun], by_model: dict
) -> tuple[list[str], list[list[str]]]:
    """Columns: every set/sweep solved anywhere, then forces, report(s), anims."""
    columns: list[str] = []
    for run in runs:
        for r in by_model.get(str(run.folder), []):
            if r.get("kind") == "solve":
                col = f"{r['set']}/{r['sweep']}"
                if col not in columns:
                    columns.append(col)
    rows = []
    for run in runs:
        results = by_model.get(str(run.folder), [])
        cells = {f"{r['set']}/{r['sweep']}": r
                 for r in results if r.get("kind") == "solve"}
        row = [run.name]
        for col in columns:
            r = cells.get(col)
            row.append(STATUS_LETTER.get(r["status"], "?") if r else "-")
        forces = [r for r in results if r.get("kind") == "forces"]
        row.append(STATUS_LETTER.get(forces[0]["status"], "?") if forces else "-")
        reports = [r for r in results if r.get("kind") == "report"]
        row.append("".join(STATUS_LETTER.get(r["status"], "?") for r in reports) or "-")
        anims = [r for r in results if r.get("kind") == "animate"]
        good = sum(r.get("status") in GOOD for r in anims)
        row.append(f"{good}/{len(anims)}" if anims else "-")
        rows.append(row)
    return ["model", *columns, "forces", "report", "anims"], rows


def write_batch_summary(folder: Path, runs: list[ModelRun], by_model: dict,
                        header: list[str]) -> Path:
    """<batch>/batch_summary.md (matrix, pass counts, failures) and .csv."""
    import csv

    columns, rows = summary_matrix(runs, by_model)
    solve_cols = columns[1:-3]
    lines = [f"# Batch summary: {folder.name}", "", *[f"- {h}" for h in header], ""]
    lines += ["Status letters: `.` ok, `w` solved with solver warnings, "
              "`L` lock-out (no pose exists at some step), `G` geometry does not "
              "build, `M` out of memory after retries, `E` error, `?` missing, "
              "`-` not run.", ""]

    lines += ["## Matrix", "", "| " + " | ".join(columns) + " |",
              "| " + " | ".join("---" for _ in columns) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    lines.append("")

    lines += ["## Pass count per sweep", "", "| sweep | solved | of |",
              "| --- | --- | --- |"]
    for i, col in enumerate(solve_cols, start=1):
        ran = [row[i] for row in rows if row[i] != "-"]
        lines.append(f"| {col} | {sum(c in '.w' for c in ran)} | {len(ran)} |")
    lines.append("")

    clean = [row[0] for row in rows
             if all(c in ".w-" for c in row[1:len(solve_cols) + 1])
             and row[-3] in ".w-"]
    lines += [f"## Models with every sweep solved ({len(clean)} of {len(rows)})", "",
              ", ".join(clean) or "(none)", ""]

    lines += ["## Failures", ""]
    any_failure = False
    for run in runs:
        for message in run.plan_errors:
            any_failure = True
            lines.append(f"- **{run.name}** plan: {message}")
        for r in by_model.get(str(run.folder), []):
            if r.get("status") in GOOD:
                continue
            any_failure = True
            lines.append(f"- **{run.name}** {task_name(r)}: {r.get('status')} - "
                         f"{describe(r)}  \n  log: `{r.get('log', '')}`")
    if not any_failure:
        lines.append("(none)")
    lines.append("")

    md = folder / f"{BATCH_SUMMARY_NAME}.md"
    md.write_text("\n".join(lines), encoding="utf-8")

    with open(folder / f"{BATCH_SUMMARY_NAME}.csv", "w", newline="",
              encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["model", "kind", "set", "sweep", "status", "steps_ok",
                         "n_steps", "fail_step", "at", "last_good", "message",
                         "seconds", "peak_mb", "attempts", "log"])
        for run in runs:
            for r in by_model.get(str(run.folder), []):
                writer.writerow([run.name, r.get("kind"), r.get("set"), r.get("sweep"),
                                 r.get("status"), r.get("steps_ok", ""),
                                 r.get("n_steps", ""), r.get("fail_step", ""),
                                 r.get("at", ""), r.get("last_good", ""),
                                 r.get("message", ""), r.get("seconds", ""),
                                 r.get("peak_mb", ""), r.get("attempts", ""),
                                 r.get("log", "")])
    return md


def print_matrix(runs: list[ModelRun], by_model: dict) -> None:
    """The status matrix, one row per model, for the console."""
    columns, rows = summary_matrix(runs, by_model)
    if not rows:
        return
    sweep_columns = columns[1:-3]
    several_sets = len({c.split("/")[0] for c in sweep_columns}) > 1
    # "01" for one set; "f01" / "r01" when several sets share the matrix.
    short = [(c.split("/")[0][:1] if several_sets else "") + c.split("/")[-1][:2]
             for c in sweep_columns]
    cell = max([2, *map(len, short)])
    width = max(len(r[0]) for r in rows) + 2
    print("\n" + " " * width + " ".join(f"{c:>{cell}s}" for c in short)
          + "   forces report anims")
    for row in rows:
        print(f"{row[0]:{width}s}" + " ".join(f"{c:>{cell}s}" for c in row[1:-3])
              + f"   {row[-3]:>6s} {row[-2]:>6s} {row[-1]:>5s}")
    print("   . ok   w warnings   L lock-out   G geometry   M memory   E error   "
          "- not run")


def dry_run(runs: list[ModelRun]) -> None:
    """Print what would run, and validate each force configuration."""
    for run in runs:
        print(f"{run.name}  ({run.folder})")
        for message in run.plan_errors:
            print(f"   PLAN FAILED  {message}")
        for plan in run.sets:
            anims = [s.name for s in plan.sweeps if s.animate]
            print(f"   {plan.name}: {len(plan.sweeps)} sweep(s) "
                  f"({', '.join(s.name for s in plan.sweeps)})")
            if anims:
                print(f"      animations: {', '.join(anims)}")
        if run.forces is not None:
            from kinematics.cli.commands.forces import load_inputs

            try:
                loaded = load_inputs(run.forces, cases=forces_cases(run.forces))
                print(f"   forces: valid, {len(loaded.cases)} case(s), "
                      f"{len(loaded.run.corners)} corner(s)")
            except Exception as error:  # noqa: BLE001
                print(f"   forces: INVALID - {error}")
    print("\n(dry run: nothing solved, nothing written)")


# ==========================================================================
# Entry point
# ==========================================================================
def build_parser() -> argparse.ArgumentParser:
    """Every flag; see the module docstring for the workflow."""
    parser = argparse.ArgumentParser(
        prog="Working/run_all.py",
        description=__doc__,
        # Abbreviations would let `--par 4` through, which a batch then could
        # not strip before passing the rest of the command line to each model.
        allow_abbrev=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="These flags override run.yaml for this invocation only; "
        "run.yaml is the only other place anything is configured. "
        "See RUNNING.md for its key reference.",
    )

    which = parser.add_argument_group("which model(s)")
    which.add_argument(
        "--model",
        type=Path,
        default=None,
        help="the model folder to run: a name under Working/models/ (aurora, "
        "aurora_evo, ...) or a path. Default: the geometry each run.yaml names",
    )
    which.add_argument(
        "--batch",
        type=Path,
        default=None,
        help="run every model folder inside this one (e.g. an optimizer run, "
        "opt_<timestamp>): a name under Working/models/ or a path",
    )

    what = parser.add_argument_group("what runs")
    what.add_argument(
        "--sets",
        default=None,
        help="comma-separated sweep sets, by folder name under sweep_sets/ "
        "(default: all of them)",
    )
    what.add_argument(
        "--config",
        type=Path,
        default=None,
        help="run one sweep set by path to its run.yaml, for a set outside "
        "sweep_sets/<name>/. Mutually exclusive with --sets",
    )
    what.add_argument(
        "--no-sweeps", action="store_true", help="skip the kinematic sweep sets"
    )
    what.add_argument(
        "--no-forces",
        action="store_true",
        help="skip the static force solve (which is on by default)",
    )

    sweeps = parser.add_argument_group(
        "inside each sweep set", "these override the set's run.yaml for this run only"
    )
    sweeps.add_argument(
        "--geometry",
        type=Path,
        default=None,
        help="run one set against a specific geometry file. Prefer --model",
    )
    sweeps.add_argument(
        "--side",
        default=None,
        choices=("left", "right"),
        help="which corner the per-corner rows report (one set at a time)",
    )
    sweeps.add_argument(
        "--only", default=None, help="comma-separated sweeps to run, e.g. --only 01,09"
    )
    sweeps.add_argument(
        "--skip", default=None, help="comma-separated sweeps to leave out"
    )
    sweeps.add_argument(
        "--plots",
        default=None,
        help="comma-separated sweeps that get a figure; the others get none",
    )
    sweeps.add_argument(
        "--gifs", default=None, help="comma-separated sweeps that get an animation"
    )
    sweeps.add_argument("--no-plots", action="store_true", help="no figures at all")
    sweeps.add_argument("--no-gifs", action="store_true", help="no animations at all")
    sweeps.add_argument(
        "--no-joints",
        action="store_true",
        help="drop the bearing misalignment section from the report",
    )
    sweeps.add_argument(
        "--report-only",
        action="store_true",
        help="rebuild the reports from the CSVs already in sweep_outputs/, "
        "solving and animating nothing",
    )
    sweeps.add_argument(
        "--solve-only", action="store_true",
        help="solve the sweeps (and animate them), but build no report"
    )
    sweeps.add_argument(
        "--on-bad-solve",
        default=None,
        choices=("off", "warn", "fail"),
        help="what to do about non-converged or high-residual steps",
    )

    machine = parser.add_argument_group(
        "machine", "the pool is sized automatically; see sweep_sets/scheduler.py")
    machine.add_argument(
        "--workers",
        type=int,
        default=None,
        help="most worker processes to run at once (default: as many as the "
        "physical cores and free memory allow)",
    )
    for old in REMOVED_FLAGS:
        machine.add_argument(old, default=None, help=argparse.SUPPRESS)

    other = parser.add_argument_group("other")
    other.add_argument(
        "--list",
        action="store_true",
        help="print the sweep sets and models found, then stop",
    )
    other.add_argument(
        "--dry-run",
        action="store_true",
        help="validate every configuration and print what would run, but solve "
        "nothing and write no results. A complete check of Working/",
    )
    return parser


def main() -> None:
    """Parse the command line, plan, run both phases, and summarise."""
    try:
        sys.stdout.reconfigure(errors="replace")  # type: ignore[attr-defined]
    except AttributeError:
        pass
    parser = build_parser()
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    for old, new in REMOVED_FLAGS.items():
        if getattr(args, old.lstrip("-").replace("-", "_"), None) is not None:
            parser.error(f"{old} was removed; use {new}")

    # A path typed on the command line means "relative to where I am".
    for flag in ("geometry", "config"):
        path = getattr(args, flag, None)
        if path is not None:
            setattr(args, flag, path.expanduser().resolve())

    if args.list:
        print("sweep sets:")
        for config in discover_sweep_sets():
            print(f"   {label(config):10s} {config}")
        print(f"models (in {MODELS_DIR}):")
        for folder in sorted(MODELS_DIR.iterdir(), key=natural_key):
            if is_model(folder):
                forces = "forces" if (folder / FORCES_CONFIG_NAME).is_file() else ""
                print(f"   {folder.name:20s} {forces}")
            elif folder.is_dir() and discover_batch(folder):
                print(f"   {folder.name:20s} batch of {len(discover_batch(folder))}")
        return

    if args.config and args.sets:
        parser.error("--config names one sweep set by path and --sets names them by "
                     "folder; use one or the other")
    if args.report_only and args.solve_only:
        parser.error("--report-only and --solve-only are opposites")
    if sum(x is not None for x in (args.model, args.batch, args.geometry)) > 1:
        parser.error("--model, --batch and --geometry each say which geometry "
                     "to run; give one of them")
    if args.workers is not None and args.workers < 1:
        parser.error("--workers must be at least 1")

    # ---- which models -------------------------------------------------
    batch_folder = None
    if args.batch is not None:
        batch_folder = resolve_folder(args.batch, "batch folder")
        models: list[Path | None] = list(discover_batch(batch_folder))
        if not models:
            sys.exit(f"no models in {batch_folder}: no subfolder holds "
                     f"{' or '.join(GEOMETRY_NAMES)}.\n"
                     "Did export_pareto.py run for this optimizer run?")
    elif args.model is not None:
        models = [resolve_model(args.model)]
    else:
        models = [None]

    # ---- which sweep sets ---------------------------------------------
    if args.config:
        if not args.config.is_file():
            sys.exit(f"run configuration not found: {args.config}")
        sweep_sets = [args.config]
    else:
        sweep_sets = select(discover_sweep_sets(), parse_list(args.sets), "sweep set")
    selected_sets = list(sweep_sets)
    if args.no_sweeps:
        sweep_sets = []

    conflicting = [f for f in PER_SET_FLAGS if getattr(args, f, None) is not None]
    if conflicting and len(sweep_sets) > 1:
        names = ", ".join(f"--{f}" for f in conflicting)
        sys.exit(f"{names} describes a single sweep set, but {len(sweep_sets)} are "
                 f"selected ({', '.join(label(c) for c in sweep_sets)}).\n"
                 "Narrow it with --sets or --config.")

    import runner
    import tasks as task_functions

    machine = scheduler.detect_machine()
    started = time.perf_counter()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Working  : {HERE}")
    print(f"machine  : {machine.describe()}")
    if batch_folder is not None:
        print(f"batch    : {batch_folder} ({len(models)} models)")
    print(f"sweeps   : {', '.join(label(c) for c in sweep_sets) or '(none)'}")

    # ---- 1. plan ------------------------------------------------------
    runs = plan_models(args, models, sweep_sets, selected_sets, runner)
    planned = sum(len(p.sweeps) for r in runs for p in r.sets)
    plan_errors = sum(len(r.plan_errors) for r in runs)
    print(f"planned  : {planned} sweep(s) across {len(runs)} model(s)"
          + (f", {plan_errors} set(s) failed to plan" if plan_errors else ""))
    if not runs or (planned == 0 and not any(r.forces for r in runs)
                    and not plan_errors):
        sys.exit("nothing to run. --no-sweeps and --no-forces together leave no "
                 "work, or no selected model has the geometry the sets need.")
    if args.dry_run:
        print()
        dry_run(runs)
        return

    show_model = len(runs) > 1
    all_results: list[dict] = []
    phases: list[scheduler.PhaseReport] = []
    interrupted = False

    try:
        # ---- 2. solve -------------------------------------------------
        tasks = solve_tasks(runs, args.report_only)
        print()
        solved: dict = {}
        if tasks:
            results, phase = scheduler.run_phase(
                "solve", tasks, task_functions.execute, worker_mb=SOLVE_WORKER_MB,
                cap=args.workers, on_result=Progress(len(tasks), show_model))
            phases.append(phase)
            all_results += results
            interrupted = phase.interrupted
            solved = {(r["folder"], r["set"], r["sweep"]): r
                      for r in results if r.get("kind") == "solve"}

        # ---- 3. report + animate ---------------------------------------
        tasks = [] if interrupted else render_tasks(runs, solved, args)
        if tasks:
            print()
            results, phase = scheduler.run_phase(
                "report + animate", tasks, task_functions.execute,
                worker_mb=RENDER_WORKER_MB,
                cap=args.workers, max_tasks_per_child=RENDER_TASKS_PER_WORKER,
                on_result=Progress(len(tasks), show_model))
            phases.append(phase)
            all_results += results
            interrupted = phase.interrupted
    except KeyboardInterrupt:  # between phases
        interrupted = True

    # ---- 4. summary ----------------------------------------------------
    if interrupted:
        print("\ninterrupted - the summary covers only what finished")
    minutes = (time.perf_counter() - started) / 60
    header = [f"started {stamp}, {minutes:.1f} min"
              + (" (INTERRUPTED)" if interrupted else ""),
              "command: run_all.py " + " ".join(argv),
              f"machine: {machine.describe()}"]
    for phase in phases:
        header.append(
            f"{phase.label}: {phase.workers} worker(s) (limited by "
            f"{phase.limited_by}), peak {phase.worker_peak_mb:.0f} MB/worker, "
            f"{phase.retries} retried, {phase.seconds:.0f} s"
            + (f", ended at {phase.final_limit} worker(s)"
               if phase.final_limit != phase.workers else ""))

    by_model: dict[str, list[dict]] = {}
    for r in all_results:
        by_model.setdefault(r.get("folder", ""), []).append(r)
    for run in runs:
        write_run_log(run, by_model.get(str(run.folder), []), [*header, ""])

    print()
    for line in header[2:]:
        print(line)
    if show_model or len(runs) == 1:
        print_matrix(runs, by_model)
    if batch_folder is not None:
        md = write_batch_summary(batch_folder, runs, by_model, header)
        print(f"\nsummary  : {md}")
    print(f"run logs : <model>/{RUN_LOG_NAME}, tracebacks in <model>/{LOGS_DIRNAME}/")

    failed = [r for r in all_results if r.get("status") not in GOOD]
    if interrupted:
        sys.exit(130)
    if failed or plan_errors:
        sys.exit(f"\n{len(failed)} task(s) failed, {plan_errors} set(s) failed to "
                 f"plan ({minutes:.1f} min). See the summary above.")
    print(f"\ndone. {len(all_results)} task(s) in {minutes:.1f} min.")


if __name__ == "__main__":
    main()
