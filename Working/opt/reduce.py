import math

import numpy as np

#: Fewest frames a reduction will work from after bad solves are dropped. Below
#: three there is not enough curve left to integrate meaningfully.
MIN_USABLE_FRAMES = 3

#: Smallest fraction of a sweep's frames that must survive. If more than half a
#: sweep failed to solve, that is not a numerical blip - the linkage cannot make
#: the requested travel, and the candidate is reported infeasible for that
#: reason rather than scored on the remainder.
MIN_USABLE_FRACTION = 0.5


def _frame_ok(frame, residual_limit):
    """Return True when this step's solve can be trusted."""
    info = getattr(frame, "solver", None)
    if info is None:
        return True
    if not info.converged:
        return False
    if residual_limit is not None and info.max_residual > residual_limit:
        return False
    return True


def usable_frames(analysis, sweep_name):
    """
    Return the frames a reduction may read, applying run.yaml's solver policy.

    Non-convergence is a numerical event, not automatically a design verdict: a
    single ill-conditioned pose can fail while its neighbours solve cleanly, and
    a residual marginally over tolerance is still essentially the right pose.
    Discarding a whole candidate for either would throw away good designs.

    So this follows ``on_bad_solve`` from run.yaml, which already says what to
    do: ``off`` reads every frame, ``warn`` drops the bad ones exactly as the
    reports drop them from min/max/range, and ``fail`` refuses the candidate.

    What is NOT tolerated is integrating over frames that did not solve, which
    is what happened before: the objective was computed from whatever numbers
    the failed steps happened to leave behind.

    Raises:
        ValueError: if too little of the sweep survives to reduce honestly. The
            caller reports the candidate as infeasible carrying this reason, so
            the log says which sweep failed and how much of it.
    """
    from .solve import solver_policy

    mode, residual_limit = solver_policy()
    frames = analysis.frames
    if mode == "off" or not frames:
        return frames

    good = [f for f in frames if _frame_ok(f, residual_limit)]
    dropped = len(frames) - len(good)

    if dropped and mode == "fail":
        raise ValueError(
            f"sweep '{sweep_name}': {dropped} of {len(frames)} steps did not "
            f"solve within residual_limit, and run.yaml sets "
            f"on_bad_solve: fail"
        )
    if len(good) < MIN_USABLE_FRAMES or len(good) < MIN_USABLE_FRACTION * len(frames):
        raise ValueError(
            f"sweep '{sweep_name}': only {len(good)} of {len(frames)} steps "
            "solved, too few to reduce. The linkage most likely cannot reach "
            "the requested travel."
        )
    return good


#: Below this ideal inner-minus-outer difference (deg) the percentage is noise.
#: Same threshold as the report (susreport.ACKERMANN_MIN_IDEAL_DELTA_DEG).
ACKERMANN_MIN_IDEAL_DELTA_DEG = 0.25


def ackermann_percent(frame) -> float:
    """Signed Ackermann percentage of one steered frame, as the report defines it.

    100% = true Ackermann, 0% = parallel, NEGATIVE = anti-Ackermann (the wheel
    on the inside of the turn steers LESS than the outside one).

    Which wheel is inner comes from the turn DIRECTION, not from which wheel
    steers more: ISO steer > 0 is a left turn, so the left wheel is inner.
    Taking inner = max(|left|, |right|) instead - which this function replaced -
    makes the result symmetric under swapping the wheels, so anti-Ackermann of
    the same size reads as positive Ackermann and passes the constraint.

    A frame too close to centre to measure returns 0.0, which fails any
    Ackermann band instead of passing it by default.
    """
    steer_l = frame.corner_metrics["left"]["steer_angle"]
    steer_r = frame.corner_metrics["right"]["steer_angle"]
    left_turn = (steer_l + steer_r) > 0.0
    inner, outer = (steer_l, steer_r) if left_turn else (steer_r, steer_l)
    inner, outer = abs(inner), abs(outer)

    wheelbase = _wheelbase()
    track = frame.metrics.get("track", 1000.0)
    if outer <= 1e-6:
        return 0.0
    inner_arm = max(wheelbase / math.tan(math.radians(outer)) - track, 1e-9)
    ideal_delta = math.degrees(math.atan2(wheelbase, inner_arm)) - outer
    if ideal_delta < ACKERMANN_MIN_IDEAL_DELTA_DEG:
        return 0.0
    return 100.0 * (inner - outer) / ideal_delta


_WHEELBASE = None


def _wheelbase() -> float:
    """Wheelbase (mm) from the template model's vehicle_config, as the report reads it."""
    global _WHEELBASE
    if _WHEELBASE is None:
        import yaml

        from .solve import model_path

        spec = yaml.safe_load(model_path().read_text()) or {}
        _WHEELBASE = float((spec.get("vehicle_config") or {}).get("wheelbase", 2240.0))
    return _WHEELBASE


