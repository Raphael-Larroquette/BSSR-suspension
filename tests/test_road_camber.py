"""Road-relative camber: ISO 8855 inclination angle, sign mirrored like camber.

The analytic cases build the two vectors the metric reads (the outboard spin
axis and the road normal) directly, so the expected value is known in closed
form and does not depend on any solved geometry. The solved cases check the
wiring: the column is exported for both corners, agrees with camber where the
two must agree, and splits from it with the right sign when the road tilts.
"""

from math import asin, atan, cos, degrees, radians, sin, tan
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from kinematics.cli.io.loaders import load_geometry
from kinematics.core.enums import Axis, PointID
from kinematics.core.input import build_sweep
from kinematics.core.metrics.angles import calculate_camber
from kinematics.core.metrics.catalog import get_default_corner_metrics
from kinematics.core.metrics.main import compute_metrics_for_state_from_suspension
from kinematics.core.metrics.steering_geometry import calculate_road_camber
from kinematics.core.primitives.geometry import Direction3
from kinematics.core.primitives.point_ref import PointRef, Side
from kinematics.core.road import RoadPlane
from kinematics.core.suspensions.axle import AxleSuspension
from kinematics.core.sweep import solve_sweep


def _spin_axis(side_sign: float, camber_deg: float, steer_deg: float) -> Direction3:
    """Outboard spin axis of a wheel with true inclination and ISO steer.

    The wheel is first leaned by ``camber_deg`` (positive = top outboard, so the
    outboard end of the axle drops), then steered about chassis +Z by
    ``steer_deg`` (ISO: positive = left on both sides).
    """
    g = radians(camber_deg)
    leaned = np.array([0.0, side_sign * cos(g), -sin(g)])
    d = radians(steer_deg)
    rz = np.array([[cos(d), -sin(d), 0.0], [sin(d), cos(d), 0.0], [0.0, 0.0, 1.0]])
    return Direction3(tuple(rz @ leaned))


def _ctx(side_sign: float, axis: Direction3, road_tilt_deg: float = 0.0):
    """The two inputs the metric reads, plus side_sign for calculate_camber.

    ``road_tilt_deg`` tilts the road normal towards chassis +Y (left).
    """
    b = radians(road_tilt_deg)
    normal = Direction3((0.0, sin(b), cos(b)))
    return SimpleNamespace(
        side_sign=side_sign,
        wheel_axis=axis,
        road=SimpleNamespace(normal=normal),
    )


@pytest.mark.parametrize("side_sign", [1.0, -1.0])
@pytest.mark.parametrize("camber", [-3.0, 0.0, 2.0])
def test_level_road_straight_ahead_equals_camber(side_sign, camber) -> None:
    ctx = _ctx(side_sign, _spin_axis(side_sign, camber, 0.0))
    assert calculate_road_camber(ctx) == pytest.approx(camber, abs=1e-12)
    assert calculate_camber(ctx) == pytest.approx(camber, abs=1e-12)


@pytest.mark.parametrize("side_sign", [1.0, -1.0])
@pytest.mark.parametrize("steer", [-30.0, -10.0, 15.0, 35.0])
def test_steer_does_not_leak_into_road_camber(side_sign, steer) -> None:
    """Measured about X_T, which turns with the wheel: steer changes nothing."""
    camber = -2.0
    ctx = _ctx(side_sign, _spin_axis(side_sign, camber, steer))
    assert calculate_road_camber(ctx) == pytest.approx(camber, abs=1e-12)


@pytest.mark.parametrize("side_sign", [1.0, -1.0])
def test_iso_camber_differs_under_steer_exactly_as_its_definition_says(
    side_sign,
) -> None:
    """ISO camber is about X_V, so a steered lean projects as tan(g)/cos(d).

    This is the reason road camber exists as a separate channel, not a defect
    in camber: both follow their ISO definitions.
    """
    camber, steer = -2.0, 30.0
    ctx = _ctx(side_sign, _spin_axis(side_sign, camber, steer))
    expected_iso_camber = degrees(atan(tan(radians(camber)) / cos(radians(steer))))
    assert calculate_camber(ctx) == pytest.approx(expected_iso_camber, abs=1e-9)
    assert calculate_road_camber(ctx) == pytest.approx(camber, abs=1e-12)
    assert abs(calculate_camber(ctx) - calculate_road_camber(ctx)) > 0.1


