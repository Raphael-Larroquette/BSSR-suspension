"""
Solve one candidate geometry through the sweeps the objectives need.

Two things this module deliberately does NOT do any more:

* It does not read ``sweep_sets/<axle>/sweeps/*.yaml``. Those files no longer
  exist: ``run.yaml`` is the whole sweep set, and a sweep's targets are
  generated from its ``travel`` / ``damper`` / ``rack`` keys. The generation is
  done by calling ``sweep_sets/runner.py`` — the same code the report workflow
  uses — rather than reimplementing it here, so the optimiser cannot drift into
  solving something the reports no longer solve.

* It does not hard-code ``models/aurora/front.yaml`` as the template. The car
  comes from ``optimizer.CAR_NAME``, which is what ``export_pareto.py`` already
  honours when it copies the template folder. With the path fixed here and
  CAR_NAME respected there, the two agreed only by coincidence: you could
  optimise Aurora's geometry and have the results written into another car's
  folder.

Both the template and the generated sweep specs are cached per car, so the
cost is paid once per process rather than once per candidate — which matters
when a run evaluates several thousand of them across a worker pool.
"""

import copy
import importlib.util
import sys
import tempfile
import warnings
from pathlib import Path

import yaml
from kinematics.core.analysis import analyze_sweep
from kinematics.core.input import build_suspension, build_sweep

WORKING = Path(__file__).resolve().parent.parent

#: Axle a run optimises, unless optimizer.py names another one.
DEFAULT_AXLE = "front"

#: Car whose model file is the template, unless optimizer.py names another one.
DEFAULT_CAR = "aurora"

_TEMPLATES = {}
_SWEEP_SPECS = {}
_SWEEP_SOURCES = {}
_RUNNER = None


def _setting(name, default):
    """Read one setting from optimizer.py, falling back to a default."""
    import optimizer

    return getattr(optimizer, name, default)


def target_car():
    """Return the (car, axle) this run optimises."""
    return _setting("CAR_NAME", DEFAULT_CAR), _setting("AXLE", DEFAULT_AXLE)


def model_path(car=None, axle=None):
    """Return the model file the candidate hardpoints are patched into."""
    if car is None or axle is None:
        car, axle = target_car()
    path = WORKING / "models" / car / f"{axle}.yaml"
    if not path.is_file():
        available = sorted(p.name for p in (WORKING / "models").iterdir() if p.is_dir())
        raise FileNotFoundError(
            f"no model at {path}. CAR_NAME is '{car}' and AXLE is '{axle}'; "
            f"models/ holds: {', '.join(available)}"
        )
    return path


def run_config_path(axle=None):
    """Return the sweep set for this axle. run.yaml IS the sweep set."""
    if axle is None:
        _, axle = target_car()
    path = WORKING / "sweep_sets" / axle / "run.yaml"
    if not path.is_file():
        raise FileNotFoundError(
            f"no sweep set at {path}. run.yaml is the whole sweep set; see "
            "Working/sweep_sets/RUNNING.md"
        )
    return path


def load_runner():
    """Import ``sweep_sets/runner.py`` once, and reuse it."""
    global _RUNNER
    if _RUNNER is not None:
        return _RUNNER
    path = WORKING / "sweep_sets" / "runner.py"
    if not path.is_file():
        raise FileNotFoundError(f"no sweep runner at {path}")
    name = "bssr_sweep_runner"
    cached = sys.modules.get(name)
    if cached is None:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        # Register before executing: @dataclass looks its own module up in
        # sys.modules while the class body runs, and fails if it is absent.
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            del sys.modules[name]
            raise
        cached = module
    _RUNNER = cached
    return _RUNNER


def _apply_limits(spec, limits):
    """
    Narrow a generated sweep to the optimisation range, in place.

    A target authored with ``start == stop`` is holding something still — a
    centred rack, a wheel at design height — and is left alone.

    The authored *orientation* is preserved rather than overwritten, so a sweep
    whose two corners move in opposite directions stays that way. Assigning
    ``(start, stop)`` to every moving target, as this previously did, would
    silently turn the roll sweep into a second parallel-heave sweep the moment
    an objective read it.
    """
    low, high = float(limits["start"]), float(limits["stop"])
    for target in spec.get("targets", []):
        start, stop = target.get("start"), target.get("stop")
        if start is None or stop is None or start == stop:
            continue
        target["start"], target["stop"] = (
            (low, high) if start < stop else (high, low)
        )


def _sweep_source(car, axle):
    """Return the runner, the run config and what this geometry can be driven by."""
    key = (car, axle)
    if key not in _SWEEP_SOURCES:
        runner = load_runner()
        config_path = run_config_path(axle)
        _SWEEP_SOURCES[key] = (
            runner,
            config_path,
            runner.load_run_config(config_path),
            runner.geometry_drives(model_path(car, axle)),
        )
    return _SWEEP_SOURCES[key]


