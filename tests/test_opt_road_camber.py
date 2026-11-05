"""Optimiser: the road_camber objective and per-drive SWEEP_LIMITS.

Frames are built directly with the handful of metrics the reducer reads, so
the expected scores are known in closed form.
"""

import math
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

WORKING = Path(__file__).resolve().parents[1] / "Working"
if str(WORKING) not in sys.path:
    sys.path.insert(0, str(WORKING))

from opt import reduce as R  # noqa: E402
from opt import solve as S  # noqa: E402

RANGE_GROUPS = ("travel", "damper", "rack")


@pytest.fixture(autouse=True)
def _no_solver_policy(monkeypatch):
    """Read every frame: the solver policy needs an activated run script."""
    monkeypatch.setattr(R, "usable_frames", lambda analysis, name: analysis.frames)


def _ramp(n=13, travel=25.0, rack=35.0, steer=22.0, outer="left",
          outer_cam=lambda t: 0.0, inner_cam=lambda t: 0.0, hold=False):
    """A right turn (outer left) or left turn (outer right) ramp, or a held roll."""
    inner = "right" if outer == "left" else "left"
    sign = -1.0 if outer == "left" else 1.0  # ISO steer: right turn negative
    frames = []
    for i in range(n):
        u = i / (n - 1)
        z = travel if hold else travel * u
        frames.append(NS(
            metrics={"rack_displacement": rack * u},
            corner_metrics={
                outer: {"steer_angle": sign * steer * u, "wheel_travel": z,
                        "road_camber": outer_cam(u)},
                inner: {"steer_angle": sign * steer * u, "wheel_travel": -z,
                        "road_camber": inner_cam(u)},
            },
        ))
    return NS(frames=frames)


def test_constant_road_camber_gives_weighted_rms() -> None:
    analysis = _ramp(outer_cam=lambda u: 1.0, inner_cam=lambda u: 2.0)
    expected = math.sqrt((4.0 * 1.0 + 1.0 * 4.0) / 5.0)
    assert R.road_camber_score(analysis, 4.0) == pytest.approx(expected)


def test_target_is_subtracted_before_squaring() -> None:
    analysis = _ramp(outer_cam=lambda u: -1.0, inner_cam=lambda u: -1.0)
    assert R.road_camber_score(analysis, 4.0, target=-1.0) == pytest.approx(0.0)


def test_signed_regions_cannot_cancel() -> None:
    analysis = _ramp(outer_cam=lambda u: 1.0 if u < 0.5 else -1.0,
                     inner_cam=lambda u: 0.0)
    assert R.road_camber_score(analysis, 4.0) > 0.8


def test_linear_curve_matches_closed_form() -> None:
    # g(u) = 3u over the span: mean of g^2 is 3, on the outer wheel only.
    analysis = _ramp(n=401, outer_cam=lambda u: 3.0 * u)
    expected = math.sqrt(4.0 * 3.0 / 5.0)
    assert R.road_camber_score(analysis, 4.0) == pytest.approx(expected, rel=1e-4)


def test_outer_wheel_follows_turn_direction() -> None:
    right_turn = _ramp(outer="left", outer_cam=lambda u: 1.0)
    left_turn = _ramp(outer="right", outer_cam=lambda u: 1.0)
    assert R._corner_sides(right_turn.frames) == ("left", "right")
    assert R._corner_sides(left_turn.frames) == ("right", "left")
    assert R.road_camber_score(right_turn, 4.0) == pytest.approx(
        R.road_camber_score(left_turn, 4.0))


def test_wrong_way_roll_is_refused() -> None:
    analysis = _ramp(travel=-25.0)  # right turn, but the outer (left) wheel droops
    with pytest.raises(ValueError, match="rolled the wrong way"):
        R.road_camber_score(analysis, 4.0)


def test_unsteered_sweep_is_refused() -> None:
    analysis = _ramp(steer=0.0)
    with pytest.raises(ValueError, match="steered sweep"):
        R.road_camber_score(analysis, 4.0)


def test_held_roll_integrates_over_rack() -> None:
    analysis = _ramp(n=401, hold=True, outer_cam=lambda u: 3.0 * u)
    expected = math.sqrt(4.0 * 3.0 / 5.0)
    assert R.road_camber_score(analysis, 4.0) == pytest.approx(expected, rel=1e-4)


