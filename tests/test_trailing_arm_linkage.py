"""Trailing-arm shock linkages: direct (A) and the four rocker layouts (B-E).

The fixtures in ``tests/data/trailing_arm_linkage`` are the Aurora arm with a
rocker linkage drawn in side view. Every kinematic result is checked against an
independent planar solver written here (circle-circle intersections in x-z, no
code shared with the package), and every force result against virtual work.
"""

import warnings
from pathlib import Path

import numpy as np
import pytest
import yaml

from kinematics.cli.io.loaders import load_geometry
from kinematics.core.enums import LinkageMount, PointID
from kinematics.core.input import build_suspension, build_sweep
from kinematics.core.loads.cases import LoadCase
from kinematics.core.loads.main import solve_forces
from kinematics.core.loads.travel import solve_forces_over_travel
from kinematics.core.suspensions.corner.trailing_arm_linkage import (
    TrailingArmLinkage,
    transmission_angle_deg,
)
from kinematics.core.sweep import solve_evaluated_sweep

DATA = Path(__file__).parent / "data"
LAYOUTS = "BCDE"
STEPS = 17
TRAVEL = 50.8
MASS = 294.0
GRAVITY = 9.80665
PIVOT = np.array([-1865.0, 278.5])
WHEEL = np.array([-2240.0, 278.5])


# --------------------------------------------------------------------------
# Independent planar reference
# --------------------------------------------------------------------------
def _rotate(point, centre, angle):
    c, s = np.cos(angle), np.sin(angle)
    d = point - centre
    return centre + np.array([c * d[0] - s * d[1], s * d[0] + c * d[1]])


def _circles(c0, r0, c1, r1, near):
    d = np.linalg.norm(c1 - c0)
    a = (r0**2 - r1**2 + d**2) / (2 * d)
    h = np.sqrt(max(r0**2 - a**2, 0.0))
    mid = c0 + a * (c1 - c0) / d
    perp = np.array([-(c1 - c0)[1], (c1 - c0)[0]]) / d
    return min((mid + h * perp, mid - h * perp), key=lambda p: np.linalg.norm(p - near))


def _planar_pose(design, layout, z):
    """Pose of every linkage point at wheel travel z, in (x, z)."""
    arm_angle = -np.arcsin(z / np.linalg.norm(WHEEL - PIVOT))

    def arm(point):
        return _rotate(point, PIVOT, arm_angle)

    rocker_on_arm = layout in "DE"
    rocker = arm(design["R"]) if rocker_on_arm else design["R"]
    rod_end = design["O"] if rocker_on_arm else arm(design["O"])
    base = arm(design["T"]) if layout in "CE" else design["T"]
    inboard = _circles(
        rocker,
        np.linalg.norm(design["I"] - design["R"]),
        rod_end,
        np.linalg.norm(design["I"] - design["O"]),
        arm(design["I"]) if rocker_on_arm else design["I"],
    )
    before, after = design["I"] - design["R"], inboard - rocker
    turn = np.arctan2(before[0] * after[1] - before[1] * after[0], before @ after)
    shock_end = rocker + _rotate(design["S"] - design["R"], np.zeros(2), turn)
    return {
        "R": rocker,
        "O": rod_end,
        "I": inboard,
        "S": shock_end,
        "T": base,
        "turn": np.degrees(turn) - (np.degrees(arm_angle) if rocker_on_arm else 0.0),
    }


def _acute(u, v):
    cosine = abs(u @ v) / np.linalg.norm(u) / np.linalg.norm(v)
    return np.degrees(np.arccos(min(1.0, cosine)))