@pytest.mark.parametrize("tilt", [-4.0, 3.0])
def test_tilted_road_mirrors_between_sides(tilt) -> None:
    """Normal tilted left by b: left reads camber - b, right reads camber + b."""
    camber = -1.5
    left = calculate_road_camber(_ctx(1.0, _spin_axis(1.0, camber, 0.0), tilt))
    right = calculate_road_camber(_ctx(-1.0, _spin_axis(-1.0, camber, 0.0), tilt))
    assert left == pytest.approx(camber - tilt, abs=1e-12)
    assert right == pytest.approx(camber + tilt, abs=1e-12)


def test_sign_relation_to_strict_iso_inclination() -> None:
    """road_camber = -side_sign * ISO inclination (right-hand about X_T).

    A wheel whose top leans to the vehicle's RIGHT is a positive ISO
    inclination on both sides. That lean is inboard on the left wheel
    (road camber negative) and outboard on the right (road camber positive).
    """
    lean_right = 2.0  # deg, top of wheel towards -Y
    left = calculate_road_camber(_ctx(1.0, _spin_axis(1.0, -lean_right, 0.0)))
    right = calculate_road_camber(_ctx(-1.0, _spin_axis(-1.0, lean_right, 0.0)))
    assert left == pytest.approx(-1.0 * lean_right)
    assert right == pytest.approx(+1.0 * lean_right)


def test_road_camber_is_registered_as_a_degree_corner_metric() -> None:
    names = {m.column_name: m for m in get_default_corner_metrics()}
    assert "road_camber" in names
    assert names["road_camber"].unit.name == "DEG"


def _rolled_axle_rows(test_data_dir: Path, left_mm: float, right_mm: float):
    axle = load_geometry(test_data_dir / "axle_geometry.yaml")
    assert isinstance(axle, AxleSuspension)
    spec = yaml.safe_load(
        (test_data_dir / "axle_sweep.yaml").read_text(encoding="utf-8")
    )
    del spec["steps"]
    for target, value in zip(
        spec["targets"], (left_mm, right_mm, 0.0), strict=True
    ):
        target.pop("start", None)
        target.pop("stop", None)
        target["values"] = [value]
    states, _ = solve_sweep(axle, build_sweep(spec, axle))
    rows = compute_metrics_for_state_from_suspension(states[0], axle)
    left_cc = states[0].get(PointRef(Side.LEFT, PointID.WHEEL_CONTACT_CENTRE))
    right_cc = states[0].get(PointRef(Side.RIGHT, PointID.WHEEL_CONTACT_CENTRE))
    road = RoadPlane.from_axle_contact_centres(left_cc, right_cc)
    return rows, road


def test_solved_axle_exports_road_camber_and_matches_camber_at_design(
    test_data_dir: Path,
) -> None:
    rows, _ = _rolled_axle_rows(test_data_dir, 0.0, 0.0)
    for side in (Side.LEFT, Side.RIGHT):
        corner = rows.corners[side]
        # Equal up to the second-order toe projection: design toe is small.
        assert corner["road_camber"] == pytest.approx(corner["camber"], abs=1e-3)


def test_solved_roll_splits_road_camber_from_camber_with_mirrored_sign(
    test_data_dir: Path,
) -> None:
    """Left wheel up, right wheel down: the road tilts against the chassis.

    The loaded (bump) wheel gains road camber, the droop wheel loses it, by
    the road plane's tilt. That tilt is a kinematic quantity, not body roll.
    """
    rows, road = _rolled_axle_rows(test_data_dir, 20.0, -20.0)
    n = road.normal
    tilt = degrees(asin(float(n[Axis.Y])))  # towards +Y, i.e. b in the analytic tests
    left, right = rows.corners[Side.LEFT], rows.corners[Side.RIGHT]

    assert tilt < 0.0  # left contact patch is higher, so the normal leans right
    assert left["road_camber"] - left["camber"] == pytest.approx(-tilt, abs=2e-2)
    assert right["road_camber"] - right["camber"] == pytest.approx(tilt, abs=2e-2)
    assert left["road_camber"] > left["camber"]
    assert right["road_camber"] < right["camber"]
