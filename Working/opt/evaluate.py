import math
import time
import subprocess
import csv
from pathlib import Path
from dataclasses import dataclass
from .construct import expand_hardpoints
from .solve import solve_stage
from .reduce import reduce_outcomes
import sys
from .settings import current as current_settings

@dataclass(frozen=True)
class Evaluation:
    outcomes: dict
    feasible: bool
    failure: str
    diagnostics: list
    seconds: float
    hardpoints: dict

try:
    SOLVER_SHA = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
except Exception:
    SOLVER_SHA = "unknown"

_FIXED = {}


def fixed_params():
    """
    The non-searched numbers derive_parameters() builds every candidate from.

    Nothing here is a constant of this module. The tyre's design radius and the
    wheel offset come from the TEMPLATE model's own geometry file, so they can
    never disagree with the model the candidate is patched into. The design
    rules - track width, caster, minimum arm separation - are settings in the
    optimizer script.
    """
    settings = current_settings()
    key = id(settings)
    if key not in _FIXED:
        from .solve import template_wheel

        radius, offset = template_wheel()
        _FIXED[key] = {
            "track_width": float(settings.TRACK_WIDTH),
            "rolling_radius": radius,
            "wheel_offset": offset,
            "caster_deg": float(settings.CASTER_DEG),
            "min_outboard_separation": float(settings.MIN_ARM_SEPARATION),
        }
    return _FIXED[key]


def _report(stage, err):
    """Print one candidate's failure, only when settings.VERBOSE_FAILURES asks.

    Most failures are expected: roughly two thirds of random geometries lock
    up or cannot assemble. Printed one per line they bury the progress table,
    so by default each generation prints a count instead (see
    problem.LogGeneration). Turn this on to see why individual candidates fail.
    """
    settings = current_settings()
    if getattr(settings, "VERBOSE_FAILURES", False):
        print(f"{stage} error: {err}")


def evaluate(params: dict) -> Evaluation:
    settings = current_settings()
    started = time.perf_counter()
    
    try:
        derived_flat = settings.derive_parameters(params, fixed_params())
        hardpoints = expand_hardpoints(derived_flat)
    except Exception as err:
        _report("construct", err)
        return Evaluation({}, False, f"construct: {type(err).__name__}: {err}", [], time.perf_counter() - started, {})

    # Pre-solve rack packaging. The inner tie rod point is calculated, not
    # searched, so it can land anywhere; outside its window there is no rack.
    limits = getattr(settings, "TRACKROD_INBOARD_LIMITS", {})
    for axis, (lo, hi) in limits.items():
        value = derived_flat[f"trackrod_inboard.{axis}"]
        if not lo <= value <= hi:
            msg = f"inner tie rod {axis} = {value:.1f} mm outside ({lo}, {hi})"
            _report("presolve", msg)
            return Evaluation({}, False, f"presolve: {msg}", [],
                              time.perf_counter() - started, hardpoints)

    # Pre-solve shock length. The design pose is one frame of the bump sweep,
    # so a shock already shorter than the minimum here must fail the post-solve
    # check too: skip the solve. The length is kept as the candidate's
    # shock_length outcome, so the optimiser still sees how short it was
    # (see problem.SuspensionProblem._evaluate).
    min_length = getattr(settings, "MIN_SHOCK_LENGTH", None)
    if min_length is not None:
        design_length = math.dist(
            [derived_flat[f"strut_top.{a}"] for a in "xyz"],
            [derived_flat[f"strut_bottom.{a}"] for a in "xyz"],
        )
        if design_length < min_length:
            _report("presolve", f"design shock length {design_length:.1f} mm < {min_length} mm")
            return Evaluation(
                {"shock_length": design_length}, False,
                f"presolve: design shock length {design_length:.1f} mm < {min_length} mm",
                [], time.perf_counter() - started, hardpoints,
            )

    required_sweeps = set()
    for s, m, d in settings.OBJECTIVES.values():
        required_sweeps.add(s)
    for s, m, b in settings.CONSTRAINTS.values():
        required_sweeps.add(s)
        
    try:
        analyses = solve_stage(hardpoints, list(required_sweeps))
    except (ValueError, RuntimeError) as err:
        _report("solve", err)
        return Evaluation({}, False, f"solve: {type(err).__name__}: {err}", [], time.perf_counter() - started, hardpoints)
        
    try:
        outcomes = reduce_outcomes(analyses, settings.OBJECTIVES, settings.CONSTRAINTS, settings.BUMP_WEIGHTING)
    except Exception as err:
        _report("reduce", err)
        return Evaluation({}, False, f"reduce: {type(err).__name__}: {err}", [], time.perf_counter() - started, hardpoints)
        
    warnings = [str(d) for a in analyses.values() for d in getattr(a, "diagnostics", ())]
    
    return Evaluation(outcomes, True, None, warnings, time.perf_counter() - started, hardpoints)

def write_log_rows(evaluations, gen, log_path):
    if not evaluations:
        return
        
    file_exists = log_path.exists()
    
    with open(log_path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            header = ["Generation", "Feasible", "Failure", "Time", "SHA"]
            header += list(evaluations[0][0].keys())
            header += list(evaluations[0][1].outcomes.keys())
            writer.writerow(header)
            
        for params, ev in evaluations:
            row = [gen, ev.feasible, ev.failure or "", f"{ev.seconds:.3f}", SOLVER_SHA]
            row += [params[k] for k in params.keys()]
            if ev.feasible:
                row += [ev.outcomes.get(k, "") for k in ev.outcomes.keys()]
            else:
                row += [""] * len(ev.outcomes)
            writer.writerow(row)

def run_optimization(script):
    """Run the search configured by `script` (an optimizer script's __file__)."""
    from .problem import run_pymoo
    from .settings import activate

    activate(script)
    run_pymoo()
