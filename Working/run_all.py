#!/usr/bin/env python3
"""
The entry point for everything under Working/: the kinematic sweep sets, then
the static force solve. Cross-platform, and independent of your current
working directory.

    uv run python Working/run_all.py                     everything
    uv run python Working/run_all.py --sets front        one sweep set, + forces
    uv run python Working/run_all.py --no-forces         sweeps only
    uv run python Working/run_all.py --no-sweeps         forces only

    sweep_sets/*/run.yaml     -> sweep_sets/runner.run_sweep_set(), in process
    forces/*/forces.yaml      -> `kinematics forces --config ...`

THIS IS THE ONLY COMMAND; `sweep_sets/runner.py` is a library this file calls.
A sweep set is chosen with --sets (folder name) or --config (path); every other
flag narrows what runs inside the sets chosen. Both lists are DISCOVERED, so
adding a sweep set or a car's force configuration is a new folder and nothing else.

Forces are in the same command, and on by default, because a sweep set and a
force configuration read the SAME geometry: a hardpoint edit invalidates both.
Sweeps run first because the force solve is seconds and cheap to re-run alone.

Stages run independently: every stage is attempted, and the exit code names
everything that failed.

See the repository README.md for the workflow, sweep_sets/RUNNING.md for the
run.yaml keys, and forces/force.md for the force solve.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent  # Working/
SWEEP_SETS_DIR = HERE / "sweep_sets"
FORCES_DIR = HERE / "forces"

# A sweep set is a folder with a run.yaml; a car's force configuration is a
# folder with a forces.yaml.
SWEEP_SET_GLOB = "*/run.yaml"
FORCES_GLOB = "*/forces.yaml"

# Overrides that describe ONE set and cannot mean anything across several.
PER_SET_FLAGS = ("geometry", "side")


# ==========================================================================
# Discovery
# ==========================================================================
def discover_sweep_sets() -> list[Path]:
    """Return every sweep set's run.yaml, in folder-name order."""
    return sorted(SWEEP_SETS_DIR.glob(SWEEP_SET_GLOB))


def discover_force_configs() -> list[Path]:
    """Return every car's forces.yaml, in folder-name order."""
    return sorted(FORCES_DIR.glob(FORCES_GLOB))


def label(config: Path) -> str:
    """Name a run by its folder, which is what --sets / --cars match."""
    return config.parent.name


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
    """Build the command for one car's force solve.

    A subprocess, unlike the sweep sets, because `kinematics forces` is an
    installed console script with its own diagnostics and exit codes. Running
    it here is the same command force.md documents.
    """
    cmd = ["uv", "run", "kinematics", "forces", "--config", str(config)]
    if dry_run:
        # The force CLI's own --dry-run validates every input and solves
        # without writing, so forwarding it keeps --dry-run a complete check.
        cmd.append("--dry-run")
    return cmd


