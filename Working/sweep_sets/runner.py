#!/usr/bin/env python3
"""
Plan one sweep set and build its report.

This is a LIBRARY, not a command. `Working/run_all.py` is the one entry point:
it calls `plan_sweep_set` for every (model, set), hands the solves, reports and
animations to a single process pool (scheduler.py, tasks.py), and pool workers
call `build_report` here once a set's solves are done.

    from runner import SweepOptions, plan_sweep_set
    plan = plan_sweep_set(Path("Working/sweep_sets/front/run.yaml"), SweepOptions())

Everything that is not a hardpoint is configured in the `run.yaml` of the set
being run: which sweeps run, WHAT EACH ONE DRIVES, which characteristics it
reports, which get plots, which get animations, how many decimals.
`SweepOptions` carries the command-line overrides for one invocation. See
docs/reference/sweeps.md for the full key reference and docs/reference/characteristics.md for what the
channels mean.

SWEEP FILES ARE GENERATED, not authored. A sweep's targets are built from its
`travel` / `damper` / `rack` keys and written to sweep_outputs/<set>/_resolved_sweeps/,
so a range exists in exactly one place. A sweep the vocabulary cannot express is
written as an ordinary sweep YAML and named with `file:`; it is then used
verbatim, never merged, so that stays one place too.

Layout it assumes:
    Working/
      run_all.py         <- the one entry point
      sweep_sets/        <- this file, the reporters, and the sweep sets
        runner.py  scheduler.py  tasks.py
        susreport.py  susreport_rear.py  susreport_common.py  bearings.py
        front/           <- a sweep set: run.yaml, and nothing else it needs
        rear/            <- another one
      models/
        aurora/          <- a car: geometry, force config, and results
          front.yaml  rear.yaml  forces.yaml  cases.csv
          sweep_outputs/front/  sweep_outputs/rear/   (git-ignored)
          report/front/         report/rear/          (git-ignored)
          forces/                                     (git-ignored)

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
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent  # Working/sweep_sets

# Where generated sweep files are written. The solver takes a file, and writing
# it out rather than passing it in memory puts its hash in the CSV provenance
# header, so you can read exactly what was solved. Everything solved lands here,
# generated or copied from a `file:`, so this directory is the complete record.
RESOLVED_DIRNAME = "_resolved_sweeps"

# Positions per solved step, kept for the animation task (a few kB each).
FRAMES_DIRNAME = "_frames"

# Animation formats the renderer writes (`gif: {format: ...}` in run.yaml).
ANIMATION_FORMATS = ("gif", "mp4")

# The two result folders a sweep set writes beside the geometry it ran. Both are
# git-ignored (see .gitignore) because everything in them regenerates.
SWEEP_OUTPUTS_DIRNAME = "sweep_outputs"
REPORT_DIRNAME = "report"


class SweepSetError(RuntimeError):
    """A sweep set could not be configured, solved, or reported.

    Carries a message already written for the reader: the caller prints it and
    moves on to the next stage rather than interpreting it.
    """


@dataclass(frozen=True)
class SweepOptions:
    """Command-line overrides for one invocation of one sweep set.

    Every field defaults to "do what run.yaml says". Precedence is these
    options > run.yaml, which is the only other place anything is said.
    """

    geometry: Path | None = None
    side: str | None = None
    only: list[str] | None = None
    skip: list[str] = field(default_factory=list)
    plots: list[str] | None = None
    gifs: list[str] | None = None
    no_plots: bool = False
    no_gifs: bool = False
    no_joints: bool = False
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
    "reporter": None,
    "side": None,
    "report": ("plots", "gifs"),
    "gif": ("fps", "dpi"),
    "sweeps": None,
}

# Report modules a run.yaml may name. Each owns a suspension kind: the axle
# reporter's columns are side-suffixed and it carries track, roll, roll centre
# and Ackermann; the corner reporter's are unsuffixed and it does not.
REPORTERS = ("susreport", "susreport_rear")

# ==========================================================================
# The drive vocabulary
#
# These are the run.yaml keys a generated sweep is built from, and the target
# each one produces. A corner has ONE degree of freedom, so it is driven by
# exactly one of `travel` or `damper`; every actuator the geometry declares
# needs its own key.
#
# Extending this table is what a new drive coordinate costs. Anything it cannot
# express - `mode: absolute`, an explicit `values:` list, a point driven along a
# non-principal direction - is written as an ordinary sweep YAML and named with
# `file:` instead. See docs/reference/sweeps.md.
# ==========================================================================
CORNER_GROUPS = ("travel", "damper")
ACTUATOR_GROUPS = ("rack",)
RANGE_GROUPS = CORNER_GROUPS + ACTUATOR_GROUPS


def _travel_target(side: str, start: float, stop: float) -> dict:
    """Drive a corner by wheel-centre height."""
    return {"type": "point", "point": "wheel_center", "side": side,
            "direction": {"axis": "z"}, "mode": "relative",
            "start": start, "stop": stop}


def _damper_target(side: str, start: float, stop: float) -> dict:
    """Drive a corner by damper length. A length is scalar - no direction."""
    return {"type": "element_length", "element": "damper", "side": side,
            "mode": "relative", "start": start, "stop": stop}


def _rack_target(_side, start: float, stop: float) -> dict:
    """Drive the shared steering rack. One lateral DOF, so no side."""
    return {"type": "actuator_position", "actuator": "rack",
            "direction": {"axis": "y"}, "mode": "relative",
            "start": start, "stop": stop}


TARGET_BUILDERS = {
    "travel": _travel_target,
    "damper": _damper_target,
    "rack": _rack_target,
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
            "--sets at a folder under sweep_sets/; see docs/reference/sweeps.md."
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
            "See docs/reference/sweeps.md for the key reference."
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


def matches(selector: str, stem: str) -> bool:
    """`--only 01` matches `01_bump_parallel`; so does the full stem."""
    return stem == selector or stem.startswith(f"{selector}_")


# ==========================================================================
# What the geometry can be driven by
# ==========================================================================
def _plain(value) -> str:
    """Normalise an enum or a string to its bare lowercase name."""
    return str(value).rsplit(".", 1)[-1].strip().lower()


def geometry_drives(geometry: Path) -> dict:
    """The corners and actuators this geometry exposes.

    Corner sides come from the geometry file's own `scope:` / `side:`, which is
    where they are declared. Actuator and element ids come from the solver,
    which is the only honest source for what a built suspension will accept -
    restating them here would be the second place this change exists to remove.

    Returns {sides, actuators, elements, unhandled, introspected}. `unhandled`
    names drive coordinates this module has no run.yaml key for; a sweep that
    needs to drive one must use `file:`.
    """
    spec = yaml.safe_load(geometry.read_text()) or {}
    if _plain(spec.get("scope", "corner")) == "axle":
        sides = ["left", "right"]
    else:
        sides = [_plain(spec.get("side", "left"))]

    drives = {
        "sides": sides,
        "actuators": [],
        "elements": {side: [] for side in sides},
        "unhandled": [],
        "introspected": False,
    }

    try:
        from kinematics.core.analysis import initial_pose
        from kinematics.core.input import build_suspension
    except ImportError:
        return drives

    try:
        coordinates = list(initial_pose(build_suspension(spec)).drive_coordinates)
    except AttributeError:
        # The solver's introspection API moved. Fall back to checking only what
        # run.yaml says against itself, rather than blocking the run.
        return drives
    except Exception as error:  # noqa: BLE001 - the geometry itself is bad
        raise SweepSetError(
            f"{geometry.name}: the geometry does not build, so no sweep can be "
            f"generated from it.\n  {error}\n"
            f"Check it with: uv run python Working/check.py {geometry.parent}"
        ) from None

    drives["introspected"] = True
    for coordinate in coordinates:
        cid = _plain(getattr(coordinate, "id", ""))
        ctype = _plain(getattr(coordinate, "type", ""))
        raw_side = getattr(coordinate, "side", None)
        side = _plain(raw_side) if raw_side is not None else None
        if ctype == "actuator_position" and cid in TARGET_BUILDERS:
            if cid not in drives["actuators"]:
                drives["actuators"].append(cid)
        elif ctype == "element_length" and cid == "damper":
            # A one-corner model may publish its damper unsided.
            target = side if side in drives["elements"] else (
                sides[0] if side is None and len(sides) == 1 else None
            )
            if target is None:
                drives["unhandled"].append(f"{cid} ({ctype}, side {side})")
            elif cid not in drives["elements"][target]:
                drives["elements"][target].append(cid)
        else:
            label = f"{cid} ({ctype}{', ' + side if side else ''})"
            if label not in drives["unhandled"]:
                drives["unhandled"].append(label)
    return drives


# ==========================================================================
# Sweep generation - run.yaml is the only source
# ==========================================================================
def _side_span(value, side: str, sides: list[str]):
    """The [start, stop] a range key gives one corner, or None."""
    if value is None:
        return None
    if isinstance(value, dict):
        for key, span in value.items():
            if key is None or _plain(key) == side:
                return span
        return None
    # A bare [start, stop] is the single-corner form: there is only one wheel,
    # so naming a side would say nothing.
    return value if len(sides) == 1 else None


def validate_sweep(name: str, cfg: dict, drives: dict) -> None:
    """Check one sweep's drive keys against what the geometry exposes.

    Every corner must be driven exactly once and every actuator must be given a
    range, because the solver needs one target per degree of freedom at every
    step. Saying so here names the sweep and the coordinate; leaving it to the
    solver costs a subprocess per sweep first.
    """
    sides = drives["sides"]
    given = {group: cfg[group] for group in RANGE_GROUPS
             if cfg.get(group) is not None}

    if not given:
        raise SweepSetError(
            f"sweep '{name}' drives nothing. Give it 'travel' or 'damper' for "
            f"each corner ({', '.join(sides)}) plus a range for every actuator, "
            "or point it at a hand-written sweep file with `file:`. See "
            "docs/reference/sweeps.md."
        )

    # Side keys must name a corner this geometry has.
    for group in CORNER_GROUPS:
        value = given.get(group)
        if isinstance(value, dict):
            unknown = [str(k) for k in value if _plain(k) not in sides]
            if unknown:
                raise SweepSetError(
                    f"sweep '{name}': '{group}' names corner(s) "
                    f"{', '.join(unknown)}, but this geometry has "
                    f"{', '.join(sides)}."
                )
        elif value is not None and len(sides) > 1:
            raise SweepSetError(
                f"sweep '{name}': '{group}' is a bare [start, stop], which is "
                f"the single-corner form. This geometry has corners "
                f"{', '.join(sides)}, so write "
                "{" + ", ".join(f"{s}: [a, b]" for s in sides) + "}."
            )

    # One of travel / damper per corner: never both, never neither.
    for side in sides:
        driving = [group for group in CORNER_GROUPS
                   if _side_span(given.get(group), side, sides) is not None]
        if len(driving) > 1:
            raise SweepSetError(
                f"sweep '{name}': corner '{side}' is driven by both "
                f"{' and '.join(driving)}. A corner has one degree of freedom - "
                "drive it by wheel travel or by damper length, not both."
            )
        if not driving:
            raise SweepSetError(
                f"sweep '{name}': corner '{side}' is not driven. Add 'travel' "
                f"or 'damper' for it. See docs/reference/sweeps.md."
            )
        if "damper" in driving and drives["introspected"] \
                and "damper" not in drives["elements"][side]:
            raise SweepSetError(
                f"sweep '{name}': corner '{side}' has no damper to drive. "
                "Use 'travel', or give the geometry a spring or damper element."
            )

    # Every actuator the geometry declares needs a range, and vice versa.
    if drives["introspected"]:
        for actuator in drives["actuators"]:
            if actuator not in given:
                raise SweepSetError(
                    f"sweep '{name}' does not drive '{actuator}', which this "
                    f"geometry declares. Every actuator must be controlled "
                    f"exactly once at every step - add '{actuator}: [a, b]', "
                    "using [0, 0] to hold it. See docs/reference/sweeps.md."
                )
        for group in ACTUATOR_GROUPS:
            if group in given and group not in drives["actuators"]:
                raise SweepSetError(
                    f"sweep '{name}' sets '{group}', but this geometry has no "
                    f"{group}. Drop the key, or check the geometry's "
                    "steering configuration."
                )


def generate_sweep_file(name: str, cfg: dict, drives: dict, outdir: Path) -> Path:
    """Build one sweep YAML from run.yaml alone and write it out."""
    steps = cfg.get("steps")
    if steps is None:
        raise SweepSetError(
            f"sweep '{name}': missing 'steps'. A generated sweep needs one - "
            "there are no built-in defaults."
        )
    try:
        steps = int(steps)
    except (TypeError, ValueError):
        raise SweepSetError(
            f"sweep '{name}': 'steps' must be a whole number, got {steps!r}"
        ) from None

    targets: list[dict] = []
    for group in CORNER_GROUPS:
        value = cfg.get(group)
        if value is None:
            continue
        for side in drives["sides"]:
            span = _side_span(value, side, drives["sides"])
            if span is None:
                continue
            start, stop = _span(name, group, side, span)
            targets.append(TARGET_BUILDERS[group](side, start, stop))
    for group in ACTUATOR_GROUPS:
        value = cfg.get(group)
        if value is None:
            continue
        start, stop = _span(name, group, None, value)
        targets.append(TARGET_BUILDERS[group](None, start, stop))

    spec = {"version": 1, "steps": steps, "targets": targets}
    header = (
        f"# GENERATED by Working/run_all.py from run.yaml, sweep '{name}'.\n"
        "# Do not edit: it is overwritten on every run, and nothing reads it\n"
        "# back. Edit run.yaml instead - it is the only place this is said.\n"
    )
    return _write_resolved(outdir, f"{name}.yaml", header, yaml.safe_dump(
        spec, sort_keys=False))


def copy_sweep_file(name: str, source: Path, outdir: Path) -> Path:
    """Copy a hand-written sweep file into the resolved directory, verbatim.

    A `file:` sweep is used exactly as written - run.yaml does not override its
    ranges or its step count, because a sweep whose structure needed hand
    authoring is one whose ranges belong beside that structure. Copying it here
    rather than solving it in place keeps _resolved_sweeps/ the complete record
    of what was solved.
    """
    if not source.is_file():
        raise SweepSetError(f"sweep '{name}': file not found: {source}")
    try:
        spec = yaml.safe_load(source.read_text())
    except yaml.YAMLError as error:
        raise SweepSetError(
            f"sweep '{name}': {source} is not valid YAML.\n  {error}"
        ) from None
    if not isinstance(spec, dict) or not spec.get("targets"):
        raise SweepSetError(
            f"sweep '{name}': {source} has no `targets:`. See docs/reference/sweeps.md for the "
            "sweep-file grammar."
        )
    header = (
        f"# COPIED VERBATIM from {source} by Working/run_all.py.\n"
        "# Do not edit this copy: it is overwritten on every run. Edit the\n"
        "# source file instead - run.yaml does not override a `file:` sweep.\n"
    )
    return _write_resolved(outdir, f"{name}.yaml", header, source.read_text())


def _write_resolved(outdir: Path, filename: str, header: str, body: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    resolved = outdir / filename
    resolved.write_text(header + body)
    return resolved


def _span(name: str, group: str, side, span) -> tuple[float, float]:
    """Validate a [start, stop] pair from run.yaml."""
    where = f"{group}{'.' + side if side else ''}"
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        raise SweepSetError(
            f"sweep '{name}': '{where}' must be [start, stop], got {span!r}"
        )
    try:
        return float(span[0]), float(span[1])
    except (TypeError, ValueError):
        raise SweepSetError(
            f"sweep '{name}': '{where}' values must be numbers, got {span!r}"
        ) from None


# ==========================================================================
# Planning: everything up to (not including) solving
# ==========================================================================
@dataclass
class SweepPlan:
    """One enabled sweep of one set, against one geometry."""

    name: str
    resolved: Path | None  # the generated or copied sweep file
    csv: Path
    frames: Path  # positions per step, written by the solve, read by animate
    steps: int
    animate: bool
    animation: Path  # where the animation goes, if `animate`
    fps: int
    dpi: int


@dataclass
class SetPlan:
    """One sweep set planned against one geometry: what to solve and report."""

    name: str
    config_path: Path
    geometry: Path
    model: Path  # the folder holding the geometry; logs and run.log go here
    outputs: Path
    report: Path
    reporter: str
    resolved_config: Path
    sweeps: list[SweepPlan]
    report_wanted: bool


def _animation_format(settings: dict, name: str) -> str:
    fmt = str(settings.get("format", "gif")).strip().lower().lstrip(".")
    if fmt not in ANIMATION_FORMATS:
        raise SweepSetError(
            f"sweep '{name}': gif.format must be one of "
            f"{', '.join(ANIMATION_FORMATS)}, got {fmt!r}"
        )
    return fmt


def plan_sweep_set(config_path: Path, opts: SweepOptions | None = None) -> SetPlan:
    """Validate one sweep set, generate its sweep files, and say what to run.

    Nothing is solved here. Old results of every sweep that is about to run are
    deleted first, so a sweep that fails this time cannot leave last run's CSV
    behind for the report to pick up as if it were current.

    Raises SweepSetError with a reader-ready message on any configuration fault.
    """
    opts = opts or SweepOptions()
    config_path = Path(config_path)
    config = load_run_config(config_path)

    # ---- CLI over run.yaml -------------------------------------------
    if opts.geometry:
        config["geometry"] = str(opts.geometry)
    if opts.side:
        config["side"] = opts.side
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
    if not geometry.is_file():
        raise SweepSetError(f"geometry not found: {geometry}")

    # Results live beside the geometry, in a folder named after the sweep set.
    # That is what lets one sweep set run against several cars.
    set_name = str(config["name"])
    outputs = geometry.parent / SWEEP_OUTPUTS_DIRNAME / set_name
    report = geometry.parent / REPORT_DIRNAME / set_name

    gif_only = opts.gifs
    gifs_master = master_override(config["report"]["gifs"])

    # ---- decide what runs --------------------------------------------
    configured = config["sweeps"] or {}
    if not isinstance(configured, dict) or not configured:
        raise SweepSetError(
            f"{config_path}: `sweeps:` is empty. A sweep set is its sweeps; "
            "see docs/reference/sweeps.md for the keys each one takes."
        )

    chosen: list[dict] = []
    for name, sweep_cfg in configured.items():
        name = str(name)
        if not isinstance(sweep_cfg, dict):
            raise SweepSetError(
                f"{config_path}: sweep '{name}' must be a mapping of settings, "
                f"got {sweep_cfg!r}"
            )
        if "run" not in sweep_cfg:
            raise SweepSetError(
                f"{config_path}: sweep '{name}' has no `run:` setting. "
                "There are no built-in defaults."
            )
        enabled = truthy(sweep_cfg["run"], True)
        if opts.only is not None:
            enabled = any(matches(s, name) for s in opts.only)
        if any(matches(s, name) for s in (opts.skip or [])):
            enabled = False
        if not enabled:
            continue

        # A sweep is generated from its drive keys unless it names a file.
        source = sweep_cfg.get("file")
        if source is not None:
            source = Path(source)
            if not source.is_absolute():
                source = (config_dir / source).resolve()
            clashing = [g for g in RANGE_GROUPS if sweep_cfg.get(g) is not None]
            if clashing:
                raise SweepSetError(
                    f"sweep '{name}' names a `file:` and also sets "
                    f"{', '.join(clashing)}. A `file:` sweep is used verbatim - "
                    "put its ranges in that file, or drop the `file:` key and "
                    "let the sweep be generated."
                )

        # `gif` is optional per sweep: absent means no animation.
        wants_gif = truthy(sweep_cfg.get("gif"), False)
        if isinstance(sweep_cfg.get("gif"), dict):
            wants_gif = truthy(sweep_cfg["gif"].get("enabled"), True)
        if gifs_master is not None:
            wants_gif = gifs_master
        if gif_only is not None:
            wants_gif = any(matches(s, name) for s in gif_only)

        # The top-level `gif:` block, with a per-sweep `gif:` mapping over it.
        gif_settings = dict(config["gif"])
        if isinstance(sweep_cfg.get("gif"), dict):
            gif_settings.update(
                {k: v for k, v in sweep_cfg["gif"].items() if k != "enabled"})

        chosen.append({"name": name, "source": source, "cfg": sweep_cfg,
                       "gif": wants_gif, "gif_settings": gif_settings})

    if not chosen:
        raise SweepSetError(
            f"{set_name}: nothing to run - every sweep is disabled or filtered "
            "out. A selector such as --only applies to every set being run; "
            "use --sets or --config to narrow which sets those are."
        )

    # `--plots a,b` is a whitelist: it forces plots off everywhere else.
    if opts.plots is not None:
        for item in chosen:
            keep = any(matches(s, item["name"]) for s in opts.plots)
            config["sweeps"].setdefault(item["name"], {})
            config["sweeps"][item["name"]]["plots"] = "all" if keep else "none"

    outputs.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True, exist_ok=True)

    # ---- the resolved configuration -----------------------------------
    # run.yaml after the command-line overrides: what susreport reads, and the
    # record of what ran. `ran` is narrowed to the sweeps that actually solved
    # when the report is built.
    resolved_config = {
        key: config[key] for key in
        ("name", "reporter", "side", "decimals", "report", "solver", "gif")
        if key in config
    }
    resolved_config.update({
        "sweeps": {i["name"]: i["cfg"] for i in chosen},
        "ran": [i["name"] for i in chosen],
        "geometry": str(geometry),
        "source_config": str(config_path),
    })
    resolved_path = report / "_resolved_run.json"
    resolved_path.write_text(json.dumps(resolved_config, indent=2, default=str))

    # Validate the half of the configuration susreport owns, before spending
    # any CPU. This is also what makes --dry-run a complete config check.
    if not opts.solve_only:
        common, _reporter = load_reporter(str(config["reporter"]))
        try:
            common.load_config(None, resolved_path)
        except SystemExit as error:
            raise SweepSetError(str(error.code)) from None

    # ---- generate the sweep files ------------------------------------
    resolved_dir = outputs / RESOLVED_DIRNAME
    if not opts.report_only:
        drives = geometry_drives(geometry)
        if drives["unhandled"]:
            print(f"   note ({set_name}): this geometry exposes drive coordinate(s) "
                  "run.yaml has no key for: " + ", ".join(drives["unhandled"])
                  + ". A sweep that must drive one needs `file:` (docs/reference/sweeps.md).")
        # Validate every sweep before generating any, so the first complaint
        # names the sweep rather than arriving with half the set written.
        for item in chosen:
            if item["source"] is None:
                validate_sweep(item["name"], item["cfg"], drives)

    plans: list[SweepPlan] = []
    for item in chosen:
        name = item["name"]
        resolved = None
        if not opts.report_only:
            if item["source"] is None:
                resolved = generate_sweep_file(name, item["cfg"], drives, resolved_dir)
            else:
                resolved = copy_sweep_file(name, item["source"], resolved_dir)
        steps = int((yaml.safe_load(resolved.read_text()) or {}).get("steps", 0)) \
            if resolved else 0
        settings = item["gif_settings"]
        fmt = _animation_format(settings, name)
        plan = SweepPlan(
            name=name,
            resolved=resolved,
            csv=outputs / f"{name}.csv",
            frames=outputs / FRAMES_DIRNAME / f"{name}.npz",
            steps=steps,
            animate=bool(item["gif"]),
            animation=outputs / f"{name}.{fmt}",
            fps=int(settings["fps"]),
            dpi=int(settings["dpi"]),
        )
        if not opts.report_only and not opts.dry_run:
            # Stale results of a sweep about to be re-solved must not survive.
            stale = [plan.csv, plan.frames,
                     *(outputs / f"{name}.{ext}" for ext in ANIMATION_FORMATS)]
            for path in stale:
                path.unlink(missing_ok=True)
        plans.append(plan)

    return SetPlan(
        name=set_name,
        config_path=config_path,
        geometry=geometry,
        model=geometry.parent,
        outputs=outputs,
        report=report,
        reporter=str(config["reporter"]),
        resolved_config=resolved_path,
        sweeps=plans,
        report_wanted=not opts.solve_only,
    )


# ==========================================================================
# Reporting (runs in a pool worker; see tasks.py)
# ==========================================================================
STATUS_COLUMNS = ("sweep", "status", "steps", "where", "reason")


def describe_failure(result: dict) -> str:
    """Where a sweep stopped, in words: 'step 41/65 (travel_left -55, rack 22.1)'."""
    if result.get("fail_step") is None:
        return ""
    pose = ", ".join(f"{k} {v:g}" for k, v in (result.get("at") or {}).items())
    text = f"step {result['fail_step']}/{result.get('n_steps', '?')}"
    if pose:
        text += f" ({pose})"
    good = result.get("last_good")
    if good:
        text += "; last solved: " + ", ".join(f"{k} {v:g}" for k, v in good.items())
    return text


def status_rows(results: list[dict]) -> list[dict]:
    """One row per sweep for solve_status.csv and the report's status table."""
    rows = []
    for r in results:
        steps = r.get("steps_ok")
        rows.append({
            "sweep": r.get("sweep", ""),
            "status": r.get("status", ""),
            "steps": f"{steps}/{r.get('n_steps')}" if steps is not None else "",
            "where": describe_failure(r),
            "reason": r.get("message", "") if r.get("status") != "ok" else "",
        })
    return rows