def build_sweep_spec(name, car=None, axle=None):
    """
    Generate one sweep declared in run.yaml, as an in-memory spec.

    Generated **per sweep on demand**, not for the whole set: a run reads two of
    the ten sweeps declared, and building all of them would let an unrelated
    sweep — one the optimiser never looks at — fail validation and take the run
    down with it.

    The runner writes a generated sweep to disk, so it is produced into a
    scratch directory and read straight back. That keeps this a call into the
    team's own generation rather than a second copy of its rules.
    """
    import optimizer

    if car is None or axle is None:
        car, axle = target_car()
    runner, config_path, run_config, drives = _sweep_source(car, axle)

    declared = run_config.get("sweeps") or {}
    entry = declared.get(name)
    if entry is None:
        raise KeyError(
            f"sweep '{name}' is not declared in {config_path}. It declares: "
            f"{sorted(declared)}"
        )
    if not entry.get("run", True):
        warnings.warn(
            f"sweep '{name}' is switched off in {config_path.name} (run: false) "
            "but an objective or constraint reads it. The optimiser will solve "
            "it anyway; the reports will not.",
            stacklevel=2,
        )

    with tempfile.TemporaryDirectory() as scratch:
        outdir = Path(scratch)
        source = entry.get("file")
        if source is not None:
            written = runner.copy_sweep_file(
                name, (config_path.parent / source).resolve(), outdir
            )
        else:
            runner.validate_sweep(name, entry, drives)
            written = runner.generate_sweep_file(name, entry, drives, outdir)
        spec = yaml.safe_load(Path(written).read_text(encoding="utf-8"))

    limits = getattr(optimizer, "SWEEP_LIMITS", {})
    if name in limits:
        _apply_limits(spec, limits[name])

    # Optimiser-only step count. run.yaml's own count is what the reports
    # solve at; the search reads far fewer frames than it solves, so paying for
    # full resolution is waste. See SWEEP_STEPS in optimizer.py for which
    # frames each reduction actually reads, and why a coarser sweep is safe.
    steps = getattr(optimizer, "SWEEP_STEPS", {})
    if name in steps:
        wanted = int(steps[name])
        if wanted < 2:
            raise ValueError(
                f"SWEEP_STEPS['{name}'] is {wanted}; a sweep needs at least 2 "
                "steps to have a range at all"
            )
        spec["steps"] = wanted
    return spec


def sweep_spec(name):
    """Return one generated sweep spec, generating it on first use."""
    key = target_car()
    cache = _SWEEP_SPECS.setdefault(key, {})
    if name not in cache:
        cache[name] = build_sweep_spec(name, *key)
    return cache[name]


def solver_policy(axle=None):
    """
    Return ``(on_bad_solve, residual_limit)`` exactly as run.yaml declares them.

    The sweep set already states what to do about a step that did not solve —
    ``off`` ignores it, ``warn`` flags it and drops it from the statistics,
    ``fail`` stops — so the optimiser reads that policy rather than inventing a
    second one. See :func:`opt.reduce.usable_frames` for how it is applied.
    """
    car, resolved = target_car()
    if axle is None:
        axle = resolved
    _, _, run_config, _ = _sweep_source(car, axle)
    block = run_config.get("solver") or {}
    mode = str(block.get("on_bad_solve", "warn")).strip().lower()
    limit = block.get("residual_limit")
    return mode, (float(limit) if limit is not None else None)


def template(car=None, axle=None):
    """Return the model data for this car, loaded once per process."""
    path = model_path(car, axle)
    if path not in _TEMPLATES:
        with open(path, "r", encoding="utf-8") as handle:
            _TEMPLATES[path] = yaml.safe_load(handle)
    return _TEMPLATES[path]


def solve_stage(hardpoints_dict, required_sweeps):
    """Build the candidate suspension and analyse it through the named sweeps."""
    data = copy.deepcopy(template())
    left = data.get("hardpoints", {}).get("left")
    if left is None:
        raise KeyError(
            f"{model_path().name} authors no hardpoints.left, so it cannot be "
            "used as an optimisation template"
        )

    for hp_name, coords in hardpoints_dict.items():
        if hp_name not in left:
            raise KeyError(
                f"the derivation produced '{hp_name}', which "
                f"{model_path().name} does not author. Fix the name in "
                "derive_parameters, or add the point to the model."
            )
        left[hp_name].update(coords)

    suspension = build_suspension(data)

    out = {}
    for name in required_sweeps:
        spec = copy.deepcopy(sweep_spec(name))
        out[name] = analyze_sweep(suspension, build_sweep(spec, suspension))
    return out
