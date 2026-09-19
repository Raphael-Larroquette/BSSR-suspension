from opt.evaluate import run_optimization

CAR_NAME = "aurora"
POPULATION_SIZE = 64
GENERATIONS = 3

BUMP_WEIGHTING = 1.5

SWEEP_LIMITS = {
    "01_bump_parallel": {"start": -20.0, "stop": 20.0},
    "04_steer_design": {"start": -35.0, "stop": 35.0},
}

FREE_PARAMETERS = {
    "lower_wishbone_outboard.y": (380.0, 450.0),
    "lower_wishbone_outboard.z": (100, 200.0),
    "upper_wishbone_outboard.z_frac": (0.0, 1.0),
    "lower_wishbone_inboard.y": (0.0, 320.0),
    "lower_wishbone_inboard.z": (137.5, 200.0),
    "upper_wishbone_inboard.y": (0.0, 340.0),
    "upper_wishbone_inboard.z_frac": (0.0, 1.0),  # Fractional span ensures safety
    "trackrod_outboard.x": (-150.0, -100.0),
    "trackrod_outboard.z": (450.0, 560.0),
    "trackrod_outboard.y": (320.0, 380.0),
    "trackrod_inboard.x": (-150.0, -100.0),
    "trackrod_inboard.z": (450.0, 560.0),
    "trackrod_inboard.y": (200.0, 280.0),
}

KNOWN_DESIGN = {
    "lower_wishbone_outboard.y": 422.38,
    "lower_wishbone_outboard.z": 185.0,
    "upper_wishbone_outboard.z_frac": 0.683235,
    "lower_wishbone_inboard.y": 249.79,
    "lower_wishbone_inboard.z": 185.0,
    "upper_wishbone_inboard.y": 235.389,
    "upper_wishbone_inboard.z_frac": 0.6491,
    "trackrod_outboard.x": -129.718,
    "trackrod_outboard.z": 538.251,
    "trackrod_outboard.y": 354.863,
    "trackrod_inboard.x": -150.0,
    "trackrod_inboard.z": 531.106,
    "trackrod_inboard.y": 228.97,
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

    for k, v in p.items():
        if k not in derived and not k.endswith("_frac") and "inboard." not in k:
            derived[k] = v

    return derived


OBJECTIVES = {
    "fvsa_length": ("01_bump_parallel", "fvsa_length", "maximize"),
    "bump_steer": ("01_bump_parallel", "bump_steer", "minimize"),
    "bump_scrub": ("01_bump_parallel", "bump_scrub", "minimize"),
}

CONSTRAINTS = {
    "rc_height": ("01_bump_parallel", "roll_center_z", (0.0, 30.0)),
    "ackermann": ("04_steer_design", "ackermann", (90.0, 110.0)),
    "kingpin": ("01_bump_parallel", "kpi", (9.0, 11.0)),
    "max_turn": ("04_steer_design", "max_turn", (17.5, 90.0)),
}

if __name__ == "__main__":
    run_optimization()