def _planar_reference(path, layout):
    points = yaml.safe_load(path.read_text())["hardpoints"]

    def xz(name):
        return np.array([points[name]["x"], points[name]["z"]], dtype=float)

    design = {
        "O": xz("pushrod_outboard"),
        "R": xz("rocker_axis_a"),
        "I": xz("pushrod_inboard"),
        "S": xz("strut_bottom"),
        "T": xz("strut_top"),
    }
    rows = []
    for z in np.linspace(-TRAVEL, TRAVEL, STEPS):
        pose = _planar_pose(design, layout, z)
        h = 1e-3

        def length(zz):
            q = _planar_pose(design, layout, zz)
            return np.linalg.norm(q["S"] - q["T"])

        rows.append(
            {
                "damper_length": np.linalg.norm(pose["S"] - pose["T"]),
                "install_ratio": -(length(z + h) - length(z - h)) / (2 * h),
                "rod_transmission_angle": _acute(
                    pose["I"] - pose["O"], pose["I"] - pose["R"]
                ),
                "shock_transmission_angle": _acute(
                    pose["S"] - pose["T"], pose["S"] - pose["R"]
                ),
                # planar x-z turn is right-handed about -y; the axis a -> b is +y
                "rocker_angle": -pose["turn"],
            }
        )
    return rows


def _fixture(layout):
    return DATA / "trailing_arm_linkage" / f"layout_{layout.lower()}.yaml"


def _sweep(suspension):
    return solve_evaluated_sweep(
        suspension,
        build_sweep(
            {
                "version": 1,
                "steps": STEPS,
                "targets": [
                    {
                        "type": "point",
                        "point": "wheel_center",
                        "side": "center",
                        "direction": {"axis": "z"},
                        "mode": "relative",
                        "start": -TRAVEL,
                        "stop": TRAVEL,
                    }
                ],
            },
            suspension,
        ),
    )


@pytest.fixture(scope="module", params=list(LAYOUTS))
def solved(request):
    layout = request.param
    suspension = load_geometry(_fixture(layout))
    return layout, suspension, _sweep(suspension)


# --------------------------------------------------------------------------
# Kinematics
# --------------------------------------------------------------------------
def test_layout_is_read_from_the_two_switches(solved):
    layout, suspension, _ = solved
    assert suspension.linkage.layout == layout
    assert tuple(suspension.free_points()) == (
        PointID.AXLE_INBOARD,
        PointID.PUSHROD_INBOARD,
        PointID.STRUT_BOTTOM,
    )


@pytest.mark.parametrize(
    "channel",
    [
        "damper_length",
        "rod_transmission_angle",
        "shock_transmission_angle",
        "rocker_angle",
    ],
)
def test_matches_the_planar_four_bar(solved, channel):
    layout, _, evaluated = solved
    assert not evaluated.diagnostics
    reference = _planar_reference(_fixture(layout), layout)
    tool = [row[channel] for row in evaluated.metrics.rows]
    np.testing.assert_allclose(tool, [r[channel] for r in reference], atol=1e-4)


def test_installation_ratio_matches_the_planar_four_bar(solved):
    layout, _, evaluated = solved
    reference = _planar_reference(_fixture(layout), layout)
    tool = [-row["deriv_damper_length_wrt_hub_z"] for row in evaluated.metrics.rows]
    np.testing.assert_allclose(tool, [r["install_ratio"] for r in reference], atol=1e-6)


def test_fixtures_keep_healthy_transmission_angles(solved):
    _, _, evaluated = solved
    for row in evaluated.metrics.rows:
        assert row["rod_transmission_angle"] > 45.0
        assert row["shock_transmission_angle"] > 45.0


def test_transmission_angle_definition():
    axis = np.array([0.0, 1.0, 0.0])
    root = np.zeros(3)
    tip = np.array([100.0, 0.0, 0.0])
    square = transmission_angle_deg(np.array([100.0, 0.0, -50.0]), tip, root, tip, axis)
    along = transmission_angle_deg(np.array([200.0, 5.0, 0.0]), tip, root, tip, axis)
    assert square == pytest.approx(90.0)
    assert along == pytest.approx(0.0)  # toggle: the axial offset is projected out


# --------------------------------------------------------------------------
# Forces
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def front():
    return load_geometry(DATA / "aurora" / "front.yaml")