def joint_force_score(solved):
    """
    0.75 x mean |F| + 0.25 x max |F| over the candidate axle's joints, in N.

    Every physical joint counts once per side per case: a ball joint appears on
    both parts it connects, and is read from one of them. The tyre contact load
    is an applied force, not a joint, and is left out. Only the axle being
    optimised is scored; the other axle is fixed, so its joints would add a
    constant to the mean and could pin the max at a value no candidate moves.
    Weights come from FORCE_WEIGHTS in optimizer.py.
    """
    import optimizer
    from kinematics.core.loads.results import disambiguate_part_names

    run, axle = solved
    names = disambiguate_part_names(
        {
            (corner.axle.value, body.base_name): ""
            for corner in run.corners
            for body in corner.subsystem.bodies
            if not body.is_ground
        }
    )
    own_parts = {name for (ax, _), name in names.items() if ax == axle}

    magnitudes = {}
    for block in run.solution.blocks:
        if block.part not in own_parts:
            continue
        for row in block.rows:
            for load in row.loads:
                if load.applied:
                    continue
                key = (row.case, row.side, load.name)
                magnitudes[key] = float(np.linalg.norm(load.force))
    if not magnitudes:
        raise ValueError(f"force solve returned no joints for the {axle} axle")

    forces = np.fromiter(magnitudes.values(), float)
    weights = getattr(optimizer, "FORCE_WEIGHTS", {"mean": 0.75, "max": 0.25})
    return weights["mean"] * forces.mean() + weights["max"] * forces.max()


def travel_integral(
    analysis, key: str, bump_weight: float = 1.5, sweep_name=""
) -> float:
    frames = usable_frames(analysis, sweep_name)
    travel = np.array(
        [list(f.corner_metrics.values())[0]["wheel_travel"] for f in frames]
    )
    value = np.array([list(f.corner_metrics.values())[0][key] for f in frames])

    order = np.argsort(travel)
    travel, value = travel[order], value[order]

    design = float(list(analysis.references["setup"].corner_metrics.values())[0][key])
    weight = np.where(travel >= 0.0, bump_weight, 1.0)

    integral = float(np.trapezoid(np.abs(value - design) * weight, travel))
    span = travel[-1] - travel[0]
    return integral / span if span > 0 else 0.0


def reduce_outcomes(analyses, objectives_cfg, constraints_cfg, bump_weight):
    outcomes = {}

    for obj_name, (sweep_name, metric, sense) in objectives_cfg.items():
        if sweep_name not in analyses:
            continue
        analysis = analyses[sweep_name]

        if metric == "joint_force":
            outcomes[obj_name] = joint_force_score(analysis)
        elif metric == "bump_steer":
            outcomes[obj_name] = travel_integral(
                analysis, "toe_angle", bump_weight, sweep_name
            )
        elif metric == "bump_scrub":
            outcomes[obj_name] = travel_integral(
                analysis, "half_track", bump_weight, sweep_name
            )
        else:
            try:
                outcomes[obj_name] = float(
                    list(analysis.references["setup"].corner_metrics.values())[0][
                        metric
                    ]
                )
            except KeyError:
                outcomes[obj_name] = float(analysis.references["setup"].metrics[metric])

    for const_name, (sweep_name, metric, bounds) in constraints_cfg.items():
        if sweep_name not in analyses:
            continue
        analysis = analyses[sweep_name]

        if metric == "ackermann":
            # Resolved outside the try: if too little of the sweep solved, that
            # must reach the caller as an infeasible candidate, not be caught
            # below and turned into a score.
            frames = usable_frames(analysis, sweep_name)
            try:
                # Both locks, and the worse one is what the constraint sees.
                pcts = [ackermann_percent(f) for f in (frames[0], frames[-1])]
                outcomes[const_name] = max(pcts, key=lambda p: abs(p - 100.0))
            except Exception as e:
                import traceback

                print(f"ACKERMANN ERROR: {e}")
                traceback.print_exc()
                outcomes[const_name] = 0.0

        elif metric == "motion_ratio":
            # Damper/wheel at design height, defined exactly as the report
            # defines it: MR = -d(damper length)/d(wheel centre z).
            setup = analysis.references["setup"].corner_metrics
            outcomes[const_name] = -float(
                setup["left"]["deriv_damper_length_wrt_hub_z"]
            )

        elif metric == "max_turn":
            toes = [
                list(f.corner_metrics.values())[0]["toe_angle"]
                for f in usable_frames(analysis, sweep_name)
            ]
            outcomes[const_name] = min(abs(max(toes)), abs(min(toes)))

        else:
            try:
                outcomes[const_name] = float(
                    list(analysis.references["setup"].corner_metrics.values())[0][
                        metric
                    ]
                )
            except KeyError:
                outcomes[const_name] = float(
                    analysis.references["setup"].metrics[metric]
                )

    return outcomes