def test_inner_positive_costs_more_than_negative() -> None:
    pos = _ramp(inner_cam=lambda u: 1.0)
    neg = _ramp(inner_cam=lambda u: -1.0)
    assert R.road_camber_score(pos, 4.0, inner_positive_weight=3.0) == \
        pytest.approx(math.sqrt(3.0 / 5.0))
    assert R.road_camber_score(neg, 4.0, inner_positive_weight=3.0) == \
        pytest.approx(math.sqrt(1.0 / 5.0))


def test_asymmetry_is_inner_only_and_about_target() -> None:
    outer_pos = _ramp(outer_cam=lambda u: 1.0)
    assert R.road_camber_score(outer_pos, 4.0, inner_positive_weight=3.0) == \
        pytest.approx(R.road_camber_score(outer_pos, 4.0))
    # -0.5 is above a -1 target: penalised 3x, even though it is negative.
    inner = _ramp(outer_cam=lambda u: -1.0, inner_cam=lambda u: -0.5)
    assert R.road_camber_score(inner, 4.0, target=-1.0,
                               inner_positive_weight=3.0) == \
        pytest.approx(math.sqrt(3.0 * 0.25 / 5.0))


def test_sign_change_integrates_exactly() -> None:
    # g(u) = 2u - 1 (crossing at u = 0.5): mean of g^2 is 1/3 per half, so the
    # weighted mean square is 3 * 1/6 + 1/6 = 2/3. n = 400 puts the crossing
    # between frames, so it is only right if the crossing is inserted.
    analysis = _ramp(n=400, inner_cam=lambda u: 2.0 * u - 1.0)
    assert R.road_camber_score(analysis, 4.0, inner_positive_weight=3.0) == \
        pytest.approx(math.sqrt((2.0 / 3.0) / 5.0), rel=1e-4)


# --- SWEEP_LIMITS ------------------------------------------------------------

def test_limits_form_detection() -> None:
    assert S._limits_form("01", {"start": -50, "stop": 50}, RANGE_GROUPS) == "span"
    assert S._limits_form("10", {"rack": (0, 35)}, RANGE_GROUPS) == "drives"
    with pytest.raises(ValueError, match="both 'start' and 'stop'"):
        S._limits_form("01", {"start": -50}, RANGE_GROUPS)
    with pytest.raises(ValueError, match="mixes or misnames"):
        S._limits_form("10", {"start": 0, "stop": 1, "rack": (0, 3)}, RANGE_GROUPS)
    with pytest.raises(ValueError, match="mixes or misnames"):
        S._limits_form("10", {"steer": (0, 3)}, RANGE_GROUPS)


def test_override_merges_per_side_and_keeps_the_rest() -> None:
    entry = {"steps": 65, "travel": {"left": [0, 25], "right": [0, -25]},
             "rack": [0, 35]}
    merged = S._override_drives(
        "10", entry, {"travel": {"left": (0.0, 30.0)}, "rack": (0.0, 20.0)})
    assert merged["travel"] == {"left": [0.0, 30.0], "right": [0, -25]}
    assert merged["rack"] == [0.0, 20.0]
    assert entry["travel"]["left"] == [0, 25]  # run.yaml's entry is untouched


def test_override_refuses_undriven_key_and_file_sweeps() -> None:
    with pytest.raises(ValueError, match="does not drive 'damper'"):
        S._override_drives("10", {"travel": {}, "rack": [0, 1]},
                           {"damper": {"left": (0, 1)}})
    with pytest.raises(ValueError, match="`file:` sweep"):
        S._override_drives("x", {"file": "sweeps/x.yaml"}, {"rack": (0, 1)})


def test_single_span_refused_on_multi_drive_sweep() -> None:
    spec = {"targets": [
        {"type": "point", "start": 0, "stop": 25},
        {"type": "point", "start": 0, "stop": -25},
        {"type": "actuator_position", "start": 0, "stop": 35},
    ]}
    with pytest.raises(ValueError, match="moves 2 kinds of drive"):
        S._check_single_drive("10_corner_ramp", spec)
    # Both wheels moving (01, 02) and a held rack is fine.
    spec["targets"][2]["stop"] = 0
    S._check_single_drive("02_roll", spec)


def test_travel_ends_reads_both_forms() -> None:
    assert R._travel_ends({"start": -50.8, "stop": 50.8}) == [-50.8, 50.8]
    assert R._travel_ends(
        {"travel": {"left": (0, 25), "right": (0, -25)}, "rack": (0, 35)}
    ) == [-25.0, 25.0]
    assert R._travel_ends({"rack": (0, 35)}) == []
