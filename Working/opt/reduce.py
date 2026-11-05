import math

import numpy as np
from .settings import current as current_settings

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


def worst_ackermann_percent(frames) -> float:
    """Ackermann % of whichever end of the steer sweep is furthest from 100%.

    The first and last frame are the two full locks, so this judges the design
    on both directions at once. Shared by the `ackermann` constraint metric and
    the `ackermann_error` objective, so the two can never disagree.
    """
    pcts = [ackermann_percent(f) for f in (frames[0], frames[-1])]
    return max(pcts, key=lambda p: abs(p - 100.0))


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
    settings = current_settings()
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
    weights = getattr(settings, "FORCE_WEIGHTS", {"mean": 0.75, "max": 0.25})
    return weights["mean"] * forces.mean() + weights["max"] * forces.max()


def _travel_ends(limits):
    """Wheel-travel extremes a SWEEP_LIMITS entry asks for, in either form.

    ``{"start", "stop"}`` gives them directly. The per-drive form gives them
    under ``travel`` as ``(a, b)`` or ``{side: (a, b)}``; the extremes over every
    side are what an extrapolation has to reach.
    """
    if "start" in limits or "stop" in limits:
        return [limits[k] for k in ("start", "stop") if k in limits]
    travel = limits.get("travel")
    if travel is None:
        return []
    spans = travel.values() if isinstance(travel, dict) else [travel]
    values = [float(v) for span in spans for v in span]
    return [min(values), max(values)] if values else []


def min_damper_length(analysis, sweep_name=""):
    """
    Shortest damper length (mm) over the sweep, both sides.

    Taken over every frame, not just the last one, so it still holds if the
    installation ratio changes sign somewhere in travel. If an end frame failed to
    solve and was dropped, the length is extrapolated linearly from the two
    nearest solved frames out to the travel SWEEP_LIMITS asked for, so a
    candidate cannot pass just because its full-bump frame did not solve.
    """
    settings = current_settings()
    frames = usable_frames(analysis, sweep_name)
    worst = math.inf
    ends = _travel_ends(getattr(settings, "SWEEP_LIMITS", {}).get(sweep_name, {}))

    for side in frames[0].corner_metrics:
        travel = np.array([f.corner_metrics[side]["wheel_travel"] for f in frames])
        length = np.array([f.corner_metrics[side]["damper_length"] for f in frames])
        order = np.argsort(travel)
        travel, length = travel[order], length[order]
        worst = min(worst, float(length.min()))

        for end in ends:
            if end > travel[-1] + 0.5:
                t, l = travel[-2:], length[-2:]
            elif end < travel[0] - 0.5:
                t, l = travel[:2], length[:2]
            else:
                continue
            slope = (l[1] - l[0]) / (t[1] - t[0])
            worst = min(worst, float(l[0] + slope * (end - t[0])))

    return worst


#: Cap on |camber gain| for a frame whose FVSA is exactly 0 (the instant centre
#: sitting on the contact patch), so one degenerate frame cannot make the
#: objective infinite. Real designs are orders of magnitude below this.
MAX_CAMBER_GAIN_DEG_PER_MM = 1.0e3


def camber_gain_curve(analysis, sweep_name=""):
    """
    Camber gain R = 1/FVSA (deg/mm) at every usable frame, for every corner.

    1/FVSA is the camber change per mm of wheel travel at that pose - checked
    against the measured slope of the camber curve to within ~4 % on the
    Oct 2026 Pareto designs. It is used instead of FVSA itself because FVSA
    passes through +/-infinity wherever the arms are parallel and flips sign
    there, while 1/FVSA passes smoothly through zero.

    Sign follows the solver's FVSA: positive = instant centre INBOARD of the
    contact centre. A frame with no instant centre (arms exactly parallel, so
    FVSA is undefined) is infinite FVSA, i.e. R = 0 - not a failure.

    Returns:
        (travel, {side: R}) with travel sorted ascending, in mm.
    """
    frames = usable_frames(analysis, sweep_name)
    sides = list(frames[0].corner_metrics)
    travel = np.array([f.corner_metrics[sides[0]]["wheel_travel"] for f in frames])
    order = np.argsort(travel)

    def gain(fvsa):
        if fvsa is None or not math.isfinite(fvsa):
            return 0.0
        if fvsa == 0.0:
            return MAX_CAMBER_GAIN_DEG_PER_MM
        return math.degrees(1.0 / fvsa)

    curves = {
        side: np.array([gain(f.corner_metrics[side].get("fvsa_length"))
                        for f in frames])[order]
        for side in sides
    }
    return travel[order], curves


