from opt.evaluate import run_optimization
#TO RUN: type uv run python Working/optimizer.py into terminal
#Once done, run uv run python Working/export_pareto.py to export them to yamls
#to solve, type uv run python Working/run_all.py --sets front --geometry "C:\Users\alexz\Downloads\BSSR-suspension\Working\models\pareto1\front.yaml" --only 01 --no-forces
CAR_NAME = "aurora"
POPULATION_SIZE = 120   # 2 full waves of 60 workers, and == ref_dirs
GENERATIONS = 120

POOL_WORKERS = None

BUMP_WEIGHTING = 1.5

SWEEP_LIMITS = {
    "01_bump_parallel": {"start": -20.0, "stop": 20.0},
    "04_steer_design": {"start": -35.0, "stop": 35.0},
}

SWEEP_STEPS = {
    "01_bump_parallel": 11, #must be odd, minimize to start with (go no lower than 9) then add more steps for refinement.
    "04_steer_design": 3, #temp 3 steps only, increase number of steps if analyzing characteristics of full sweep.
}

FREE_PARAMETERS = {
    "lower_wishbone_outboard.y": (380.0, 550.0),
    "lower_wishbone_outboard.z": (100, 200.0),
    "upper_wishbone_outboard.z_frac": (0.0, 1.0),
    "lower_wishbone_inboard.y": (0.0, 320.0),
    "lower_wishbone_inboard.z": (117.5, 200.0),
    "upper_wishbone_inboard.y": (0.0, 340.0),
    "upper_wishbone_inboard.z_frac": (0.0, 1.0),  # Fractional span ensures safety
    "trackrod_outboard.x": (-150.0, -100.0),
    "trackrod_outboard.z": (450.0, 560.0),
    "trackrod_outboard.y": (380.0, 480.0),
    "trackrod_inboard.x": (-150.0, -100.0),
    "trackrod_inboard.z": (450.0, 560.0),
    "trackrod_inboard.y": (280.0, 340.0),
}

KNOWN_DESIGN = {
    "lower_wishbone_outboard.y": 475.84,
    "lower_wishbone_outboard.z": 137,
    "upper_wishbone_outboard.z": 437,
    "lower_wishbone_inboard.y": 295.84,
    "lower_wishbone_inboard.z": 137,
    "upper_wishbone_inboard.y": 314.95,
    "upper_wishbone_inboard.z": 422.12,
    "trackrod_outboard.x": -119.83,
    "trackrod_outboard.z": 525.2,
    "trackrod_outboard.y": 407.4,
    "trackrod_inboard.x": -130,
    "trackrod_inboard.z": 516.2,
    "trackrod_inboard.y": 320.7,
}


def derive_parameters(free, fixed):
    import math

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

    # === MAP INBOARD POINTS TO FRONT & REAR ===
    # front.yaml requires the inboard points to be separated into _front and _rear
    derived["lower_wishbone_inboard_front.y"] = p.get("lower_wishbone_inboard.y")
    derived["lower_wishbone_inboard_rear.y"] = p.get("lower_wishbone_inboard.y")
    derived["lower_wishbone_inboard_front.z"] = lca_in_z
    derived["lower_wishbone_inboard_rear.z"] = lca_in_z

    derived["upper_wishbone_inboard_front.y"] = p.get("upper_wishbone_inboard.y")
    derived["upper_wishbone_inboard_rear.y"] = p.get("upper_wishbone_inboard.y")
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

    # Set symmetrical x coordinates of inbound points
    derived["lower_wishbone_inboard_front.x"] = (
        derived["lower_wishbone_outboard.x"] + 50.0
    )
    derived["lower_wishbone_inboard_rear.x"] = (
        derived["lower_wishbone_outboard.x"] - 50.0
    )
    derived["upper_wishbone_inboard_front.x"] = (
        derived["upper_wishbone_outboard.x"] + 50.0
    )
    derived["upper_wishbone_inboard_rear.x"] = (
        derived["upper_wishbone_outboard.x"] - 50.0
    )

    for k, v in p.items():
        if k not in derived and not k.endswith("_frac") and "wishbone_inboard" not in k:
            derived[k] = v

    return derived


OBJECTIVES = {
    "fvsa_length": ("01_bump_parallel", "fvsa_length", "maximize"),
    "bump_steer": ("01_bump_parallel", "bump_steer", "minimize"),
    "bump_scrub": ("01_bump_parallel", "bump_scrub", "minimize"),
}

# `fvsa_sign` exists because `fvsa_length` is a SIGNED quantity: positive means
# the front-view instant centre sits inboard of the contact patch (conventional
# - bump gives negative camber), negative means outboard (bump gives POSITIVE
# camber). The sign flips through infinity at parallel wishbones, so a bare
# `maximize fvsa_length` is only meaningful on the positive branch: on the
# negative branch, "larger" means a SHORTER outboard swing arm and MORE camber
# change of the wrong sign. Designs on that branch have already been produced
# (Paretro2 measures -2064 mm). This lower bound keeps the search on the
# conventional branch. It reads a metric the objective already computes, so it
# costs no extra solving. 1000 mm is a sign guard, not a real minimum swing-arm
# length - raise it if you want to rule out genuinely short arms too.
#
# BETTER, WHEN THERE IS TIME: drop the FVSA objective entirely and minimise the
# travel-weighted |camber - camber_design| over 01_bump_parallel instead, reusing
# the same integral bump_steer uses. Camber gain is what FVSA is a proxy for, and
# it has no sign, no branch and no singularity.
CONSTRAINTS = {
    "rc_height": ("01_bump_parallel", "roll_center_z", (0.0, 40.0)),
    "ackermann": ("04_steer_design", "ackermann", (90.0, 110.0)),
    "kingpin": ("01_bump_parallel", "kpi", (9.0, 11.0)),
    "max_turn": ("04_steer_design", "max_turn", (17.5, 90.0)),
    "fvsa_sign": ("01_bump_parallel", "fvsa_length", (1000.0, None)),
}

# Auto-convert absolute Z coordinates in KNOWN_DESIGN to the z_frac required by the optimizer
min_sep = 200.0  # From evaluate.py FIXED_PARAMS

if "upper_wishbone_outboard.z" in KNOWN_DESIGN:
    lca_z = KNOWN_DESIGN.get("lower_wishbone_outboard.z", 185.0)
    uca_z = KNOWN_DESIGN.get("upper_wishbone_outboard.z")
    KNOWN_DESIGN["upper_wishbone_outboard.z_frac"] = (uca_z - (lca_z + min_sep)) / 200.0

if "upper_wishbone_inboard.z" in KNOWN_DESIGN:
    lca_in_z = KNOWN_DESIGN.get("lower_wishbone_inboard.z", 185.0)
    lca_z = KNOWN_DESIGN.get("lower_wishbone_outboard.z", 185.0)
    uca_in_z = KNOWN_DESIGN.get("upper_wishbone_inboard.z")
    uca_in_z_min = max(lca_z, lca_in_z) + min_sep
    KNOWN_DESIGN["upper_wishbone_inboard.z_frac"] = (uca_in_z - uca_in_z_min) / 200.0

if __name__ == "__main__":
    run_optimization()
