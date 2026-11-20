"""Quasi-static steady corner (Working/sweep_sets/corner.py).

Checks are against things that do not depend on corner.py's own algebra:
statics identities, a straight-running step, the closed-form linear roll
gradient, and an independent re-solve of the targets it produces.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SWEEP_SETS = REPO_ROOT / "Working" / "sweep_sets"
AURORA = REPO_ROOT / "Working" / "models" / "aurora"


def _load_corner():
    if str(SWEEP_SETS) not in sys.path:
        sys.path.insert(0, str(SWEEP_SETS))
    spec = importlib.util.spec_from_file_location("corner", SWEEP_SETS / "corner.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["corner"] = module
    spec.loader.exec_module(module)
    return module


corner = _load_corner()

BASE = dict(
    mode="full",
    turn="right",
    speed=8.0,
    radius=[math.inf, 15.0],
    steps=5,
    rack_limit=35,
    roll_gravity=True,
    pitch=True,
    fy_split="load",
    mu=1.0,
    tolerance={"travel": 0.01, "rack": 0.01},
    max_iterations=20,
)


@pytest.fixture(scope="module")
def aurora():
    from kinematics.core.input import build_suspension

    data = yaml.safe_load((AURORA / "front.yaml").read_text())
    vehicle = corner.load_vehicle(data, AURORA / "forces.yaml")
    return build_suspension(data), data, vehicle


def _settings(**changes):
    return corner.parse_settings("test", {**BASE, **changes})


def _total(vehicle):
    m = vehicle.m_s + 2 * vehicle.m_uf + vehicle.m_ur
    b = vehicle.wheelbase + vehicle.cg[0]
    return m, b


def test_settings_name_the_missing_key() -> None:
    block = dict(BASE)
    del block["speed"]
    with pytest.raises(corner.CornerError, match="speed"):
        corner.parse_settings("x", block)


def test_settings_reject_an_unknown_mode() -> None:
    with pytest.raises(corner.CornerError, match="mode"):
        _settings(mode="slow")


def test_schema_takes_an_optional_mass_split_and_wheel_rate() -> None:
    from kinematics.core.schema.loads import VehicleMassConfig

    plain = VehicleMassConfig(mass=285, g=9.81)
    assert plain.sprung_mass is None and plain.wheel_rate_front is None
    assert "wheel_rate_front" not in plain.model_dump()
    with pytest.raises(ValueError):
        VehicleMassConfig(mass=285, g=9.81, wheel_rate_front=-1)


@pytest.mark.parametrize("mode", ["fast", "full"])
def test_straight_running_step_is_the_design_state(aurora, mode) -> None:
    suspension, data, vehicle = aurora
    first = corner.resolve(suspension, data, vehicle, _settings(), mode=mode).rows[0]
    assert first["a_y"] == 0.0
    assert abs(first["rack"]) < 1e-9
    assert abs(first["travel_left"]) < 1e-4 and abs(first["travel_right"]) < 1e-4
    m, b = _total(vehicle)
    front = m * vehicle.g * b / vehicle.wheelbase
    assert first["tyre_fz_left"] + first["tyre_fz_right"] == pytest.approx(
        front, rel=1e-6
    )


def test_tyre_loads_balance_the_turn(aurora) -> None:
    """Front-axle vertical sum and roll moment from whole-car statics."""
    suspension, data, vehicle = aurora
    settings = _settings(pitch=False, roll_gravity=False)
    model = corner._build_model(suspension, vehicle, settings)
    last = corner.resolve(suspension, data, vehicle, settings, mode="fast").rows[-1]
    m, b = _total(vehicle)
    assert last["tyre_fz_left"] + last["tyre_fz_right"] == pytest.approx(
        m * vehicle.g * b / vehicle.wheelbase, rel=1e-6
    )
    # right turn: left is outer; y_cg is +left
    moment = m * vehicle.g * vehicle.cg[1] + m * last["a_y"] * vehicle.cg[2]
    difference = last["tyre_fz_left"] - last["tyre_fz_right"]
    assert difference * model.t0 / 2 == pytest.approx(moment, rel=1e-6)


def test_fast_matches_the_linear_roll_gradient(aurora) -> None:
    """Fast mode is the textbook steady roll with gravity, for a constant k_w.

    phi = m_c (h_c - h_ra) a_y / (K_phi - m_c g (h_c - h_ra)),  K_phi = k_w t0^2/2
    """
    suspension, data, vehicle = aurora
    settings = _settings(radius=[math.inf, 300.0], steps=2, pitch=False)
    model = corner._build_model(suspension, vehicle, settings)
    last = corner.resolve(suspension, data, vehicle, settings, mode="fast").rows[-1]
    arm = model.m_c * (model.h_c - model.h_ra)  # kg mm
    k_phi = 0.5 * vehicle.k_w * model.t0**2  # N mm / rad
    expected = arm * last["a_y"] / (k_phi - arm * vehicle.g)
    assert math.radians(last["roll_deg"]) == pytest.approx(expected, rel=1e-3)


def test_full_mode_satisfies_its_own_equations_when_re_solved(aurora) -> None:
    """Re-solve the produced spec independently; steer and spring balance hold."""
    suspension, data, vehicle = aurora
    settings = _settings()
    result = corner.resolve(suspension, data, vehicle, settings, mode="full")
    assert not result.warnings
    model = corner._build_model(suspension, vehicle, settings)
    steps = corner._turn_kinematics(model)
    targets = result.spec["targets"]
    rack = targets[2]["values"]
    travel = {"left": targets[0]["values"], "right": targets[1]["values"]}
    solved = corner._solve(suspension, rack, travel)
    for k, step in enumerate(steps):
        delta_o = math.radians(-solved["left"]["steer"][k])
        delta_i = math.radians(-solved["right"]["steer"][k])
        effective = corner._effective_steer(np.array(delta_o), np.array(delta_i))
        assert float(effective) == pytest.approx(step["delta_target"], abs=2e-4)
        track = float(solved["track"][k])
        z = {side: float(solved[side]["travel"][k]) for side in ("left", "right")}
        phi = math.atan((z["left"] - z["right"]) / track)
        loads = corner._tyre_loads(model, step, phi, track)
        for side, sigma in (("left", -1.0), ("right", 1.0)):
            wheel = (
                loads["fz"][side]
                + sigma * loads["fy"][side] * float(solved[side]["scrub"][k])
                - vehicle.m_uf * vehicle.g
            )
            spring = model.w_sc[side] + vehicle.k_w * z[side]
            assert spring == pytest.approx(wheel, abs=vehicle.k_w * 0.02)


def test_fast_and_full_agree_at_small_lateral_acceleration(aurora) -> None:
    """Near straight running the design roll centre is the solved one.

    The two modes differ by design in one more place: fast sends the front
    unsprung transfer straight to the tyres (textbook roll-centre split), full
    lets virtual work decide, and for an independent suspension that load
    mostly reaches the spring. With the front unsprung mass moved into the
    sprung mass, that difference goes away and the modes must agree.
    """
    import dataclasses

    suspension, data, vehicle = aurora
    light = dataclasses.replace(
        vehicle, m_uf=0.01, m_s=vehicle.m_s + 2 * (vehicle.m_uf - 0.01)
    )
    settings = _settings(radius=[math.inf, 300.0], steps=2)
    fast = corner.resolve(suspension, data, light, settings, mode="fast").rows[-1]
    full = corner.resolve(suspension, data, light, settings, mode="full").rows[-1]
    for side in ("left", "right"):
        assert fast[f"travel_{side}"] == pytest.approx(full[f"travel_{side}"], rel=0.02)


def test_a_radius_inside_the_wheelbase_has_no_steady_turn(aurora) -> None:
    suspension, data, vehicle = aurora
    with pytest.raises(corner.CornerError, match="no steady turn"):
        corner.resolve(
            suspension, data, vehicle, _settings(radius=[math.inf, 1.0]), mode="fast"
        )


def test_runner_rejects_drive_keys_beside_a_corner(tmp_path) -> None:
    path = SWEEP_SETS / "runner.py"
    runner_spec = importlib.util.spec_from_file_location("_runner_corner", path)
    runner = importlib.util.module_from_spec(runner_spec)
    sys.modules["_runner_corner"] = runner
    runner_spec.loader.exec_module(runner)
    config = yaml.safe_load((SWEEP_SETS / "front" / "run.yaml").read_text())
    config["geometry"] = str(AURORA / "front.yaml")
    config["sweeps"] = {
        "c": {
            "run": True,
            "report": True,
            "plots": "all",
            "corner": dict(BASE),
            "rack": [0, 1],
        }
    }
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(yaml.safe_dump(config))
    with pytest.raises(runner.SweepSetError, match="corner"):
        runner.plan_sweep_set(run_yaml, runner.SweepOptions(dry_run=True))
