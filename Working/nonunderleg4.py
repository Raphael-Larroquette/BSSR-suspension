from opt.construct import (strut_bottom_fractions, strut_bottom_point,
                           trackrod_inboard_yz)
from opt.evaluate import run_optimization
import math
# TO RUN:     uv run python Working/nonunderleg4.py
#             -> Working/models/opt_<timestamp>/opt_<timestamp>.csv (the Pareto front)
# EXPORT:     uv run python Working/export_pareto.py [opt_<timestamp>]
#             -> opt_<timestamp>/pareto1, pareto2, ... (default: the latest run)
# SOLVE ALL:  uv run python Working/run_all.py --batch opt_<timestamp> --sets front --only 01 --no-forces
# SOLVE one: uv run python Working/run_all.py --model opt_,timestamp/pareto## --only 01 --no-forces
# CHECK SEED: uv run python Working/check_design.py Working/nonunderleg4.py
#
# CHANGES FROM nonunderleg3.py: a fifth objective, `road_camber`, read from
# 10_corner_ramp - see ROAD_CAMBER_* below and OBJECTIVES. Everything else is
# identical, so a front from 3 and a front from 4 differ only by that objective.
#
# This file IS the run's configuration. Copy it to make a variant: whichever
# script you launch is the one used (see opt/settings.py).

# ---------------------------------------------------------------------------
# References. Everything this run reads is named here; nothing in opt/ names a
# file of its own. Paths are relative to Working/ (or absolute).
# ---------------------------------------------------------------------------
# Template model folder: any folder with front.yaml, rear.yaml and forces.yaml -
# a car in models/, or a candidate from a previous run such as
# "models/opt_2026-10-02_1430/pareto21". Candidates are patched into its
# <AXLE>.yaml; the other axle and the force config come from the same folder.
# The tyre radius and wheel offset are read from it too.
TEMPLATE = "models/aurora"
AXLE = "front"                              # the axle being optimised
SWEEP_SET = "sweep_sets/front/run.yaml"     # which sweeps the objectives read
CASES = "cases.csv"                         # load cases for the joint_force objective

# Design rules derive_parameters() builds every candidate with.
TRACK_WIDTH = 985.0          # mm, contact patch to contact patch
CASTER_DEG = 7.0              # deg
MIN_ARM_SEPARATION = 200.0    # mm, minimum vertical gap UCA above LCA (inboard and outboard)

# Search size.
# NSGA-III reference directions by objective count (opt/problem.py): 4 -> 165,
# 5 -> 210. Keep the population at or above that; 1320 covers 5 objectives.
POPULATION_SIZE = 1320   # max workers is 60 on python in windows
GENERATIONS = 400

# Worker processes. None = one per logical CPU (128 on the 64-core machine).
# Windows caps one process pool at 60 workers, so they are split into as few
# pools as that allows (128 -> 3 pools of 43, 43, 42) - see opt/problem.py.
# Try 64 (one per physical core) vs None and keep whichever is faster per
# generation. Each worker holds ~200 MB of RAM.
POOL_WORKERS = None
# Largest pool. None = 60 on Windows (its limit), everything in one pool
# elsewhere. Only lower it to test multi-pool behaviour on a small machine.
WORKERS_PER_POOL = None

# Bump-side multiplier inside the travel integrals (droop counts 1x).
BUMP_WEIGHTING = 1.5          # bump_scrub
CAMBER_BUMP_WEIGHTING = 2.0   # camber_gain

# road_camber objective (10_corner_ramp). The outer wheel - in bump, carrying
# the load - counts ROAD_CAMBER_BUMP_WEIGHTING x, the inner (droop) wheel 1x.
# ROAD_CAMBER_TARGET is the road camber the objective pulls both wheels to, deg,
# signed like camber (negative = top in). 0 = upright on the road. Some tyres
# grip best slightly negative on the loaded wheel; change it once you know.
ROAD_CAMBER_BUMP_WEIGHTING = 4.0
ROAD_CAMBER_TARGET = 0.0

# Shortest the shock may ever be, eye to eye, in mm. Checked twice with this
# one number: before solving (design length, free - a shock already too short
# at design height can only get shorter in the sweep) and after (the whole bump
# sweep). Set it to the chosen shock's fully compressed length plus any
# bump-stop margin. Placeholder until a shock is chosen. None turns it off.
MIN_SHOCK_LENGTH = 200.0