# ==========================================================================
# Entry point
# ==========================================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="Working/run_all.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="These flags override run.yaml for this invocation only; "
        "run.yaml is the only other place anything is configured. "
        "See RUNNING.md for its key reference.",
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
        "--cars",
        default=None,
        help="comma-separated force configurations, by folder name under "
        "forces/ (default: all of them)",
    )
    what.add_argument(
        "--forces-config",
        type=Path,
        default=None,
        help="solve one force configuration by path to its forces.yaml. "
        "Mutually exclusive with --cars",
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
        help="run the set against a different car (one set at a time)",
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
        "--jobs", type=int, default=None, help="parallel solver processes"
    )
    sweeps.add_argument(
        "--report-only",
        action="store_true",
        help="rebuild the reports from the CSVs already in outputs/, solving nothing",
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
        help="print the sweep sets and force configurations found, then stop",
    )
    other.add_argument(
        "--dry-run",
        action="store_true",
        help="validate every configuration and print every command, but solve "
        "nothing and write no results. A complete check of Working/",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        print("sweep sets:")
        for config in discover_sweep_sets():
            print(f"   {label(config):10s} {config}")
        print("force configurations:")
        for config in discover_force_configs():
            print(f"   {label(config):10s} {config}")
        return

    if args.config and args.sets:
        parser.error(
            "--config names one sweep set by path and --sets names them by "
            "folder; use one or the other"
        )
    if args.forces_config and args.cars:
        parser.error("use --forces-config or --cars, not both")
    if args.report_only and args.solve_only:
        parser.error("--report-only and --solve-only are opposites")

    # ---- which sweep sets --------------------------------------------
    if args.config:
        if not args.config.is_file():
            sys.exit(f"run configuration not found: {args.config}")
        sweep_sets = [args.config]
    else:
        sweep_sets = select(
            discover_sweep_sets(), parse_list(args.sets), "sweep set"
        )

    # ---- which force configurations ----------------------------------
    if args.forces_config:
        if not args.forces_config.is_file():
            sys.exit(f"force configuration not found: {args.forces_config}")
        force_configs = [args.forces_config]
    else:
        force_configs = select(
            discover_force_configs(), parse_list(args.cars), "force configuration"
        )

    if args.no_sweeps:
        sweep_sets = []
    if args.no_forces:
        force_configs = []

    if not sweep_sets and not force_configs:
        sys.exit(
            "nothing to run. --no-sweeps and --no-forces together leave no "
            "work; otherwise nothing was discovered under sweep_sets/ or "
            "forces/."
        )

    # These each describe one set; applying them to several would run every
    # set against the same car, into the same output folder.
    conflicting = [
        flag for flag in PER_SET_FLAGS if getattr(args, flag, None) is not None
    ]
    if conflicting and len(sweep_sets) > 1:
        names = ", ".join(f"--{flag.replace('_', '-')}" for flag in conflicting)
        sys.exit(
            f"{names} describes a single sweep set, but {len(sweep_sets)} are "
            f"selected ({', '.join(label(c) for c in sweep_sets)}).\n"
            "Narrow it with --sets or --config."
        )

    runner = import_runner() if sweep_sets else None
    options = None
    if runner is not None:
        options = runner.SweepOptions(
            geometry=args.geometry,
            side=args.side,
            only=parse_list(args.only),
            skip=parse_list(args.skip) or [],
            plots=parse_list(args.plots),
            gifs=parse_list(args.gifs),
            no_plots=args.no_plots,
            no_gifs=args.no_gifs,
            no_joints=args.no_joints,
            jobs=args.jobs,
            report_only=args.report_only,
            solve_only=args.solve_only,
            dry_run=args.dry_run,
            on_bad_solve=args.on_bad_solve,
        )

    print(f"Working  : {HERE}")
    print(f"sweeps   : {', '.join(label(c) for c in sweep_sets) or '(skipped)'}")
    print(f"forces   : {', '.join(label(c) for c in force_configs) or '(skipped)'}")
    if args.dry_run:
        print("dry run  : every configuration is validated, nothing is written")
    print()

    failed: list[str] = []

    for config in sweep_sets:
        name = label(config)
        print(f"==> {name} (sweeps)")
        try:
            runner.run_sweep_set(config, options)
        except runner.SweepSetError as error:
            failed.append(f"{name} (sweeps)")
            print(f"\n{error}", file=sys.stderr)
        except Exception:  # noqa: BLE001 - a bug here must not skip the rest
            failed.append(f"{name} (sweeps)")
            traceback.print_exc()
        print()

    for config in force_configs:
        name = label(config)
        print(f"==> {name} (forces)")
        cmd = force_command(config, args.dry_run)
        print("   $", " ".join(cmd), flush=True)
        if subprocess.run(cmd).returncode != 0:
            failed.append(f"{name} (forces)")
            print(f"   FAILED: {name} (forces)", file=sys.stderr)
        print()

    if failed:
        sys.exit(f"{len(failed)} stage(s) failed: {', '.join(failed)}")
    print(f"done. {len(sweep_sets) + len(force_configs)} stage(s) completed.")


if __name__ == "__main__":
    main()