def status_markdown(results: list[dict]) -> list[str]:
    """The "Solve status" section placed at the top of report.md."""
    lines = ["## Solve status\n",
             "| sweep | status | steps | where it stopped | reason |",
             "| --- | --- | --- | --- | --- |"]
    for row in status_rows(results):
        reason = str(row["reason"]).replace("|", "/")
        lines.append(f"| `{row['sweep']}` | {row['status']} | {row['steps']} | "
                     f"{row['where'] or '-'} | {reason or '-'} |")
    lines.append("")
    return lines


def write_status_csv(path: Path, results: list[dict]) -> None:
    """report/<set>/solve_status.csv."""
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=STATUS_COLUMNS)
        writer.writeheader()
        writer.writerows(status_rows(results))


def build_report(payload: dict) -> dict:
    """Build one set's report from the sweeps that solved. Called by tasks.py.

    payload: resolved_config, outputs, report, reporter, results (the solve
    results for this set, in plan order).
    """
    results = payload["results"]
    report = Path(payload["report"])
    write_status_csv(report / "solve_status.csv", results)

    solved = [r["sweep"] for r in results if r.get("status") in ("ok", "warn")]
    if not solved:
        return {"status": "skipped", "message": "no sweep solved, so no report"}

    resolved_path = Path(payload["resolved_config"])
    resolved = json.loads(resolved_path.read_text())
    resolved["ran"] = solved
    resolved_path.write_text(json.dumps(resolved, indent=2, default=str))

    common, reporter = load_reporter(payload["reporter"])
    config = common.load_config(None, resolved_path)
    report_md = common.run_report(Path(payload["outputs"]), report, config, reporter)

    # The status table goes at the top, under the title: the first thing a
    # reader needs is which sweeps are missing from everything below.
    lines = Path(report_md).read_text(encoding="utf-8").split("\n")
    insert_at = 1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1
    lines[insert_at:insert_at] = status_markdown(results)
    Path(report_md).write_text("\n".join(lines), encoding="utf-8")

    failed = len(results) - len(solved)
    return {
        "status": "ok",
        "output": str(report_md),
        "message": f"{failed} sweep(s) missing (not solved)" if failed else "",
    }


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