# True prints why each failed candidate failed. Off, each generation prints
# only how many failed - most failures are ordinary kinematic lock-outs.
VERBOSE_FAILURES = False

# Two forms (opt/solve.py):
#   {"start": a, "stop": b}   one span for a sweep that moves ONE kind of drive.
#                             Refused on a sweep that moves several (09, 10).
#   {"travel": ..., "damper": ..., "rack": ...}
#                             per drive, in run.yaml's own vocabulary, merged
#                             over run.yaml's entry. Any subset; the rest keep
#                             run.yaml's values. A side mapping merges per side.
SWEEP_LIMITS = {
    "01_bump_parallel": {"start": -50.8, "stop": 50.8},
    "04_steer_design": {"start": -35.0, "stop": 35.0},
    # Right turn: rack +y steers right, so the LEFT wheel is outer, in bump.
    # Currently the same as run.yaml (placeholder until set from the roll
    # gradient); stated here so the corner this run judged is in the script.
    "10_corner_ramp": {
        "travel": {"left": (0.0, 25.0), "right": (0.0, -25.0)},
        "rack": (0.0, 35.0),
    },
}

# Steps the OPTIMISER solves each sweep at. run.yaml's own counts (22 and 65)
# are what the reports use; the search reads far fewer frames than it solves.
#   01_bump_parallel  `bump_scrub` integrates this curve, and `toe_range` and
#                     `shock_length` read its extremes, so it needs real
#                     resolution. 11 costs ~0.3% on the integrals, uniform
#                     across candidates so rankings are unaffected. Below 9 the
#                     trapezoid error starts to matter.
#   04_steer_design   only `ackermann_error` (both full locks) and `max_turn`
#                     (the two extremes) are read, and steer is monotonic in
#                     rack travel, so 3 frames capture both locks exactly -
#                     measured identical to 4 decimals against 65.
#                     WARNING: add an objective that reads the SHAPE of the
#                     steer curve and this must go back up.
#   10_corner_ramp    `road_camber` integrates the whole road-camber curve of
#                     both wheels, so like 01 it needs real resolution.
SWEEP_STEPS = {
    "01_bump_parallel": 13,
    "04_steer_design": 3,
    "10_corner_ramp": 13,
}

FREE_PARAMETERS = {
    "lower_wishbone_outboard.y": (400.0, 468.763), # inside of half track - wheel offset
    "lower_wishbone_outboard.z": (77.0, 200.0),
    "upper_wishbone_outboard.z_frac": (0.0, 1.0),
    "lower_wishbone_inboard.y_frac": (0.0, 1.0), # driver ergo, 5 deg draft angle chassis function
    "lower_wishbone_inboard.z": (118.6, 350), # lower is 77mm ride hight + BAB thickness + 1 inch 
    "upper_wishbone_inboard.y_frac": (0.0, 1.0),
    "upper_wishbone_inboard.z_frac": (0.0, 1.0),  # Fractional span ensures safety
    "trackrod_outboard.x": (-250.0, -50.0), # behind caster 
    "trackrod_outboard.z": (400.0, 550.0), # below top of wheel + margin
    "trackrod_outboard.y": (300.0, 435.0),
    "trackrod_inboard.x": (-150.0, -50.0), # Assume driver ergo nonfactor for track rod positions
    # trackrod_inboard y and z are not searched: they are calculated for zero
    # bump steer (opt/construct.py) and must land in TRACKROD_INBOARD_LIMITS.
    # Inboard pivot x, absolute. Front and rear ranges never overlap, so the
    # front pivot is always ahead of the rear one by at least 50 mm.
    "lower_wishbone_inboard_front.x": (0, 300.0), # underleg area, assume all inboard front hardpoints must be in front of the wheel center
    "lower_wishbone_inboard_rear.x": (-300.0, -5.0), 
    "upper_wishbone_inboard_front.x": (0.0, 200.0),
    "upper_wishbone_inboard_rear.x": (-250.0, -5.0),
    # Spring mounts at design height, see opt/construct.py.
    # LCA mount: inside the LCA triangle in plan, `height` mm straight up from
    # the LCA plane. u: 0 = ball joint, 1 = inboard pivot axis (area-uniform).
    # v: 0 = front pivot side, 1 = rear pivot side.
    "strut_bottom.u_frac": (0.08, 1.0),
    "strut_bottom.v_frac": (0.0, 1.0),
    "strut_bottom.height": (10.0, 50.0),
    # Chassis mount: same x as the LCA mount, y and z absolute. z starts at
    # 275 so it is always above the highest possible LCA mount (200 + 50).
    "strut_top.y_frac": (0.0, 1.0), # outside driver compartment but not too offset from chassis   
    "strut_top.z": (275.0, 490.0), # needs to be less than the UCA height TODO
}

