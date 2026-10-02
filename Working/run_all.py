#!/usr/bin/env python3
"""
The entry point for everything under Working/: the kinematic sweep sets, then
the static force solve, for one model or a whole folder of them.
Cross-platform, and independent of your current working directory.

    uv run python Working/run_all.py                          Aurora, everything
    uv run python Working/run_all.py --model aurora_evo       another model
    uv run python Working/run_all.py --sets front --no-forces one sweep set only
    uv run python Working/run_all.py --batch opt_2026-10-02_1430 ...
                                                              every model in a folder

A MODEL is a folder under Working/models/ holding front.yaml and/or rear.yaml,
and optionally forces.yaml. Load cases are shared: Working/cases.csv. Everything
a run writes lands inside the model folder:

    models/<model>/sweep_outputs/<set>/   one CSV per sweep, and the animations
    models/<model>/report/<set>/          report.md, plots, summary.csv
    models/<model>/forces/                forces.csv, load_transfer.csv

--model and --batch take a folder name under Working/models/ or a path. A batch
runs every model folder directly inside the one named (an optimizer run's
pareto1, pareto2, ...), several at once, each logging to <model>/run.log.

THIS IS THE ONLY COMMAND; `sweep_sets/runner.py` is a library this file calls.
A sweep set is chosen with --sets (folder name) or --config (path); every other
flag narrows what runs inside the sets chosen. Each set's run.yaml names the
geometry FILE it reads (front.yaml or rear.yaml); --model picks the folder.

Forces run by default, because a sweep set and the force solve read the SAME
geometry: a hardpoint edit invalidates both. A model without a forces.yaml is
skipped for forces, with a note.

Stages run independently: every stage is attempted, and the exit code names
everything that failed.

See the repository README.md for the workflow, sweep_sets/RUNNING.md for the
run.yaml keys, and models/FORCES.md for the force solve.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent  # Working/
SWEEP_SETS_DIR = HERE / "sweep_sets"
MODELS_DIR = HERE / "models"

# A sweep set is a folder with a run.yaml.
SWEEP_SET_GLOB = "*/run.yaml"

# A model's force configuration, beside its geometry.
FORCES_CONFIG_NAME = "forces.yaml"

# Geometry files that make a folder a model.
GEOMETRY_NAMES = ("front.yaml", "rear.yaml")

# The load cases every model's force solve uses (a forces.yaml with its own
# `cases:` key overrides this for that model).
CASES_FILE = HERE / "cases.csv"

# What a batch writes each model's console output to, inside the model folder.
BATCH_LOG_NAME = "run.log"

# Overrides that describe ONE set and cannot mean anything across several.
PER_SET_FLAGS = ("geometry", "side")

# The kinematics CLI, on this interpreter. See sweep_sets/runner.py.
KINEMATICS = [sys.executable, "-m", "kinematics.cli"]


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
# Stages
# ==========================================================================
def import_runner():
    """Import the sweep-set library that lives beside the sets.

    Lazy and by path: --help and --list should not pay for yaml, and
    sweep_sets/ is a working directory rather than an installed module.
    """
    if str(SWEEP_SETS_DIR) not in sys.path:
        sys.path.insert(0, str(SWEEP_SETS_DIR))
    import runner

    return runner


def force_command(config: Path, dry_run: bool) -> list[str]:
    """Build the command for one model's force solve.

    A subprocess, unlike the sweep sets, because `kinematics forces` is the
    CLI command with its own diagnostics and exit codes. Results go to
    forces/ beside the configuration.
    """
    cmd = [*KINEMATICS, "forces", "--config", str(config)]
    # One set of load cases for every model, unless a model names its own.
    import yaml

    if (yaml.safe_load(config.read_text()) or {}).get("cases") is None:
        cmd += ["--cases", str(CASES_FILE)]
    if dry_run:
        # The force CLI's own --dry-run validates every input and solves
        # without writing, so forwarding it keeps --dry-run a complete check.
        cmd.append("--dry-run")
    return cmd


# ==========================================================================
# Batch: one child run_all.py per model, several at once
# ==========================================================================
# Flags that configure the batch itself, so are not passed on to each model.
BATCH_ONLY_FLAGS = {"--batch": True, "--parallel": True, "--gif-workers": True}


def forwarded_args(argv: list[str]) -> list[str]:
    """The command line minus the batch-only flags (and their values)."""
    out, skip = [], False
    for arg in argv:
        if skip:
            skip = False
            continue
        name = arg.split("=", 1)[0]
        if name in BATCH_ONLY_FLAGS:
            skip = "=" not in arg and BATCH_ONLY_FLAGS[name]
            continue
        out.append(arg)
    return out


def batch_sizes(n_models: int, parallel: int | None,
                gif_workers: int | None) -> tuple[int, int]:
    """
    How many models run at once, and how many GIF workers each one gets.

    Auto: one model per 8 logical CPUs (at least 1, at most 16), and the CPUs
    shared between them for frame rendering. 16 CPUs -> 2 models x 8 workers;
    128 -> 16 x 8. Every concurrent model holds one animation's frames in
    memory (~10 MB per frame at dpi 200), so lower --parallel if RAM runs out.
    """
    cpus = os.cpu_count() or 1
    if not parallel:
        parallel = max(1, min(16, cpus // 8))
    parallel = max(1, min(parallel, n_models))
    if not gif_workers:
        gif_workers = max(1, cpus // parallel)
    return parallel, gif_workers


def run_batch(folder: Path, args, argv: list[str]) -> None:
    """Run every model in `folder` as its own run_all.py, `parallel` at once."""
    models = discover_batch(folder)
    if not models:
        sys.exit(f"no models in {folder}: no subfolder holds "
                 f"{' or '.join(GEOMETRY_NAMES)}.\n"
                 "Did export_pareto.py run for this optimizer run?")
    parallel, gif_workers = batch_sizes(len(models), args.parallel,
                                        args.gif_workers)
    passthrough = forwarded_args(argv)

    print(f"batch    : {folder}")
    print(f"models   : {len(models)} ({models[0].name} ... {models[-1].name})")
    print(f"parallel : {parallel} model(s) at once, {gif_workers} GIF worker(s) each")
    print(f"logs     : <model>/{BATCH_LOG_NAME}")
    print(f"each runs: run_all.py --model <model> {' '.join(passthrough)}\n")

    def one(model: Path) -> tuple[Path, int, float]:
        cmd = [sys.executable, str(Path(__file__).resolve()), "--model", str(model),
               "--gif-workers", str(gif_workers), *passthrough]
        started = time.perf_counter()
        with open(model / BATCH_LOG_NAME, "w", encoding="utf-8") as log:
            log.write("$ " + " ".join(cmd) + "\n\n")
            log.flush()
            code = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
        return model, code, time.perf_counter() - started

    failed: list[str] = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = [pool.submit(one, model) for model in models]
        for done, future in enumerate(as_completed(futures), start=1):
            model, code, seconds = future.result()
            status = "ok" if code == 0 else f"FAILED - see {model / BATCH_LOG_NAME}"
            print(f"   [{done:>{len(str(len(models)))}}/{len(models)}] "
                  f"{model.name:20s} {seconds:6.0f} s  {status}", flush=True)
            if code != 0:
                failed.append(model.name)

    minutes = (time.perf_counter() - started) / 60
    if failed:
        sys.exit(f"\n{len(failed)} of {len(models)} model(s) failed "
                 f"({minutes:.1f} min): {', '.join(failed)}")
    print(f"\ndone. {len(models)} model(s) in {minutes:.1f} min.")


# ==========================================================================
# Entry point
# ==========================================================================
def build_parser() -> argparse.ArgumentParser:
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
    which.add_argument(
        "--parallel",
        type=int,
        default=None,
        help="--batch only: models run at once (default: one per 8 CPUs)",
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
        "--gif-workers",
        type=int,
        default=None,
        help="processes rendering each animation's frames (default: every "
        "logical CPU; in a batch, the CPUs shared between the models)",
    )
    sweeps.add_argument(
        "--no-joints",
        action="store_true",
        help="drop the bearing misalignment section from the report",
    )
    sweeps.add_argument(
        "--jobs", type=int, default=None, help="parallel solver processes"
    )
    sweeps.add_argument(
        "--report-only",
        action="store_true",
        help="rebuild the reports from the CSVs already in sweep_outputs/, "
        "solving nothing",
    )
    sweeps.add_argument(
        "--solve-only", action="store_true", help="solve the sweeps and stop, no report"
    )
    sweeps.add_argument(
        "--on-bad-solve",
        default=None,
        choices=("off", "warn", "fail"),
        help="what to do about non-converged or high-residual steps",
    )

    other = parser.add_argument_group("other")
    other.add_argument(
        "--list",
        action="store_true",
        help="print the sweep sets and models found, then stop",
    )
    other.add_argument(
        "--dry-run",
        action="store_true",
        help="validate every configuration and print every command, but solve "
        "nothing and write no results. A complete check of Working/",
    )
    return parser


def main() -> None:
    """Parse the command line and run the batch, or the stages for one model."""
    parser = build_parser()
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    # A path typed on the command line means "relative to where I am", so pin
    # it to the current directory now. Left relative, --geometry would reach
    # the runner and be resolved against the sweep set's folder, which is the
    # rule for a `geometry:` written INSIDE run.yaml, not for one typed here.
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
        parser.error(
            "--config names one sweep set by path and --sets names them by "
            "folder; use one or the other"
        )
    if args.report_only and args.solve_only:
        parser.error("--report-only and --solve-only are opposites")
    if sum(x is not None for x in (args.model, args.batch, args.geometry)) > 1:
        parser.error("--model, --batch and --geometry each say which geometry "
                     "to run; give one of them")
    if args.parallel is not None and args.batch is None:
        parser.error("--parallel only applies to --batch")

    if args.batch is not None:
        run_batch(resolve_folder(args.batch, "batch folder"), args, argv)
        return

    model = resolve_model(args.model) if args.model is not None else None

    # ---- which sweep sets --------------------------------------------
    if args.config:
        if not args.config.is_file():
            sys.exit(f"run configuration not found: {args.config}")
        sweep_sets = [args.config]
    else:
        sweep_sets = select(discover_sweep_sets(), parse_list(args.sets), "sweep set")
    if args.no_sweeps:
        sweep_sets = []

    # ---- the geometry each set runs ----------------------------------
    # A model swaps the folder and keeps the file run.yaml names, so the front
    # set reads <model>/front.yaml. A set the model has no file for is
    # skipped, not failed: a front-only model is a normal thing to have.
    targets: list[tuple[Path, Path | None]] = []
    skipped: list[str] = []
    for config in sweep_sets:
        if model is not None:
            geometry = model / default_geometry(config).name
            if not geometry.is_file():
                skipped.append(f"{label(config)} (no {geometry.name} in {model.name})")
                continue
            targets.append((config, geometry))
        else:
            targets.append((config, args.geometry))

    # ---- which force configurations ----------------------------------
    # Forces follow the geometry: the model folder, else the folder of each
    # geometry being run.
    if model is not None:
        folders = [model]
    elif args.geometry is not None:
        folders = [args.geometry.parent]
    else:
        folders = list(dict.fromkeys(
            default_geometry(config).parent for config in sweep_sets or
            select(discover_sweep_sets(), parse_list(args.sets), "sweep set")))
    force_configs: list[Path] = []
    if not args.no_forces:
        for folder in folders:
            config = folder / FORCES_CONFIG_NAME
            if config.is_file():
                force_configs.append(config)
            else:
                skipped.append(f"forces ({folder.name} has no {FORCES_CONFIG_NAME})")

    if not targets and not force_configs:
        sys.exit(
            "nothing to run. "
            + ("; ".join(skipped) + ". " if skipped else "")
            + "--no-sweeps and --no-forces together leave no work."
        )

    # These each describe one set; applying them to several would run every
    # set against the same car, into the same output folder.
    conflicting = [
        flag for flag in PER_SET_FLAGS if getattr(args, flag, None) is not None
    ]
    if conflicting and len(targets) > 1:
        names = ", ".join(f"--{flag.replace('_', '-')}" for flag in conflicting)
        sys.exit(
            f"{names} describes a single sweep set, but {len(targets)} are "
            f"selected ({', '.join(label(c) for c, _ in targets)}).\n"
            "Narrow it with --sets or --config."
        )

    runner = import_runner() if targets else None

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
            jobs=args.jobs,
            gif_workers=args.gif_workers,
            report_only=args.report_only,
            solve_only=args.solve_only,
            dry_run=args.dry_run,
            on_bad_solve=args.on_bad_solve,
        )

    print(f"Working  : {HERE}")
    if model is not None:
        print(f"model    : {model}")
    print(f"sweeps   : {', '.join(label(c) for c, _ in targets) or '(none)'}")
    print(f"forces   : {', '.join(c.parent.name for c in force_configs) or '(none)'}")
    for note in skipped:
        print(f"skipped  : {note}")
    if args.dry_run:
        print("dry run  : every configuration is validated, nothing is written")
    print()

    failed: list[str] = []

    for config, geometry in targets:
        name = label(config)
        print(f"==> {name} (sweeps)")
        try:
            runner.run_sweep_set(config, options(geometry))
        except runner.SweepSetError as error:
            failed.append(f"{name} (sweeps)")
            print(f"\n{error}", file=sys.stderr)
        except Exception:  # noqa: BLE001 - a bug here must not skip the rest
            failed.append(f"{name} (sweeps)")
            traceback.print_exc()
        print()

    for config in force_configs:
        name = config.parent.name
        print(f"==> {name} (forces)")
        cmd = force_command(config, args.dry_run)
        print("   $", " ".join(cmd), flush=True)
        if subprocess.run(cmd).returncode != 0:
            failed.append(f"{name} (forces)")
            print(f"   FAILED: {name} (forces)", file=sys.stderr)
        print()

    if failed:
        sys.exit(f"{len(failed)} stage(s) failed: {', '.join(failed)}")
    print(f"done. {len(targets) + len(force_configs)} stage(s) completed.")


if __name__ == "__main__":
    main()