CHASSIS_POINTS = {
    "B": {"rocker_axis_a", "rocker_axis_b", "strut_top"},
    "C": {"rocker_axis_a", "rocker_axis_b"},
    "D": {"pushrod_outboard", "strut_top"},
    "E": {"pushrod_outboard"},
}


def test_every_layout_is_statically_determinate(solved, front):
    layout, suspension, _ = solved
    run = solve_forces([front, suspension], [LoadCase(6, 0, 0)], MASS, GRAVITY)
    rear = {
        block.part
        for block in run.solution.blocks
        if any(row.axle.value == "rear" for row in block.rows)
    }
    rod = "Dogbone" if layout in "DE" else "Pushrod"
    assert rear == {rod, "Rocker", "Semi-Trailing Arm", "Rear Spring/Damper"}
    chassis = next(b for b in run.solution.chassis if b.part == "Rear Chassis")
    assert set(chassis.columns) == CHASSIS_POINTS[layout] | {
        "trailing_arm_pivot_a",
        "trailing_arm_pivot_b",
    }


def test_shock_force_follows_virtual_work_along_travel(solved, front):
    """|F_shock| * IR = F_z at every pose, IR from kinematics alone."""
    _, suspension, evaluated = solved
    travel = solve_forces_over_travel(
        [front, suspension], 1, evaluated.states, [LoadCase(6, 0, 0)], MASS, GRAVITY
    )
    for step, row in enumerate(evaluated.metrics.rows):
        parts = {t.loads.part: t.loads for t in travel.rows if t.step == step}
        shock = np.linalg.norm(parts["Rear Spring/Damper"].loads[0].force)
        tyre = next(load for load in parts["Semi-Trailing Arm"].loads if load.applied)
        ratio = -row["deriv_damper_length_wrt_hub_z"]
        assert shock * ratio == pytest.approx(tyre.force[2], rel=1e-9)


# --------------------------------------------------------------------------
# Configuration rules
# --------------------------------------------------------------------------
def _geometry(**changes):
    data = yaml.safe_load(_fixture("B").read_text())
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    return data


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"actuation": None, "spring": {"type": "coilover", "base": "arm"}}, "base"),
        ({"actuation": {"type": "pushrod_rocker"}}, "rocker_mount"),
        (
            {"actuation": {"type": "direct", "rocker_mount": "arm"}},
            "rocker_mount needs",
        ),
        ({"spring": {"type": "torsion_bar"}}, "coilover"),
    ],
)
def test_invalid_combinations_are_named(changes, message):
    with pytest.raises(ValueError, match=message):
        build_suspension(_geometry(**changes))


def test_double_wishbone_has_no_linkage_switches(test_data_dir):
    data = yaml.safe_load((test_data_dir / "geometry.yaml").read_text())
    key = "axle_config" if "axle_config" in data else None
    target = data[key] if key else data
    target["actuation"] = {**target["actuation"], "rocker_mount": "arm"}
    with pytest.raises(ValueError, match="rocker_mount"):
        build_suspension(data)


def test_a_pickup_on_the_rocker_axis_is_rejected():
    data = _geometry()
    axis = data["hardpoints"]["rocker_axis_a"]
    data["hardpoints"]["strut_bottom"] = {**axis, "y": 100}
    with pytest.raises(ValueError, match="STRUT_BOTTOM must not lie on the rocker"):
        build_suspension(data)


def test_a_skewed_rocker_axis_warns():
    data = _geometry()
    data["hardpoints"]["rocker_axis_b"]["x"] += 10.0  # ~14 deg in plan
    with pytest.warns(UserWarning, match="from parallel"):
        build_suspension(data)


def test_a_parallel_rocker_axis_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        build_suspension(_geometry())


def test_direct_layout_is_unchanged_by_default(aurora_dir):
    rear = load_geometry(aurora_dir / "rear.yaml")
    assert rear.linkage == TrailingArmLinkage()
    assert rear.linkage.layout == "A"
    assert rear.linkage.base is LinkageMount.CHASSIS