# Packaging window for the calculated inner tie rod point (rack end), mm. A
# candidate whose zero-bump-steer point falls outside is rejected before solving.
TRACKROD_INBOARD_LIMITS = {
    "y": (142.875, 340.0),
    "z": (470.0, 600.0), # set this above the chassis roof height
}

KNOWN_DESIGN = {
    "lower_wishbone_outboard.y": 476.136,
    "lower_wishbone_outboard.z": 137.151,
    "upper_wishbone_outboard.z": 437.0,
    "lower_wishbone_inboard.y": 295.84,
    "lower_wishbone_inboard.z": 136.358,
    "upper_wishbone_inboard.y": 269.174,
    "upper_wishbone_inboard.z": 422.12,
    "trackrod_outboard.x": -128.565,
    "trackrod_outboard.z": 524.387,
    "trackrod_outboard.y": 408.764,   # was 407.4: 32% Ackermann; 394.5 gives 95%
    "trackrod_inboard.x": -187.077,
    # Previously derived as outboard x +/- 50, kept so the seed is unchanged.
    "lower_wishbone_inboard_front.x": 104.876,
    "lower_wishbone_inboard_rear.x": -143.639,
    "upper_wishbone_inboard_front.x": 71.414,
    "upper_wishbone_inboard_rear.x": -111.03,
    # Absolute spring mounts; converted to strut_bottom u/v/height and
    # strut_top y/z by resolve_spring_seed(). Chosen inside the current ranges
    # (u_frac 0.153) so the seed passes every constraint: install ratio 0.635 (MR 1.57),
    # 252 mm at full bump, joint_force 4200 N. The old mounts (10.43, 365.75,
    # 341.13) / (10.43, 443.12, 166.76) gave IR 0.80 (MR 1.25) but sit at u_frac 0.033.
    "strut_top": (19.45, 330.367, 454.21),
    "strut_bottom": (3.155, 370.985, 186.049), # change? how was this and the one above calculated? not underchassis
}

#: The force objective: this share of the mean joint force plus the rest of the
#: largest one. Both are |F| in N over every front joint and every load case in
#: <TEMPLATE>/forces.yaml, over the cases in CASES.
FORCE_WEIGHTS = {"mean": 0.75, "max": 0.25}


def wishbone_triangles(derived):
    """LCA and UCA hardpoint triangles, each (inboard front, inboard rear, ball joint)."""
    def xyz(name):
        return [derived[f"{name}.{a}"] for a in "xyz"]

    return tuple(
        [xyz(f"{arm}_wishbone_inboard_front"),
         xyz(f"{arm}_wishbone_inboard_rear"),
         xyz(f"{arm}_wishbone_outboard")]
        for arm in ("lower", "upper")
    )