def camber_gain_score(analysis, bump_weight, sweep_name=""):
    """
    Bump-weighted mean |camber gain| over the sweep, deg/mm (minimise).

        (1 / span) * integral of w(z) * |1/FVSA(z)| dz,   w = bump_weight for z >= 0

    The same shape as `bump_scrub`, applied to the camber gain at every pose
    instead of FVSA at the design pose alone. Read from the first corner, as
    the other bump-sweep objectives are.
    """
    travel, curves = camber_gain_curve(analysis, sweep_name)
    gain = np.abs(next(iter(curves.values())))
    weight = np.where(travel >= 0.0, bump_weight, 1.0)
    span = travel[-1] - travel[0]
    return float(np.trapezoid(gain * weight, travel)) / span if span > 0 else 0.0


def min_camber_gain(analysis, sweep_name=""):
    """
    Smallest camber gain R = 1/FVSA (deg/mm) at any frame, either corner.

    R >= 0 at every frame means the front-view instant centre is inboard (or
    at infinity) throughout the travel, not just at design height. Negative
    means it crossed outboard somewhere - the parallel-arm designs whose
    camber curve humps negative in both bump and droop.
    """
    _, curves = camber_gain_curve(analysis, sweep_name)
    return float(min(curve.min() for curve in curves.values()))


def _corner_sides(frames):
    """Return (outer, inner) side names for a cornering sweep.

    Which wheel is outer is a property of the TURN: ISO steer is positive for a
    left turn, whose outer wheel is the right. Read at the frame of largest
    mean steer, so the near-centre frames of a ramp, where the sign is noise,
    cannot flip it. Same rule as the report (susreport._add_corner_roles), so
    the objective scores the wheel the report labels outer.

    Raises:
        ValueError: if the rack never moves (no turn), or if the outer wheel is
            in droop at that frame - the sweep is rolled the wrong way for its
            steer, so it is a transient, not a corner, and scoring it would
            push the design the wrong way. This is a run.yaml mistake, not a
            property of the candidate, so it fails every candidate the same.
    """
    mean = [0.5 * (f.corner_metrics["left"]["steer_angle"]
                   + f.corner_metrics["right"]["steer_angle"]) for f in frames]
    at = int(np.argmax(np.abs(mean)))
    if abs(mean[at]) < 1e-6:
        raise ValueError("road_camber needs a steered sweep: the rack never moves")
    outer, inner = ("right", "left") if mean[at] > 0.0 else ("left", "right")
    if frames[at].corner_metrics[outer]["wheel_travel"] < -1e-6:
        raise ValueError(
            f"road_camber: the sweep turns towards the {inner} but the {outer} "
            "(outer) wheel is in droop - it is rolled the wrong way for its "
            "steer. Flip its travel signs in run.yaml."
        )
    return outer, inner


def _weighted_mean_square(x, err, positive_weight=1.0):
    """(1/span) * integral of w(err) * err^2 dx, w = positive_weight where err > 0.

    The weight steps where err changes sign, so the crossings (err linear
    between frames) are inserted as samples first: no trapezoid straddles the
    step, and the score does not depend on where the frames happen to fall.
    err = 0 at a crossing, so its weight there is irrelevant.
    """
    order = np.argsort(x)
    x, err = x[order], err[order]
    span = x[-1] - x[0]
    if positive_weight != 1.0:
        flip = np.nonzero(err[:-1] * err[1:] < 0.0)[0]
        if flip.size:
            x_cross = x[flip] - err[flip] * (x[flip + 1] - x[flip]) / (
                err[flip + 1] - err[flip])
            x = np.insert(x, flip + 1, x_cross)
            err = np.insert(err, flip + 1, 0.0)
    w = np.where(err > 0.0, positive_weight, 1.0)
    sq = w * err ** 2
    if span <= 0:
        return float(sq.mean())
    return float(np.trapezoid(sq, x)) / span


