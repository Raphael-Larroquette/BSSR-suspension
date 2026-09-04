#!/usr/bin/env python3
"""
Run the configured sweep set and build the report. Cross-platform (works in
PowerShell, cmd, bash) and independent of your current working directory.

Everything that is not a hardpoint is configured in `run.yaml` next to this
file: which sweeps run, which characteristics each one reports, which get
plots, which get gifs, how many decimals, how many parallel jobs. Command-line
flags override run.yaml for one invocation. See RUNNING.md for the full key
reference and CHARACTERISTICS.md for what the channels mean.

Layout it assumes:
    models/
      aurora/            <- geometry, outputs, report
        front.yaml
        outputs/
        report/
      Sweep_Set/         <- this file
        run.yaml
        sweeps/
        susreport.py

Usage:
    uv run python models/Sweep_Set/run_all.py
    uv run python models/Sweep_Set/run_all.py --only 01,02,09
    uv run python models/Sweep_Set/run_all.py --report-only
    uv run python models/Sweep_Set/run_all.py --geometry models/aurora/rear.yaml
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent          # models/Sweep_Set
MODELS = HERE.parent                            # models
SWEEPS = HERE / "sweeps"
SUSREPORT = HERE / "susreport.py"
RUN_YAML = HERE / "run.yaml"

# Where merged sweep files are written. run.yaml overrides the sweep YAMLs, so
# the file actually handed to the solver is a merge of the two. It is written
# out rather than passed in memory so its hash lands in the CSV provenance
# header and you can read exactly what was solved.
RESOLVED_DIRNAME = "_resolved_sweeps"


# ==========================================================================
# Defaults - used when run.yaml is absent or silent on a key
# ==========================================================================
DEFAULTS: dict = {
    "model": "aurora",
    "geometry": None,
    "side": "left",
    "jobs": "auto",
    "decimals": {"mm": 3, "deg": 4, "ratio": 4, "percent": 2},
    "report": {"joints": True, "notes": True, "plots": "auto", "gifs": "auto"},
    "solver": {"on_bad_solve": "warn", "residual_limit": 1.0e-5},
    "gif": {"fps": 20, "overlays": ["fvic", "fvsa", "roll_center"],
            "overlay_frame": 3.0},
    "sweeps": {},
}

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
}


# ==========================================================================
# Configuration
# ==========================================================================
def deep_merge(base: dict, over: dict) -> dict:
    """Recursively merge `over` into a copy of `base`."""
    out = copy.deepcopy(base)
    for key, value in (over or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_run_config(path: Path | None) -> dict:
    """Load run.yaml over the built-in defaults."""
    config = copy.deepcopy(DEFAULTS)
    if path is None or not path.is_file():
        return config
    raw = yaml.safe_load(path.read_text()) or {}
    version = raw.get("version", 1)
    if version != 1:
        sys.exit(f"{path}: unsupported run configuration version {version}")
    return deep_merge(config, raw)


def resolve_jobs(value) -> int:
    """Turn the `jobs` setting into a worker count."""
    if isinstance(value, str) and value.strip().lower() == "auto":
        return max(1, min(8, os.cpu_count() or 1))
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def parse_list(value: str | None) -> list[str] | None:
    """Split a comma-separated CLI list, tolerating spaces."""
    if value is None:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


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
        sides = value if isinstance(value, dict) else {None: value}
        for side, span in sides.items():
            key = (group, side if group != "rack" else None)
            matcher = TARGET_MATCHERS.get(key)
            if matcher is None:
                sys.exit(f"{source.name}: run.yaml key '{group}.{side}' is not a "
                         "recognised target")
            found = [t for t in targets if matcher(t)]
            if not found:
                sys.exit(
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
        f"# GENERATED by run_all.py from {source.name} + run.yaml.\n"
        "# Do not edit: it is overwritten on every run. Edit run.yaml (the\n"
        "# ranges) or the source sweep file (the target structure) instead.\n"
    )
    resolved.write_text(header + yaml.safe_dump(spec, sort_keys=False))
    return resolved


def _span(source: Path, group: str, side, span) -> tuple[float, float]:
    """Validate a [start, stop] pair from run.yaml."""
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        sys.exit(f"{source.name}: '{group}{'.' + side if side else ''}' must be "
                 f"[start, stop], got {span!r}")
    try:
        return float(span[0]), float(span[1])
    except (TypeError, ValueError):
        sys.exit(f"{source.name}: '{group}{'.' + side if side else ''}' values "
                 f"must be numbers, got {span!r}")


# ==========================================================================
# Execution
# ==========================================================================
def run(cmd: list[str], quiet: bool = False) -> None:
    if not quiet:
        print("   $", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}")


def solve_one(job: dict) -> tuple[str, int, str]:
    """Solve one sweep in a subprocess. Returns (name, returncode, output)."""
    result = subprocess.run(job["cmd"], capture_output=True, text=True)
    return job["name"], result.returncode, (result.stdout or "") + (result.stderr or "")


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
# Entry point
# ==========================================================================
def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Every flag below overrides run.yaml for this invocation only. "
               "Precedence: CLI > run.yaml > sweep YAML > built-in defaults.",
    )
    ap.add_argument("--config", type=Path, default=RUN_YAML,
                    help="run configuration file "
                         "(default: run.yaml beside this script)")
    ap.add_argument("--model", default=None,
                    help="folder under models/ holding the geometry")
    ap.add_argument("--geometry", type=Path, default=None,
                    help="explicit path to the geometry yaml, overrides --model")
    ap.add_argument("--sweeps-dir", type=Path, default=None,
                    help="alternative directory of sweep YAMLs")
    ap.add_argument("--side", default=None, choices=("left", "right"),
                    help="which corner the per-corner rows report")
    ap.add_argument("--only", default=None,
                    help="comma-separated sweeps to run, e.g. --only 01,02,09")
    ap.add_argument("--skip", default=None,
                    help="comma-separated sweeps to leave out")
    ap.add_argument("--plots", default=None,
                    help="comma-separated sweeps that get a figure; others get none")
    ap.add_argument("--gifs", default=None,
                    help="comma-separated sweeps that get an animation")
    ap.add_argument("--no-plots", action="store_true", help="no figures at all")
    ap.add_argument("--no-gifs", action="store_true", help="no animations at all")
    ap.add_argument("--no-joints", action="store_true",
                    help="drop the bearing misalignment section")
    ap.add_argument("--gif-overlays", default=None,
                    help="comma-separated overlays, e.g. fvic,fvsa,roll_center "
                         "(use 'none' for a clean render)")
    ap.add_argument("--jobs", type=int, default=None,
                    help="parallel solver processes (default: run.yaml `jobs`)")
    ap.add_argument("--report-only", action="store_true",
                    help="rebuild the report from the CSVs already in outputs/")
    ap.add_argument("--solve-only", action="store_true",
                    help="solve the sweeps and stop, no report")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve the configuration, write the merged sweep "
                         "files and print the commands, but solve nothing")
    ap.add_argument("--on-bad-solve", default=None,
                    choices=("off", "warn", "fail"),
                    help="what to do about non-converged or high-residual steps")
    args = ap.parse_args()

    config = load_run_config(args.config)

    # ---- CLI over run.yaml -------------------------------------------
    if args.model:
        config["model"] = args.model
    if args.geometry:
        config["geometry"] = str(args.geometry)
    if args.side:
        config["side"] = args.side
    if args.jobs is not None:
        config["jobs"] = args.jobs
    if args.no_joints:
        config["report"]["joints"] = False
    if args.no_plots:
        config["report"]["plots"] = False
    if args.no_gifs:
        config["report"]["gifs"] = False
    if args.on_bad_solve:
        config["solver"]["on_bad_solve"] = args.on_bad_solve
    if args.gif_overlays is not None:
        overlays = parse_list(args.gif_overlays) or []
        config["gif"]["overlays"] = [] if overlays == ["none"] else overlays

    model_dir = MODELS / config["model"]
    geometry = (Path(config["geometry"]).resolve() if config.get("geometry")
                else model_dir / "front.yaml")
    sweeps_dir = args.sweeps_dir or SWEEPS
    outputs = model_dir / "outputs"
    report = model_dir / "report"

    if not geometry.is_file():
        sys.exit(f"geometry not found: {geometry}")
    outputs.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True, exist_ok=True)

    sources = sorted(sweeps_dir.glob("*.yaml"))
    if not sources:
        sys.exit(f"no sweeps in {sweeps_dir}")

    only = parse_list(args.only)
    skip = parse_list(args.skip) or []
    plot_only = parse_list(args.plots)
    gif_only = parse_list(args.gifs)
    plots_master = master_override(config["report"].get("plots", "auto"))
    gifs_master = master_override(config["report"].get("gifs", "auto"))

    # ---- decide what runs --------------------------------------------
    plan: list[dict] = []
    for source in sources:
        stem = source.stem
        sweep_cfg = (config.get("sweeps") or {}).get(stem) or {}

        enabled = truthy(sweep_cfg.get("run"), True)
        if only is not None:
            enabled = any(matches(s, stem) for s in only)
        if any(matches(s, stem) for s in skip):
            enabled = False
        if not enabled:
            continue

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
        sys.exit("nothing to run: every sweep is disabled or filtered out")

    # `--plots a,b` is a whitelist: it forces plots off everywhere else.
    if plot_only is not None:
        for item in plan:
            keep = any(matches(s, item["name"]) for s in plot_only)
            config.setdefault("sweeps", {}).setdefault(item["name"], {})
            config["sweeps"][item["name"]]["plots"] = "all" if keep else "none"

    jobs = resolve_jobs(config.get("jobs", "auto"))

    print(f"geometry : {geometry}")
    print(f"sweeps   : {sweeps_dir}  ({len(plan)} of {len(sources)} enabled)")
    print(f"outputs  : {outputs}")
    print(f"report   : {report}")
    print(f"jobs     : {jobs}\n")

    # ---- solve --------------------------------------------------------
    if not args.report_only:
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

        if args.dry_run:
            print(f"-> would solve {len(queue)} sweep(s) on {jobs} worker(s)")
            for job in queue:
                print("   $", " ".join(job["cmd"]))
            for item in plan:
                if item["gif"]:
                    print(f"   gif: {item['name']} "
                          f"overlays={config['gif'].get('overlays')}")
            print(f"\n   merged sweep files in {resolved_dir}")
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
            for name, output in failures:
                print(f"\n--- {name} ---\n{output}", file=sys.stderr)
            sys.exit(f"{len(failures)} sweep(s) failed to solve")

        # ---- animations, serially ------------------------------------
        # The animation writer holds every frame in memory, so several at once
        # thrash rather than go faster. This stays serial whatever --jobs says.
        gif_items = [i for i in plan if i["gif"]]
        overlays = [str(o) for o in (config["gif"].get("overlays") or [])]
        for item in gif_items:
            print(f"\n-> animation ({item['name']})")
            cmd = ["uv", "run", "kinematics", "sweep",
                   "--geometry", str(geometry),
                   "--sweep", str(item["resolved"]),
                   "--out", str(outputs / f"{item['name']}.csv"),
                   "--animation-out", str(outputs / f"{item['name']}.gif")]
            if overlays:
                cmd += ["--animation-overlays", ",".join(overlays)]
            frame = config["gif"].get("overlay_frame")
            if frame:
                cmd += ["--animation-overlay-frame", str(frame)]
            fps = config["gif"].get("fps")
            if fps:
                cmd += ["--animation-fps", str(fps)]
            run(cmd)

    if args.solve_only:
        print("\ndone (solve only).")
        return

    # ---- report -------------------------------------------------------
    # Write the fully resolved configuration next to the report. This is both
    # what susreport reads and the record of what actually ran.
    resolved_config = {
        "side": config["side"],
        "decimals": config["decimals"],
        "report": config["report"],
        "solver": config["solver"],
        "gif": config["gif"],
        "sweeps": {i["name"]: i["cfg"] for i in plan},
        "ran": [i["name"] for i in plan],
        "geometry": str(geometry),
        "source_config": str(args.config) if args.config.is_file() else None,
    }
    resolved_path = report / "_resolved_run.json"
    resolved_path.write_text(json.dumps(resolved_config, indent=2, default=str))

    # Only report on the sweeps that actually ran this time. Stale CSVs from a
    # disabled sweep stay on disk but must not silently reappear in the report
    # or, worse, in the bearing table.
    stale = [p for p in sorted(outputs.glob("*.csv"))
             if p.stem not in {i["name"] for i in plan}]
    if stale:
        print("\n   note: ignoring CSVs from sweeps that are not enabled: "
              + ", ".join(p.stem for p in stale))

    print("\n-> report")
    cmd = ["uv", "run", "python", str(SUSREPORT), str(outputs),
           "--out", str(report), "--resolved", str(resolved_path),
           "--side", config["side"]]
    run(cmd)

    print(f"\ndone. report at {report}")


if __name__ == "__main__":
    main()