def derive_parameters(free, fixed):
    p = dict(free)
    derived = {}

    half_track = fixed["track_width"] / 2.0
    tan_caster = math.tan(math.radians(fixed["caster_deg"]))

    # === OUTBOARD Z ORDERING ===
    lca_z = p["lower_wishbone_outboard.z"]
    uca_z_min = lca_z + fixed["min_outboard_separation"]
    uca_z_max = uca_z_min + 200.0
    uca_z = uca_z_min + p["upper_wishbone_outboard.z_frac"] * (uca_z_max - uca_z_min)

    # === INBOARD Z ORDERING ===
    # UCA inboard must be higher than both LCA inboard AND LCA outboard.
    lca_in_z = p.get("lower_wishbone_inboard.z", 185.0)
    uca_in_z_min = max(lca_z, lca_in_z) + fixed["min_outboard_separation"]
    uca_in_z_max = uca_in_z_min + 200.0
    uca_in_z = uca_in_z_min + p.get("upper_wishbone_inboard.z_frac", 0.5) * (
        uca_in_z_max - uca_in_z_min
    )

    # === CHASSIS Y CALCULATIONS ===
    def chassis_y(z):
        return 260.0 + (473.143 - z) * math.tan(math.radians(5.0))

    # Calculate LCA Inboard Y
    lca_in_y_min = chassis_y(lca_in_z)
    lca_in_y = lca_in_y_min + p.get("lower_wishbone_inboard.y_frac", 0.5) * 75.0

    # Calculate UCA Inboard Y with reverting bounds
    if uca_in_z > 473.143:
        uca_in_y_min, uca_in_y_span = 295.0, 75.0
    else:
        uca_in_y_min, uca_in_y_span = chassis_y(uca_in_z), 300.0
    uca_in_y = uca_in_y_min + p.get("upper_wishbone_inboard.y_frac", 0.5) * uca_in_y_span

    # === MAP INBOARD POINTS TO FRONT & REAR ===
    derived["lower_wishbone_inboard_front.y"] = lca_in_y
    derived["lower_wishbone_inboard_rear.y"] = lca_in_y
    derived["lower_wishbone_inboard_front.z"] = lca_in_z
    derived["lower_wishbone_inboard_rear.z"] = lca_in_z

    derived["upper_wishbone_inboard_front.y"] = uca_in_y
    derived["upper_wishbone_inboard_rear.y"] = uca_in_y
    derived["upper_wishbone_inboard_front.z"] = uca_in_z
    derived["upper_wishbone_inboard_rear.z"] = uca_in_z

    # Scrub / Caster Enforcements
    kpi = math.atan2(half_track - p["lower_wishbone_outboard.y"], lca_z)

    def y_at(z):
        return half_track - z * math.tan(kpi)

    def x_at(z):
        return (fixed["rolling_radius"] - z) * tan_caster

    derived["lower_wishbone_outboard.x"] = x_at(lca_z)
    derived["lower_wishbone_outboard.y"] = p["lower_wishbone_outboard.y"]
    derived["lower_wishbone_outboard.z"] = lca_z

    derived["upper_wishbone_outboard.x"] = x_at(uca_z)
    derived["upper_wishbone_outboard.y"] = y_at(uca_z)
    derived["upper_wishbone_outboard.z"] = uca_z

    derived["axle_outboard.x"] = 0.0
    derived["axle_outboard.y"] = half_track + fixed["wheel_offset"]
    derived["axle_outboard.z"] = fixed["rolling_radius"]

    derived["axle_inboard.x"] = 0.0
    derived["axle_inboard.y"] = half_track + fixed["wheel_offset"] - 100.0
    derived["axle_inboard.z"] = fixed["rolling_radius"]

    # Inner tie rod y, z: calculated for zero bump steer over the bump sweep's
    # travel. x stays a free parameter (it doesn't affect front-view motion).
    def xyz(name):
        return [derived.get(f"{name}.{a}", 0.0) for a in "xyz"]

    bump = SWEEP_LIMITS["01_bump_parallel"]
    trackrod_out = [p["trackrod_outboard.x"], p["trackrod_outboard.y"],
                    p["trackrod_outboard.z"]]
    inner_y, inner_z = trackrod_inboard_yz(
        [0.0, lca_in_y, lca_in_z], xyz("lower_wishbone_outboard"),
        [0.0, uca_in_y, uca_in_z], xyz("upper_wishbone_outboard"),
        trackrod_out, xyz("axle_outboard"),
        (min(bump["start"], bump["stop"]), max(bump["start"], bump["stop"])),
    )
    derived["trackrod_inboard.x"] = p["trackrod_inboard.x"]
    derived["trackrod_inboard.y"] = float(inner_y)
    derived["trackrod_inboard.z"] = float(inner_z)

    # Inboard pivot x: free parameters, one per pivot.
    for arm in ("lower", "upper"):
        for end in ("front", "rear"):
            key = f"{arm}_wishbone_inboard_{end}.x"
            derived[key] = p[key]

    # Spring mounts: LCA mount above the LCA triangle, chassis mount at its x.
    lca, _ = wishbone_triangles(derived)
    bottom = strut_bottom_point(
        lca, p["strut_bottom.u_frac"], p["strut_bottom.v_frac"],
        p["strut_bottom.height"],
    )
    for axis, value in zip("xyz", bottom):
        derived[f"strut_bottom.{axis}"] = float(value)
    derived["strut_top.x"] = float(bottom[0])
    
    # Map Strut Top Y to dynamic chassis
    strut_y_min = chassis_y(p["strut_top.z"])
    derived["strut_top.y"] = strut_y_min + p.get("strut_top.y_frac", 0.5) * 115.0
    derived["strut_top.z"] = p["strut_top.z"]

    # Anything else that is already a plain hardpoint coordinate passes
    # through; fractions and offsets (u_frac, height, ...) never do.
    for k, v in p.items():
        if (k not in derived and k.rsplit(".", 1)[-1] in ("x", "y", "z")
                and "wishbone_inboard" not in k and "strut_top.y" not in k):
            derived[k] = v

    return derived


