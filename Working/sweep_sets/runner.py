#!/usr/bin/env python3
"""
Solve one sweep set and build its report.

This is a LIBRARY, not a command. It used to be `run_all.py` with its own
argparse; there is now exactly one entry point for everything under Working/,
`Working/run_all.py`, and this module is what it calls for each sweep set.
The logic is unchanged - only the argument parsing moved.

    from runner import SweepOptions, run_sweep_set
    run_sweep_set(Path("Working/sweep_sets/front/run.yaml"), SweepOptions())

Everything that is not a hardpoint is configured in the `run.yaml` of the set
being run: which sweeps run, which characteristics each one reports, which get
plots, which get gifs, how many decimals, how many parallel jobs.
`SweepOptions` carries the command-line overrides for one invocation. See
RUNNING.md for the full key reference and CHARACTERISTICS.md for what the
channels mean.

Layout it assumes:
    Working/
      run_all.py         <- the one entry point
      sweep_sets/        <- this file, the reporters, and the sweep sets
        runner.py  susreport.py  susreport_rear.py  susreport_common.py
        bearings.py
        front/           <- a sweep set: run.yaml + sweeps/
        rear/            <- another one
      models/
        aurora/          <- a car: geometry files, and results per sweep set
          front.yaml  rear.yaml
          outputs/front/  outputs/rear/
          report/front/   report/rear/

A sweep set names itself and its default geometry, and results land beside
whatever geometry it is pointed at - so the same set runs against another car
without collisions or reconfiguration.

FAILURES RAISE `SweepSetError` rather than calling sys.exit. The caller runs
several sets and then the force solve in one process, and a bad `run.yaml` in
one set says nothing about the others - killing the interpreter would hide a
second, unrelated problem behind the first.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent  # Working/sweep_sets

# Where merged sweep files are written. run.yaml overrides the sweep YAMLs, so
# the file actually handed to the solver is a merge of the two. It is written
# out rather than passed in memory so its hash lands in the CSV provenance
# header and you can read exactly what was solved.
RESOLVED_DIRNAME = "_resolved_sweeps"


class SweepSetError(RuntimeError):
    """A sweep set could not be configured, solved, or reported.

    Carries a message already written for the reader: the caller prints it and
    moves on to the next stage rather than interpreting it.
    """


@dataclass(frozen=True)
class SweepOptions:
    """Command-line overrides for one invocation of one sweep set.

    Every field defaults to "do what run.yaml says". Precedence is these
    options > run.yaml > the sweep YAML.
    """

    geometry: Path | None = None
    sweeps_dir: Path | None = None
    side: str | None = None
    only: list[str] | None = None
    skip: list[str] = field(default_factory=list)
    plots: list[str] | None = None
    gifs: list[str] | None = None
    no_plots: bool = False
    no_gifs: bool = False
    no_joints: bool = False
    jobs: int | None = None
    report_only: bool = False
    solve_only: bool = False
    dry_run: bool = False
    on_bad_solve: str | None = None


# ==========================================================================
# Required configuration
#
# There are no default values in this file. run.yaml is the single source of
# truth, so a missing setting is an error naming the key rather than a silent
# fallback that makes the run disagree with the file you edited.
#
# This list covers only what this module itself reads. The report-side
# settings (decimals, solver, per-sweep channel lists) are validated by
# susreport when the resolved configuration reaches it - each half validates
# what it uses. `--dry-run` runs both validations, so it catches every kind of
# typo.
# ==========================================================================
REQUIRED_CONFIG = {
    "name": None,
    "geometry": None,
    "sweeps_dir": None,
    "reporter": None,
    "side": None,
    "jobs": None,
    "report": ("plots", "gifs"),
    "gif": ("fps",),
    "sweeps": None,
}

# Report modules a run.yaml may name. Each owns a suspension kind: the axle
# reporter's columns are side-suffixed and it carries track, roll, roll centre
# and Ackermann; the corner reporter's are unsuffixed and it does not.
REPORTERS = ("susreport", "susreport_rear")

# run.yaml keys that override a sweep YAML target, and how to find that target.
# (config key) -> predicate over one target mapping from the sweep file.
TARGET_MATCHERS = {
    ("travel", "left"): lambda t: (t.get("type") == "point"
                                   and t.get("point") == "wheel_center"
                                   and t.get("side") == "left"),
    ("travel", "right"): lambda t: (t.get("type") == "point"
                                    and t.get("point") == "wheel_center"
                                    and t.get("side") == "right"),
    ("damper", "left"): lambda t: (t.get("type") == "element_length"
                                   and t.get("element") == "damper"
                                   and t.get("side") == "left"),
    ("damper", "right"): lambda t: (t.get("type") == "element_length"
                                    and t.get("element") == "damper"
                                    and t.get("side") == "right"),
    ("rack", None): lambda t: (t.get("type") == "actuator_position"
                               and t.get("actuator") == "rack"),
    # Corner models drive one wheel and one damper, and their sweep targets
    # carry a `side:` only because the geometry declares one. The bare form
    # matches whichever side is there.
    ("travel", None): lambda t: (t.get("type") == "point"
                                 and t.get("point") == "wheel_center"),
    ("damper", None): lambda t: (t.get("type") == "element_length"
                                 and t.get("element") == "damper"),
}


# ==========================================================================
# Configuration
# ==========================================================================
def load_run_config(path: Path) -> dict:
    """Load and validate run.yaml. There is no implicit fallback."""
    if path is None or not Path(path).is_file():
        raise SweepSetError(
            f"run configuration not found: {path}\n"
            "There are no built-in defaults. Point --config at a run.yaml, or "
            "--sets at a folder under sweep_sets/; see RUNNING.md."
        )
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise SweepSetError(f"{path}: configuration must be a mapping")
    version = raw.get("version", 1)
    if version != 1:
        raise SweepSetError(
            f"{path}: unsupported run configuration version {version}"
        )

    missing: list[str] = []
    for key, children in REQUIRED_CONFIG.items():
        if key not in raw:
            missing.append(key)
            continue
        if children is None:
            continue
        if not isinstance(raw[key], dict):
            missing.append(f"{key} (must be a mapping)")
            continue
        missing += [f"{key}.{child}" for child in children
                    if child not in raw[key]]
    if missing:
        raise SweepSetError(
            f"{path}: missing required setting(s): {', '.join(missing)}.\n"
            "There are no built-in defaults - every setting must be present. "
            "See RUNNING.md for the key reference."
        )
    return copy.deepcopy(raw)


def load_reporter(name: str):
    """Import the report module this run.yaml names, and return its REPORTER.

    Imported lazily and by name rather than launched as a second process, so
    its tracebacks surface here and a breakpoint in the reporter is hit by an
    ordinary run. Lazy because it pulls in matplotlib and pandas, which a
    --solve-only run has no use for.
    """
    if name not in REPORTERS:
        raise SweepSetError(
            f"unknown reporter '{name}'. Known: {', '.join(REPORTERS)}"
        )
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import importlib

    import susreport_common
    module = importlib.import_module(name)
    return susreport_common, module.REPORTER


def resolve_jobs(value) -> int:
    """Turn the `jobs` setting into a worker count."""
    if isinstance(value, str) and value.strip().lower() == "auto":
        return max(1, min(8, os.cpu_count() or 1))
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def matches(selector: str, stem: str) -> bool:
    """`--only 01` matches `01_bump_parallel`; so does the full stem."""
    return stem == selector or stem.startswith(f"{selector}_")


# ==========================================================================
# Sweep resolution - run.yaml overriding the sweep YAML
# ==========================================================================
def resolve_sweep_file(source: Path, overrides: dict, outdir: Path) -> Path:
    """Merge run.yaml overrides into one sweep YAML and write the result.

    Precedence is run.yaml over the sweep file: any range or step count named
    in run.yaml replaces the sweep file's value, and anything run.yaml does not
    mention passes through untouched. Returns the path actually handed to the
    solver - the original file when nothing was overridden.
    """
    wanted = {key: overrides[key] for key in ("steps", "travel", "damper", "rack")
              if key in overrides and overrides[key] is not None}
    if not wanted:
        return source

    spec = yaml.safe_load(source.read_text()) or {}
    targets = spec.get("targets") or []

    if "steps" in wanted:
        spec["steps"] = int(wanted["steps"])

    for group in ("travel", "damper", "rack"):
        if group not in wanted:
            continue
        value = wanted[group]
        # {left: [...], right: [...]} on an axle; a bare [start, stop] on a
        # single corner, where there is only one wheel to drive.
        sides = value if isinstance(value, dict) else {None: value}
        for side, span in sides.items():
            key = (group, side if group != "rack" else None)
            matcher = TARGET_MATCHERS.get(key)
            if matcher is None:
                raise SweepSetError(
                    f"{source.name}: run.yaml key '{group}.{side}' is not a "
                    "recognised target"
                )
            found = [t for t in targets if matcher(t)]
            if not found:
                raise SweepSetError(
                    f"{source.name}: run.yaml sets '{group}"
                    f"{'.' + side if side else ''}' but that sweep file has no "
                    "matching target. Add the target to the sweep YAML, or drop "
                    "the override."
                )
            start, stop = _span(source, group, side, span)
            for target in found:
                target.pop("values", None)
                target["start"] = start
                target["stop"] = stop

    outdir.mkdir(parents=True, exist_ok=True)
    resolved = outdir / source.name
    header = (
        f"# GENERATED by Working/run_all.py from {source.name} + run.yaml.\n"
        "# Do not edit: it is overwritten on every run. Edit run.yaml (the\n"
        "# ranges) or the source sweep file (the target structure) instead.\n"
    )
    resolved.write_text(header + yaml.safe_dump(spec, sort_keys=False))
    return resolved


def _span(source: Path, group: str, side, span) -> tuple[float, float]:
    """Validate a [start, stop] pair from run.yaml."""
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        raise SweepSetError(
            f"{source.name}: '{group}{'.' + side if side else ''}' must be "
            f"[start, stop], got {span!r}"
        )
    try:
        return float(span[0]), float(span[1])
    except (TypeError, ValueError):
        raise SweepSetError(
            f"{source.name}: '{group}{'.' + side if side else ''}' values "
            f"must be numbers, got {span!r}"
        ) from None


# ==========================================================================
# Execution
# ==========================================================================
def run(cmd: list[str]) -> None:
    print("   $", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SweepSetError(f"command failed: {' '.join(cmd)}")


def solve_one(job: dict) -> tuple[str, int, str]:
    """Solve one sweep in a subprocess. Returns (name, returncode, output)."""
    result = subprocess.run(job["cmd"], capture_output=True, text=True)
    return job["name"], result.returncode, (result.stdout or "") + (result.stderr or "")


def _failure_reason(output: str) -> str:
    """Pull the headline out of a subprocess traceback.

    A solver failure prints a full traceback, whose last non-empty line is the
    exception and its message. That line is what the reader needs first.
    """
    lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
    if not lines:
        return "no output"
    for line in reversed(lines):
        if ": " in line and not line.startswith(("File ", "  ")):
            return line
    return lines[-1]


def truthy(value, default: bool) -> bool:
    """Interpret a run.yaml on/off value."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "yes", "on", "all"):
        return True
    if text in ("false", "no", "off", "none"):
        return False
    return default


