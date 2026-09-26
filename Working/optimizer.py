from opt.construct import spring_fractions, spring_mounts, top_height
from opt.evaluate import run_optimization
#TO RUN: type into terminal: uv run python Working/optimizer.py 
#Once done to export them to yamls run: uv run python Working/export_pareto.py 
#to solve, type uv run python Working/run_all.py --sets front --geometry "Working\models\pareto1\front.yaml" --only 01, 02 --no-forces 
CAR_NAME = "aurora"
POPULATION_SIZE = 1320   # max workers is 60 on python in windows. so you need at least a pop of 165 the number of objectives
GENERATIONS = 300

BUMP_WEIGHTING = 1.5

# True prints why each failed candidate failed. Off, each generation prints
# only how many failed - most failures are ordinary kinematic lock-outs.
VERBOSE_FAILURES = False

SWEEP_LIMITS = {
    "01_bump_parallel": {"start": -50.8, "stop": 50.8},
    "04_steer_design": {"start": -35.0, "stop": 35.0},
}

# Steps the OPTIMISER solves each sweep at. run.yaml's own counts (22 and 65)
# are what the reports use; the search reads far fewer frames than it solves.
#   01_bump_parallel  three objectives integrate this curve, so it needs real
#                     resolution. 11 costs ~0.3% on the integrals, uniform
#                     across candidates so rankings are unaffected. Below 9 the
#                     trapezoid error starts to matter.
#   04_steer_design   only `ackermann` (last frame, full lock) and `max_turn`
#                     (the two extremes) are read, and steer is monotonic in
#                     rack travel, so 3 frames capture both locks exactly -
#                     measured identical to 4 decimals against 65.
#                     WARNING: add an objective that reads the SHAPE of the
#                     steer curve and this must go back up.
SWEEP_STEPS = {
    "01_bump_parallel": 11,
    "04_steer_design": 3,
}

FREE_PARAMETERS = {
    "lower_wishbone_outboard.y": (400.0, 500.0),
    "lower_wishbone_outboard.z": (85.0, 200.0),
    "upper_wishbone_outboard.z_frac": (0.0, 1.0),
    "lower_wishbone_inboard.y": (100.0, 350.0),
    "lower_wishbone_inboard.z": (117.5, 200.0), #lower is 80mm ride hight + 37.5mm min separation
    "upper_wishbone_inboard.y": (100.0, 400.0),
    "upper_wishbone_inboard.z_frac": (0.0, 1.0),  # Fractional span ensures safety
    "trackrod_outboard.x": (-250.0, -50.0), # behind caster 
    "trackrod_outboard.z": (400.0, 550.0), #bellow top of wheel + margin
    "trackrod_outboard.y": (350.0, 435.0),
    "trackrod_inboard.x": (-350.0, -50.0),
    "trackrod_inboard.z": (400.0, 560.0),
    "trackrod_inboard.y": (142.875, 340.0),
    # Inboard pivot x, absolute. Front and rear ranges never overlap, so the
    # front pivot is always ahead of the rear one by at least 50 mm.
    "lower_wishbone_inboard_front.x": (25.0, 250.0),
    "lower_wishbone_inboard_rear.x": (-250.0, -25.0),
    "upper_wishbone_inboard_front.x": (25.0, 250.0),
    "upper_wishbone_inboard_rear.x": (-250.0, -25.0),
    # Spring mounts: fractions inside the UCA-LCA prism, see opt/construct.py.
    # h: 0 = LCA triangle, 1 = UCA triangle. w: 0 = inboard, 1 = outboard.
    # x is shared by both mounts: 0 = rearmost common x, 1 = frontmost.
    # rise: the chassis mount's height as a fraction of the way from the LCA
    # mount up to the UCA triangle, so it can never sit below the LCA mount.
    "spring.x_frac": (0.0, 1.0),
    "strut_top.rise_frac": (0.0, 1.0),    # chassis mount
    "strut_top.w_frac": (0.0, 1.0),
    "strut_bottom.h_frac": (0.0, 1.0),    # LCA mount
    "strut_bottom.w_frac": (0.0, 1.0),
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
    "trackrod_outboard.y": 394.5,   # was 407.4: 32% Ackermann; 394.5 gives 95%
    "trackrod_inboard.x": -130,
    "trackrod_inboard.z": 516.2,
    "trackrod_inboard.y": 320.7,
    # Previously derived as outboard x +/- 50, kept so the seed is unchanged.
    "lower_wishbone_inboard_front.x": 67.37,
    "lower_wishbone_inboard_rear.x": -32.63,
    "upper_wishbone_inboard_front.x": 30.54,
    "upper_wishbone_inboard_rear.x": -69.46,
    # Absolute spring mounts; converted to prism fractions by
    # resolve_spring_seed(). Chosen so the seed passes every constraint
    # (motion ratio 0.80); Aurora's mounts sit outside this seed's prism.
    "strut_top": (10.43, 365.75, 341.13),
    "strut_bottom": (10.43, 443.12, 166.76),
}