OBJECTIVES = {
    # Camber gain 1/FVSA at EVERY frame of the bump sweep, not just design
    # height: (1/span) * integral of w(z)*|1/FVSA(z)| dz, deg/mm, with
    # w = CAMBER_BUMP_WEIGHTING in bump and 1 in droop. Minimising it is
    # "maximise FVSA everywhere, bump first". Replaces fvsa_length, which read
    # the design pose only - exactly where parallel arms make it infinite.
    "camber_gain": ("01_bump_parallel", "camber_gain", "minimize"),
    "bump_scrub": ("01_bump_parallel", "bump_scrub", "minimize"),
    # |Ackermann % - 100|, in percentage points, at full lock. Scored on
    # whichever lock is worse, so both directions have to be good. Replaces the
    # old 60-110% constraint: 100% is the target, not a band edge, so anti-
    # Ackermann (negative %) is penalised as hard as over-Ackermann.
    "ackermann_error": ("04_steer_design", "ackermann_error", "minimize"),
    # Weighted RMS road camber over the corner ramp, deg: per wheel the mean of
    # (road_camber - ROAD_CAMBER_TARGET)^2 over its travel, outer wheel x
    # ROAD_CAMBER_BUMP_WEIGHTING, inner x1, divided by the total weight, then
    # square-rooted. Road camber = ISO 8855 inclination signed like camber, so
    # steer camber (caster/KPI) and roll both count, as the tyre sees them.
    # Pulls against camber_gain: holding road camber in roll needs MORE camber
    # change in bump, camber_gain rewards less. That trade-off is the point.
    "road_camber": ("10_corner_ramp", "road_camber", "minimize"),
    # "forces" is not a sweep: it is the static force solve at design height.
    "joint_force": ("forces", "joint_force", "minimize"),
}

CONSTRAINTS = {
    "rc_height": ("01_bump_parallel", "roll_center_z", (0.0, 40.0)),
    # Toe max - min over the bump sweep, deg, worse side: the report's toe
    # "range" column. With the calculated inner tie rod this is normally
    # ~0.05-0.2 deg, so it only catches what the front-view model misses.
    "toe_range": ("01_bump_parallel", "toe_range", (0.0, 1.0)),
    "kingpin": ("01_bump_parallel", "kpi", (9.0, 11.0)),
    "max_turn": ("04_steer_design", "max_turn", (20.0, 40.0)),
    # FVSA is signed (+ = instant centre inboard), so this is "inboard and at
    # least 1 m away" - at the design pose only.
    "fvsa_sign": ("01_bump_parallel", "fvsa_length", (1000.0, None)),
    # Sweep-wide version (inboard at every frame), not yet chosen:
    # "fvsa_inboard": ("01_bump_parallel", "min_camber_gain", (0.0, None)),
    # Installation ratio = damper travel / wheel travel, instantaneous at design
    # height (IR 0.6-1.01 is MR = wheel/damper 0.99-1.67). Constrained on IR, not
    # MR, so a damper that stops moving (IR -> 0) fails cleanly instead of MR -> inf.
    "install_ratio": ("01_bump_parallel", "install_ratio", (0.6, 1.01)),
    # Shortest damper length anywhere in the bump sweep. See MIN_SHOCK_LENGTH.
    "shock_length": ("01_bump_parallel", "min_damper_length", (MIN_SHOCK_LENGTH, None)),
}
if MIN_SHOCK_LENGTH is None:
    del CONSTRAINTS["shock_length"]