def master_override(value) -> bool | None:
    """`report.plots` / `report.gifs`: auto -> None, else a hard on/off."""
    text = str(value).strip().lower()
    if text in ("auto", "", "none_specified"):
        return None
    if text in ("true", "yes", "on", "all"):
        return True
    if text in ("false", "no", "off", "none"):
        return False
    return None


# ==========================================================================
# The one entry point
# ==========================================================================
def run_sweep_set(config_path: Path, opts: SweepOptions | None = None) -> None:
    """Solve one sweep set and build its report.

    Raises SweepSetError with a reader-ready message on any failure.
    """
    opts = opts or SweepOptions()
    config_path = Path(config_path)
    config = load_run_config(config_path)

    # ---- CLI over run.yaml -------------------------------------------
    if opts.geometry:
        config["geometry"] = str(opts.geometry)
    if opts.side:
        config["side"] = opts.side
    if opts.jobs is not None:
        config["jobs"] = opts.jobs
    if opts.no_joints:
        config["report"]["joints"] = False
    if opts.no_plots:
        config["report"]["plots"] = False
    if opts.no_gifs:
        config["report"]["gifs"] = False
    if opts.on_bad_solve:
        config.setdefault("solver", {})["on_bad_solve"] = opts.on_bad_solve

    # Paths in run.yaml are relative to run.yaml itself, so a sweep set can be
    # moved or copied without rewriting them.
    config_dir = config_path.resolve().parent
    geometry = Path(config["geometry"])
    if not geometry.is_absolute():
        geometry = (config_dir / geometry).resolve()
    sweeps_dir = opts.sweeps_dir
    if sweeps_dir is None:
        sweeps_dir = Path(config["sweeps_dir"])
        if not sweeps_dir.is_absolute():
            sweeps_dir = (config_dir / sweeps_dir).resolve()

    if not geometry.is_file():
        raise SweepSetError(f"geometry not found: {geometry}")

    # Results live beside the geometry, in a folder named after the sweep set.
    # That is what lets one sweep set run against several cars.
    set_name = str(config["name"])
    outputs = geometry.parent / "outputs" / set_name
    report = geometry.parent / "report" / set_name
    outputs.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True, exist_ok=True)

    sources = sorted(Path(sweeps_dir).glob("*.yaml"))
    if not sources:
        raise SweepSetError(f"no sweeps in {sweeps_dir}")

    only = opts.only
    skip = opts.skip or []
    plot_only = opts.plots
    gif_only = opts.gifs
    gifs_master = master_override(config["report"]["gifs"])

    # ---- decide what runs --------------------------------------------
    # Every sweep file must have an entry in run.yaml. A file with no entry is
    # an error rather than an implicit "run it": a sweep silently joining the
    # set would also silently raise a bearing requirement.
    configured = config["sweeps"] or {}
    unconfigured = [s.stem for s in sources if s.stem not in configured]
    if unconfigured:
        raise SweepSetError(
            f"{config_path}: no entry under `sweeps:` for "
            f"{', '.join(unconfigured)}.\n"
            "Every file in the sweeps directory needs one, even if it is just "
            "`run: false`. See RUNNING.md."
        )

    plan: list[dict] = []
    for source in sources:
        stem = source.stem
        sweep_cfg = configured[stem]

        enabled = truthy(sweep_cfg["run"], True)
        if only is not None:
            enabled = any(matches(s, stem) for s in only)
        if any(matches(s, stem) for s in skip):
            enabled = False
        if not enabled:
            continue

        # `gif` is optional per sweep: absent means no animation, which is
        # the only setting whose absence is unambiguous.
        wants_gif = truthy(sweep_cfg.get("gif"), False)
        if isinstance(sweep_cfg.get("gif"), dict):
            wants_gif = truthy(sweep_cfg["gif"].get("enabled"), True)
        if gifs_master is not None:
            wants_gif = gifs_master
        if gif_only is not None:
            wants_gif = any(matches(s, stem) for s in gif_only)

        plan.append({
            "name": stem,
            "source": source,
            "cfg": sweep_cfg,
            "gif": wants_gif,
        })

    if not plan:
        raise SweepSetError(
            f"{set_name}: nothing to run - every sweep is disabled or filtered "
            "out. A selector such as --only applies to every set being run; "
            "use --sets or --config to narrow which sets those are."
        )

    # `--plots a,b` is a whitelist: it forces plots off everywhere else.
    if plot_only is not None:
        for item in plan:
            keep = any(matches(s, item["name"]) for s in plot_only)
            config.setdefault("sweeps", {}).setdefault(item["name"], {})
            config["sweeps"][item["name"]]["plots"] = "all" if keep else "none"

    jobs = resolve_jobs(config["jobs"])

    print(f"sweep set: {set_name}  ({config['reporter']})")
    print(f"geometry : {geometry}")
    print(f"sweeps   : {sweeps_dir}  ({len(plan)} of {len(sources)} enabled)")
    print(f"outputs  : {outputs}")
    print(f"report   : {report}")
    print(f"jobs     : {jobs}\n")

    # ---- the resolved configuration -----------------------------------
    # run.yaml after the command-line overrides: what susreport reads, and the
    # record of what actually ran. Written before solving so a --dry-run can
    # validate the report-side settings too, and so a crashed solve still
    # leaves the configuration that produced it.
    resolved_config = {
        key: config[key] for key in
        ("name", "reporter", "side", "decimals", "report", "solver", "gif")
        if key in config
    }
    resolved_config.update({
        "sweeps": {i["name"]: i["cfg"] for i in plan},
        "ran": [i["name"] for i in plan],
        "geometry": str(geometry),
        "source_config": str(config_path),
    })
    resolved_path = report / "_resolved_run.json"
    resolved_path.write_text(json.dumps(resolved_config, indent=2, default=str))

    # Validate the half of the configuration susreport owns, before spending
    # any CPU. This is also what makes --dry-run a complete config check.
    common = reporter = None
    report_config = None
    if not opts.solve_only:
        common, reporter = load_reporter(str(config["reporter"]))
        report_config = common.load_config(None, resolved_path)

    # ---- solve --------------------------------------------------------
    if not opts.report_only:
        resolved_dir = outputs / RESOLVED_DIRNAME
        queue = []
        for item in plan:
            sweep_file = resolve_sweep_file(item["source"], item["cfg"], resolved_dir)
            item["resolved"] = sweep_file
            queue.append({
                "name": item["name"],
                "cmd": ["uv", "run", "kinematics", "sweep",
                        "--geometry", str(geometry),
                        "--sweep", str(sweep_file),
                        "--out", str(outputs / f"{item['name']}.csv")],
            })

        if opts.dry_run:
            print(f"-> would solve {len(queue)} sweep(s) on {jobs} worker(s)")
            for job in queue:
                print("   $", " ".join(job["cmd"]))
            for item in plan:
                if item["gif"]:
                    print(f"   gif: {item['name']}")
            print(f"\n   merged sweep files in {resolved_dir}")
            print(f"   resolved configuration  {resolved_path}")
            if reporter is not None:
                print(f"   configuration validated "
                      f"(runner and {config['reporter']})")
            print("   (dry run: nothing solved, no report written)")
            return

        print(f"-> solving {len(queue)} sweep(s) on {jobs} worker(s)")
        failures = []
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            for name, code, output in pool.map(solve_one, queue):
                status = "ok" if code == 0 else "FAILED"
                print(f"   {name:26s} {status}")
                if code != 0:
                    failures.append((name, output))
        if failures:
            # Every sweep loads the same geometry, so a geometry or
            # configuration fault fails all of them with one message. Say that
            # once rather than making the reader diff N identical tracebacks.
            reasons = {_failure_reason(output) for _name, output in failures}
            if len(reasons) == 1 and len(failures) > 1:
                reason = reasons.pop()
                print(f"\n--- all {len(failures)} sweeps failed identically ---",
                      file=sys.stderr)
                print(f"{reason}\n", file=sys.stderr)
                print("Every sweep loads the same geometry, so this is almost "
                      "certainly the geometry file or run.yaml, not the "
                      "sweeps.", file=sys.stderr)
                print(f"\nFull output from {failures[0][0]}:\n{failures[0][1]}",
                      file=sys.stderr)
            else:
                for name, output in failures:
                    print(f"\n--- {name} ---\n{output}", file=sys.stderr)
                    print(f"  reason: {_failure_reason(output)}", file=sys.stderr)
            raise SweepSetError(
                f"{set_name}: {len(failures)} sweep(s) failed to solve"
            )

        # ---- animations, serially ------------------------------------
        # The animation writer holds every frame in memory, so several at once
        # thrash rather than go faster. This stays serial whatever --jobs says.
        gif_items = [i for i in plan if i["gif"]]
        for item in gif_items:
            print(f"\n-> animation ({item['name']})")
            cmd = ["uv", "run", "kinematics", "sweep",
                   "--geometry", str(geometry),
                   "--sweep", str(item["resolved"]),
                   "--out", str(outputs / f"{item['name']}.csv"),
                   "--animation-out", str(outputs / f"{item['name']}.gif")]
            run(cmd)

    if opts.solve_only:
        print("\ndone (solve only).")
        return

    # ---- report -------------------------------------------------------
    # Only report on the sweeps that actually ran this time. Stale CSVs from a
    # disabled sweep stay on disk but must not silently reappear in the report
    # or, worse, in the bearing table.
    stale = [p for p in sorted(outputs.glob("*.csv"))
             if p.stem not in {i["name"] for i in plan}]
    if stale:
        print("\n   note: ignoring CSVs from sweeps that are not enabled: "
              + ", ".join(p.stem for p in stale))

    print("\n-> report")
    common.run_report(outputs, report, report_config, reporter)

    print(f"\ndone. report at {report}")