#: The force objective: this share of the mean joint force plus the rest of the
#: largest one. Both are |F| in N over every front joint and every load case in
#: forces/<CAR_NAME>/forces.yaml.
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

    # Inboard pivot x: free parameters, one per pivot.
    for arm in ("lower", "upper"):
        for end in ("front", "rear"):
            key = f"{arm}_wishbone_inboard_{end}.x"
            derived[key] = p[key]

    # Spring mounts: placed inside the prism the two arms sweep out.
    lca, uca = wishbone_triangles(derived)
    top, bottom = spring_mounts(
        lca, uca, p["spring.x_frac"],
        (top_height(p["strut_bottom.h_frac"], p["strut_top.rise_frac"]),
         p["strut_top.w_frac"]),
        (p["strut_bottom.h_frac"], p["strut_bottom.w_frac"]),
    )
    for name, point in (("strut_top", top), ("strut_bottom", bottom)):
        for axis, value in zip("xyz", point):
            derived[f"{name}.{axis}"] = float(value)

    for k, v in p.items():
        if k not in derived and not k.endswith("_frac") and "wishbone_inboard" not in k:
            derived[k] = v

    return derived


OBJECTIVES = {
    "fvsa_length": ("01_bump_parallel", "fvsa_length", "maximize"),
    "bump_steer": ("01_bump_parallel", "bump_steer", "minimize"),
    "bump_scrub": ("01_bump_parallel", "bump_scrub", "minimize"),
    # "forces" is not a sweep: it is the static force solve at design height.
    "joint_force": ("forces", "joint_force", "minimize"),
}

CONSTRAINTS = {
    "rc_height": ("01_bump_parallel", "roll_center_z", (0.0, 40.0)),
    "ackermann": ("04_steer_design", "ackermann", (60.0, 110.0)),
    "kingpin": ("01_bump_parallel", "kpi", (9.0, 11.0)),
    "max_turn": ("04_steer_design", "max_turn", (17.5, 90.0)),
    "fvsa_sign": ("01_bump_parallel", "fvsa_length", (1000.0, None)),
    # Damper travel / wheel travel, at design height.
    "motion_ratio": ("01_bump_parallel", "motion_ratio", (0.6, 1.01)),
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


def resolve_spring_seed(fixed):
    """
    Turn KNOWN_DESIGN's absolute spring mounts into prism fractions, in place.

    Run once, by the parent process, before the initial population is built -
    not at import, because every worker imports this file. A mount outside the
    seed's own prism has no exact fractions; the nearest in-prism pair is used
    and the miss is printed.
    """
    if "strut_top" not in KNOWN_DESIGN:
        return
    top = KNOWN_DESIGN.pop("strut_top")
    bottom = KNOWN_DESIGN.pop("strut_bottom")
    trial = dict(KNOWN_DESIGN)
    trial.update({"spring.x_frac": 0.5, "strut_top.rise_frac": 0.5,
                  "strut_top.w_frac": 0.5, "strut_bottom.h_frac": 0.5,
                  "strut_bottom.w_frac": 0.5})
    lca, uca = wishbone_triangles(derive_parameters(trial, fixed))
    fractions, miss = spring_fractions(lca, uca, top, bottom)
    KNOWN_DESIGN.update(fractions)
    if miss > 0.5:
        print(f"KNOWN_DESIGN spring mounts are outside the seed's UCA-LCA prism; "
              f"seeding with the nearest in-prism mounts ({miss:.1f} mm away)")


if __name__ == "__main__":
    run_optimization()
