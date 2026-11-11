#!/usr/bin/env python3
"""
The work run_all.py hands to the process pool, one function per kind of task.

This is a LIBRARY. Every function here runs inside a pool worker (see
scheduler.py), takes a plain dict payload and returns a plain dict result. They
never raise: a failure is a result with a status and a reader-ready message, so
one bad sweep cannot take down the pool or hide the others.

    solve    one sweep of one model -> <sweep>.csv, and the frames to animate
    forces   one model's static force solve -> forces/forces.csv
    report   one sweep set of one model -> report/<set>/report.md
    animate  one solved sweep -> <sweep>.gif (or .mp4)

Each task writes what it printed, and any traceback, to its own log file under
<model>/logs/, so run.log stays one line per task.

STATUSES

    ok            done
    warn          done, but the solver flagged steps (residual over the limit)
    lockout       no pose exists at some step: the mechanism cannot reach the
                  requested targets (a geometry result, not a software fault)
    geometry      the geometry file does not build
    resource      ran out of memory; the scheduler retries these
    skipped       nothing to do (e.g. a report for a set where nothing solved)
    error         anything else; see the task's log for the traceback
"""

from __future__ import annotations

import contextlib
import io
import re
import time
import traceback
from pathlib import Path

#: Statuses that count as success.
OK_STATUSES = ("ok", "warn")

#: Message fragments that mean "the machine ran out of memory".
_RESOURCE_HINTS = (
    "paging file is too small",
    "unable to allocate",
    "cannot allocate memory",
    "out of memory",
    "not enough memory",
    "memoryerror",
)

#: Message fragments the solver uses when a pose cannot be reached.
_LOCKOUT_HINTS = (
    "Solver failed to converge",
    "did not reach an acceptable residual",
)


# ==========================================================================
# Plumbing shared by every task
# ==========================================================================
def is_resource_error(error: BaseException) -> bool:
    """True when an exception means the machine, not the input, was the problem."""
    if isinstance(error, MemoryError):
        return True
    if getattr(error, "winerror", None) == 1455:  # ERROR_COMMITMENT_LIMIT
        return True
    text = f"{type(error).__name__}: {error}".lower()
    return any(hint in text for hint in _RESOURCE_HINTS)