def road_camber_score(analysis, bump_weight, target=0.0, sweep_name="",
                      inner_positive_weight=1.0):
    """
    Weighted RMS road camber over a cornering sweep, deg (minimise).

    For each wheel, the mean square of its deviation from ``target`` over the
    sweep:

        ms = (1 / span) * integral of (road_camber(x) - target)^2 dx

    On the INNER wheel, the part of the curve above the target (more positive
    camber, top out) is multiplied by ``inner_positive_weight``, so the
    optimiser prefers to miss on the negative side: the goal on that wheel is
    small negative camber, and a positive miss costs more than a negative one
    of the same size. 1 = symmetric (the old score). The minimum is still at the
    target; this changes which way a candidate that cannot reach it is pushed.

    where x is that wheel's own vertical travel - or the rack, in a sweep that
    holds the wheels still (09). Squared so a positive and a negative region
    cannot cancel; normalised by the span so the score does not change scale
    when the sweep's endpoints or step count change. In 10_corner_ramp travel
    and rack ramp together linearly, so the two abscissae give the same number.

    The wheels are then combined with the outer (loaded, in-bump) wheel
    weighted ``bump_weight`` and the inner wheel 1, and divided by the total
    weight, so the result is still a mean square; its square root is returned
    to read in degrees. The root is monotonic, so the Pareto front is the
    same either way.

    road_camber is ISO 8855 inclination signed like camber - see
    kinematics.core.metrics.steering_geometry.calculate_road_camber.
    """
    frames = usable_frames(analysis, sweep_name)
    outer, inner = _corner_sides(frames)

    def mean_square(side, positive_weight=1.0):
        x = np.array([f.corner_metrics[side]["wheel_travel"] for f in frames])
        if np.ptp(x) < 1e-6:
            x = np.array([f.metrics["rack_displacement"] for f in frames])
        y = np.array([f.corner_metrics[side]["road_camber"] for f in frames])
        return _weighted_mean_square(x, y - target, positive_weight)

    weighted = (bump_weight * mean_square(outer)
                + mean_square(inner, inner_positive_weight))
    return math.sqrt(weighted / (bump_weight + 1.0))


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
        elif metric == "ackermann_error":
            # |Ackermann % - 100| on the worse lock, percentage points. A frame
            # too close to centre to measure reads 0 %, so it scores 100 rather
            # than looking perfect. Errors are not swallowed here: a candidate
            # whose Ackermann cannot be read is reported as failed, not scored.
            frames = usable_frames(analysis, sweep_name)
            outcomes[obj_name] = abs(worst_ackermann_percent(frames) - 100.0)
        elif metric == "bump_steer":
            outcomes[obj_name] = travel_integral(
                analysis, "toe_angle", bump_weight, sweep_name
            )
        elif metric == "bump_scrub":
            outcomes[obj_name] = travel_integral(
                analysis, "half_track", bump_weight, sweep_name
            )
        elif metric == "road_camber":
            settings = current_settings()
            outcomes[obj_name] = road_camber_score(
                analysis,
                getattr(settings, "ROAD_CAMBER_BUMP_WEIGHTING", 4.0),
                getattr(settings, "ROAD_CAMBER_TARGET", 0.0),
                sweep_name,
                # 1 (symmetric) for a script that predates it.
                getattr(settings, "ROAD_CAMBER_INNER_POSITIVE_WEIGHTING", 1.0),
            )
        elif metric == "camber_gain":
            # Its own bump weight, so camber and scrub can be tuned apart.
            # Falls back to BUMP_WEIGHTING for a script that predates it.
            weight = getattr(current_settings(), "CAMBER_BUMP_WEIGHTING", bump_weight)
            outcomes[obj_name] = camber_gain_score(analysis, weight, sweep_name)
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
                outcomes[const_name] = worst_ackermann_percent(frames)
            except Exception as e:
                import traceback

                print(f"ACKERMANN ERROR: {e}")
                traceback.print_exc()
                outcomes[const_name] = 0.0

        elif metric in ("install_ratio", "motion_ratio"):
            # Instantaneous, at design height, defined exactly as the report
            # defines them:
            #   IR = damper/wheel = -d(damper length)/d(wheel centre z)
            #   MR = wheel/damper = 1 / IR
            setup = analysis.references["setup"].corner_metrics
            ir = -float(setup["left"]["deriv_damper_length_wrt_hub_z"])
            if metric == "install_ratio":
                outcomes[const_name] = ir
            else:
                outcomes[const_name] = 1.0 / ir if abs(ir) > 1e-9 else math.inf

        elif metric == "toe_range":
            # Toe max - min over the sweep, deg, worse side: the same number
            # as the report's toe "range" column.
            frames = usable_frames(analysis, sweep_name)
            outcomes[const_name] = max(
                float(np.ptp([f.corner_metrics[side]["toe_angle"] for f in frames]))
                for side in frames[0].corner_metrics
            )

        elif metric == "min_damper_length":
            outcomes[const_name] = min_damper_length(analysis, sweep_name)

        elif metric == "min_camber_gain":
            outcomes[const_name] = min_camber_gain(analysis, sweep_name)

        elif metric == "max_turn":
            toes = [
                list(f.corner_metrics.values())[0]["toe_angle"]
                for f in usable_frames(analysis, sweep_name)
            ]
            outcomes[const_name] = min(abs(max(toes)), abs(min(toes)))

        elif metric == "fvsa_length":
            # Arms parallel within the solver's tolerance leave no instant
            # centre and the metric reads None: that is an infinitely long
            # swing arm, which passes a minimum-length bound. Previously
            # float(None) raised and the candidate was thrown out as failed.
            value = list(analysis.references["setup"].corner_metrics.values())[0][metric]
            outcomes[const_name] = math.inf if value is None else float(value)

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