# Auto-convert absolute Z coordinates in KNOWN_DESIGN to the z_frac required by the optimizer
min_sep = MIN_ARM_SEPARATION

if "upper_wishbone_outboard.z" in KNOWN_DESIGN:
    lca_z_seed = KNOWN_DESIGN.get("lower_wishbone_outboard.z", 185.0)
    uca_z = KNOWN_DESIGN.get("upper_wishbone_outboard.z")
    KNOWN_DESIGN["upper_wishbone_outboard.z_frac"] = (uca_z - (lca_z_seed + min_sep)) / 200.0

if "upper_wishbone_inboard.z" in KNOWN_DESIGN:
    lca_in_z_seed = KNOWN_DESIGN.get("lower_wishbone_inboard.z", 185.0)
    lca_z_seed = KNOWN_DESIGN.get("lower_wishbone_outboard.z", 185.0)
    uca_in_z = KNOWN_DESIGN.get("upper_wishbone_inboard.z")
    uca_in_z_min = max(lca_z_seed, lca_in_z_seed) + min_sep
    KNOWN_DESIGN["upper_wishbone_inboard.z_frac"] = (uca_in_z - uca_in_z_min) / 200.0

def calc_chassis_y(z):
    return 260.0 + (473.143 - z) * math.tan(math.radians(5.0))

if "lower_wishbone_inboard.y" in KNOWN_DESIGN:
    lca_z_seed = KNOWN_DESIGN.get("lower_wishbone_inboard.z", 185.0)
    KNOWN_DESIGN["lower_wishbone_inboard.y_frac"] = (KNOWN_DESIGN.pop("lower_wishbone_inboard.y") - calc_chassis_y(lca_z_seed)) / 75.0

if "upper_wishbone_inboard.y" in KNOWN_DESIGN:
    uca_z_seed = KNOWN_DESIGN.get("upper_wishbone_inboard.z")
    y_seed = KNOWN_DESIGN.pop("upper_wishbone_inboard.y")
    y_min, span = (295.0, 75.0) if uca_z_seed > 473.143 else (calc_chassis_y(uca_z_seed), 300.0)
    KNOWN_DESIGN["upper_wishbone_inboard.y_frac"] = (y_seed - y_min) / span


def resolve_spring_seed(fixed):
    """
    Turn KNOWN_DESIGN's absolute spring mounts into free parameters, in place.
    """
    if "strut_top" not in KNOWN_DESIGN:
        return
    top = KNOWN_DESIGN.pop("strut_top")
    bottom = KNOWN_DESIGN.pop("strut_bottom")
    trial = dict(KNOWN_DESIGN)
    trial.update({"strut_bottom.u_frac": 0.5, "strut_bottom.v_frac": 0.5,
                  "strut_bottom.height": 0.0, "strut_top.y_frac": 0.5,
                  "strut_top.z": top[2]})
    lca, _ = wishbone_triangles(derive_parameters(trial, fixed))
    u, v, height, miss = strut_bottom_fractions(lca, bottom)
    
    st_z = float(top[2])
    st_y_min = calc_chassis_y(st_z)
    
    KNOWN_DESIGN.update({"strut_bottom.u_frac": u, "strut_bottom.v_frac": v,
                         "strut_bottom.height": height,
                         "strut_top.y_frac": (float(top[1]) - st_y_min) / 115.0,
                         "strut_top.z": st_z})
    
    if miss > 0.5:
        print(f"KNOWN_DESIGN LCA spring mount is outside the LCA triangle in "
              f"plan; seeding {miss:.1f} mm away, on its edge")
    if abs(top[0] - bottom[0]) > 0.5:
        print(f"KNOWN_DESIGN spring mounts differ in x by "
              f"{top[0] - bottom[0]:.1f} mm; the chassis mount is moved to "
              f"the LCA mount's x")
    for name in ("strut_bottom.u_frac", "strut_bottom.v_frac",
                 "strut_bottom.height", "strut_top.y_frac", "strut_top.z"):
        lo, hi = FREE_PARAMETERS[name]
        if not lo <= KNOWN_DESIGN[name] <= hi:
            print(f"KNOWN_DESIGN {name} = {KNOWN_DESIGN[name]:.2f} is outside "
                  f"its range ({lo}, {hi})")


if __name__ == "__main__":
    run_optimization(__file__)