def _headline(error: BaseException, limit: int = 300) -> str:
    text = " ".join(str(error).split())
    text = f"{type(error).__name__}: {text}" if text else type(error).__name__
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _run(payload: dict, body) -> dict:
    """Run `body(payload)` with output captured to the task log; never raise."""
    from scheduler import process_peak_mb

    started = time.perf_counter()
    result: dict = dict(payload.get("identity", {}))
    log_path = Path(payload["log"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            result.update(body(payload))
    except SystemExit as error:  # the reporters stop with SystemExit(message)
        result.update(status="error", message=str(error.code))
    except BaseException as error:  # noqa: BLE001 - must never escape the worker
        if isinstance(error, KeyboardInterrupt):
            raise
        buffer.write("\n" + traceback.format_exc())
        if is_resource_error(error):
            result.update(status="resource", message=_headline(error))
        else:
            result.setdefault("status", "error")
            if result["status"] in ("ok", "warn"):
                result["status"] = "error"
            result.setdefault("message", _headline(error))
    result.setdefault("status", "ok")
    result["seconds"] = round(time.perf_counter() - started, 2)
    result["peak_mb"] = round(process_peak_mb(), 1)
    result["log"] = str(log_path)
    try:
        log_path.write_text(buffer.getvalue(), encoding="utf-8")
    except OSError:
        pass
    return result


def execute(payload: dict) -> dict:
    """The single entry point the pool calls: dispatch on payload['kind']."""
    kind = payload["kind"]
    body = {
        "solve": _solve,
        "forces": _forces,
        "report": _report,
        "animate": _animate,
    }[kind]
    return _run(payload, body)


# ==========================================================================
# solve
# ==========================================================================
def _target_label(target: dict) -> str:
    """A short name for one sweep target: travel_left, damper_right, rack, ..."""
    kind = target.get("type")
    side = target.get("side")
    if kind == "point" and target.get("point") == "wheel_center":
        name = "travel"
    elif kind == "element_length":
        name = str(target.get("element", "length"))
    elif kind == "actuator_position":
        return str(target.get("actuator", "actuator"))
    else:
        name = str(target.get("point") or kind or "target")
    return f"{name}_{side}" if side else name


def _relative_values(
    sweep_path: Path,
) -> tuple[list[str], list[list[float | None]], int]:
    """(labels, per-step values, steps) as written in the sweep file."""
    import numpy as np
    import yaml

    spec = yaml.safe_load(sweep_path.read_text()) or {}
    steps = int(spec.get("steps", 0) or 0)
    labels, columns = [], []
    for target in spec.get("targets", []):
        labels.append(_target_label(target))
        if "values" in target:
            columns.append([float(v) for v in target["values"]])
        elif "start" in target and "stop" in target and steps:
            columns.append(list(np.linspace(float(target["start"]),
                                            float(target["stop"]), steps)))
        else:
            columns.append([None] * steps)
    steps = steps or (len(columns[0]) if columns else 0)
    rows = [[col[i] if i < len(col) else None for col in columns] for i in range(steps)]
    return labels, rows, steps


def _failing_step(error: BaseException, geometry: Path, sweep: Path) -> int | None:
    """Which step (0-based) a solver failure happened at.

    The residual failure names its step. The non-convergence failure only
    lists the absolute target values it was solving for, so the step is found
    by matching those against each step's targets.
    """
    text = str(error)
    found = re.search(r"sweep step (\d+)", text)
    if found:
        return int(found.group(1))
    values = [float(v) for v in re.findall(
        r"value=(?:np\.float64\()?([-+0-9.eE]+)", text)]
    if not values:
        return None
    import numpy as np

    from kinematics.cli.io.loaders import load_geometry
    from kinematics.cli.io.sweep_loader import load_sweep
    from kinematics.core.solver import convert_targets_to_absolute

    suspension = load_geometry(geometry)
    config = load_sweep(sweep, suspension)
    initial = suspension.initial_state()
    best, best_error = None, float("inf")
    for index in range(config.n_steps):
        targets = convert_targets_to_absolute(
            [series[index] for series in config.target_sweeps], initial)
        absolute = [float(getattr(t, "value", np.nan)) for t in targets]
        if len(absolute) != len(values):
            return None
        mismatch = float(np.nansum(np.abs(np.subtract(absolute, values))))
        if mismatch < best_error:
            best, best_error = index, mismatch
    return best


def _pose(labels: list[str], row: list[float | None]) -> dict[str, float]:
    return {label: round(float(value), 3)
            for label, value in zip(labels, row) if value is not None}


def _solve(payload: dict) -> dict:
    from kinematics.cli.commands.sweep import run_sweep_files

    geometry = Path(payload["geometry"])
    sweep = Path(payload["sweep"])
    csv = Path(payload["csv"])
    labels, rows, steps = _relative_values(sweep)
    out: dict = {"n_steps": steps}

    try:
        from kinematics.cli.io.loaders import load_geometry

        load_geometry(geometry)
    except Exception as error:  # noqa: BLE001
        if is_resource_error(error):
            raise
        return {**out, "status": "geometry", "message": _headline(error)}

    try:
        run = run_sweep_files(geometry, sweep, csv)
    except RuntimeError as error:
        if is_resource_error(error) or not any(
                hint in str(error) for hint in _LOCKOUT_HINTS):
            raise
        print(traceback.format_exc())
        step = _failing_step(error, geometry, sweep)
        solver_says = str(error).rsplit("Message:", 1)[-1].strip() \
            if "Message:" in str(error) else ""
        if "acceptable residual" in str(error):
            reason = "the closest pose leaves a constraint violated"
        else:
            reason = "no pose satisfies the targets"
        if solver_says:
            reason += f" (solver: {solver_says})"
        out.update(status="lockout", message=reason)
        if step is not None and step < len(rows):
            out.update(steps_ok=step, fail_step=step + 1,
                       at=_pose(labels, rows[step]))
            if step > 0:
                out["last_good"] = _pose(labels, rows[step - 1])
        return out

    diagnostics = [str(d) for d in run.evaluated.diagnostics]
    for line in diagnostics:
        print(f"diagnostic: {line}")
    out.update(steps_ok=steps, status="warn" if diagnostics else "ok")
    if diagnostics:
        out["message"] = diagnostics[0][:300] + (
            f" (+{len(diagnostics) - 1} more)" if len(diagnostics) > 1 else "")

    if payload.get("frames"):
        _save_frames(run, Path(payload["frames"]))
    if payload.get("force_cases"):
        _forces_over_travel(run, payload, out)
    return out


def _forces_over_travel(run, payload: dict, out: dict) -> None:
    """Solve the sweep's `forces:` cases at every step; write <sweep>_forces.csv.

    A failure here is reported on the sweep (status warn) rather than failing
    it: the kinematics solved, and the CSV and report stand on their own.
    """
    from kinematics.cli.commands.forces import run_force_travel
    from kinematics.core.loads.cases import LoadCase

    try:
        travel = run_force_travel(
            Path(payload["forces_config"]),
            run.suspension,
            run.evaluated.states,
            [LoadCase(*case) for case in payload["force_cases"]],
            Path(payload["forces_csv"]),
        )
    except Exception as error:  # noqa: BLE001
        if is_resource_error(error):
            raise
        print(traceback.format_exc())
        message = f"forces along travel failed: {_headline(error)}"
        out.update(status="warn", message=(
            f"{out['message']}; {message}" if out.get("message") else message))
        return
    for line in travel.diagnostics:
        print(f"forces: {line}")


def _save_frames(run, path: Path) -> None:
    """Store the presentation positions of every step, for the animate task.

    A few kB per sweep; it lets the animation be drawn later, in another
    process, without solving the sweep a second time.
    """
    import numpy as np

    from kinematics.cli.visualization.main import build_render_model

    model = build_render_model(run.suspension)
    initial = model.positions(run.suspension.initial_state())
    names = list(initial)
    states = np.array([[model.positions(state)[name] for name in names]
                       for state in run.evaluated.states], dtype=float)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        names=np.array(names),
        states=states,
        initial=np.array([initial[name] for name in names], dtype=float),
    )


# ==========================================================================
# forces
# ==========================================================================
def _forces(payload: dict) -> dict:
    from kinematics.cli.commands.forces import run_force_files

    config = Path(payload["config"])
    cases = Path(payload["cases"]) if payload.get("cases") else None
    run = run_force_files(config, None, None, cases, None, None, None)
    diagnostics = [str(d) for d in run.run.solution.diagnostics]
    for line in diagnostics:
        print(f"diagnostic: {line}")
    print(f"wrote {run.output_path}")
    print(f"wrote {run.load_transfer_path}")
    result = {"status": "warn" if diagnostics else "ok",
              "output": str(run.output_path)}
    if diagnostics:
        result["message"] = diagnostics[0][:300]
    return result


# ==========================================================================
# report
# ==========================================================================
def _report(payload: dict) -> dict:
    import runner

    return runner.build_report(payload)


# ==========================================================================
# animate
# ==========================================================================
def _animate(payload: dict) -> dict:
    import numpy as np

    from kinematics.cli.io.loaders import load_geometry
    from kinematics.cli.visualization.main import build_render_model
    from kinematics.cli.visualization.render2d import write_animation

    data = np.load(payload["frames"])
    names = [str(n) for n in data["names"]]
    states = [dict(zip(names, map(tuple, frame))) for frame in data["states"]]
    initial = dict(zip(names, map(tuple, data["initial"])))
    visualizer = build_render_model(load_geometry(Path(payload["geometry"]))).visualizer
    path = write_animation(states, initial, visualizer, Path(payload["out"]),
                           fps=int(payload["fps"]), dpi=int(payload["dpi"]))
    print(f"wrote {path}")
    return {"status": "ok", "output": str(path)}
