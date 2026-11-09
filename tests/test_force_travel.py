"""Static force solve at a pose, and along a solved sweep.

The load is the constant case load: found at design, applied at the posed
contact patch. The checks are invariants of that statement: at the design pose
nothing changes, every step is in equilibrium, and on a direct-acting arm the
damper force follows from virtual work (F_damper = F_wheel / IR) with IR taken
from the sweep geometry alone.
"""

import csv
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from kinematics.cli.commands.forces import run_force_travel
from kinematics.cli.io.force_writer import FORCE_TRAVEL_COLUMNS
from kinematics.cli.io.loaders import load_geometry
from kinematics.core.enums import AxlePosition, PointID
from kinematics.core.input import build_sweep
from kinematics.core.loads.cases import LoadCase
from kinematics.core.loads.main import solve_forces
from kinematics.core.loads.travel import solve_forces_over_travel
from kinematics.core.primitives.geometry import extract_array
from kinematics.core.sweep import solve_evaluated_sweep

GRAVITY = 9.80665
MASS = 294.0
REAR = 1
STEPS = 9
TRAVEL = 50.8
WORKING = Path(__file__).resolve().parents[1] / "Working"


@pytest.fixture
def suspensions(aurora_dir: Path):
    return [
        load_geometry(aurora_dir / "front.yaml"),
        load_geometry(aurora_dir / "rear.yaml"),
    ]


@pytest.fixture
def rear_states(suspensions):
    sweep = build_sweep(
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
        suspensions[REAR],
    )
    return solve_evaluated_sweep(suspensions[REAR], sweep).states


def _loads(run, part):
    block = next(b for b in run.solution.blocks if b.part == part)
    return {load.name: load for load in block.rows[0].loads}


def test_design_pose_reproduces_the_static_solve(suspensions):
    cases = [LoadCase(2, 1, 1), LoadCase(6, 0, 0)]
    static = solve_forces(suspensions, cases, MASS, GRAVITY)
    posed = solve_forces(
        suspensions,
        cases,
        MASS,
        GRAVITY,
        poses=[None, suspensions[REAR].initial_state()],
    )
    for a, b in zip(static.solution.blocks, posed.solution.blocks):
        for row_a, row_b in zip(a.rows, b.rows):
            for load_a, load_b in zip(row_a.loads, row_b.loads):
                np.testing.assert_allclose(load_a.force, load_b.force, atol=1e-9)
                np.testing.assert_allclose(load_a.position, load_b.position)


def test_pose_count_must_match(suspensions):
    with pytest.raises(ValueError, match="pose"):
        solve_forces(suspensions, [LoadCase(1, 0, 0)], MASS, GRAVITY, poses=[None])


def test_only_the_moving_axle_is_reported(suspensions, rear_states):
    travel = solve_forces_over_travel(
        suspensions, REAR, rear_states, [LoadCase(6, 0, 0)], MASS, GRAVITY
    )
    assert travel.axle is AxlePosition.REAR
    assert travel.steps == STEPS
    assert {row.loads.axle for row in travel.rows} == {AxlePosition.REAR}
    steps = sorted({row.step for row in travel.rows})
    assert steps == list(range(STEPS))
    travels = sorted({round(row.wheel_travel, 6) for row in travel.rows})
    np.testing.assert_allclose(travels, np.linspace(-TRAVEL, TRAVEL, STEPS), atol=1e-6)


def test_every_step_is_in_equilibrium_with_the_constant_case_load(
    suspensions, rear_states
):
    case = LoadCase(6, 0, 0)
    static = solve_forces(suspensions, [case], MASS, GRAVITY)
    tyre_static = _loads(static, "Semi-Trailing Arm")["wheel_contact_centre"].force
    travel = solve_forces_over_travel(
        suspensions, REAR, rear_states, [case], MASS, GRAVITY
    )
    for step, state in enumerate(rear_states):
        patch = extract_array(state.get(PointID.WHEEL_CONTACT_CENTRE))
        rows = [r.loads for r in travel.rows if r.step == step]
        arm = next(r for r in rows if r.part == "Semi-Trailing Arm")
        tyre = next(load for load in arm.loads if load.applied)
        np.testing.assert_allclose(tyre.force, tyre_static)  # constant load
        np.testing.assert_allclose(tyre.position, patch)  # posed patch
        chassis = next(r for r in rows if r.part == "Rear Chassis")
        force = tyre.force - sum(load.force for load in chassis.loads)
        moment = np.cross(tyre.position, tyre.force) - sum(
            np.cross(load.position, load.force) for load in chassis.loads
        )
        assert np.abs(force).max() < 1e-6
        assert np.abs(moment).max() < 1e-3


def test_damper_force_follows_virtual_work(suspensions, rear_states):
    """On a direct-acting arm, |F_damper| = F_z / IR at every step.

    IR = -d(damper length)/d(wheel z) is taken from the posed geometry by
    central differences, so this checks the solve against kinematics alone.
    """
    case = LoadCase(6, 0, 0)
    travel = solve_forces_over_travel(
        suspensions, REAR, rear_states, [case], MASS, GRAVITY
    )

    def length(state):
        top = extract_array(state.get(PointID.STRUT_TOP))
        bottom = extract_array(state.get(PointID.STRUT_BOTTOM))
        return float(np.linalg.norm(top - bottom))

    def wheel_z(state):
        return float(extract_array(state.get(PointID.WHEEL_CENTER))[2])

    for step in range(1, STEPS - 1):
        before, after = rear_states[step - 1], rear_states[step + 1]
        ir = -(length(after) - length(before)) / (wheel_z(after) - wheel_z(before))
        rows = [r.loads for r in travel.rows if r.step == step]
        arm = next(r for r in rows if r.part == "Semi-Trailing Arm")
        tyre = next(load for load in arm.loads if load.applied)
        damper = next(load for load in arm.loads if load.name == "strut_bottom")
        # central differences on a 12.7 mm step: allow 0.5 %
        assert np.linalg.norm(damper.force) == pytest.approx(
            tyre.force[2] / ir, rel=5e-3
        )


def test_run_force_travel_writes_one_row_per_joint_per_step(
    suspensions, rear_states, aurora_dir, tmp_path
):
    out = tmp_path / "01_bump_forces.csv"
    travel = run_force_travel(
        aurora_dir / "forces.yaml",
        suspensions[REAR],
        rear_states,
        [LoadCase(6, 0, 0), LoadCase(2, 1, 0)],
        out,
    )
    with out.open(newline="") as handle:
        rows = list(csv.reader(handle))
    assert tuple(rows[0]) == FORCE_TRAVEL_COLUMNS
    expected = sum(
        sum(1 for load in r.loads.loads if not load.applied) for r in travel.rows
    )
    assert len(rows) - 1 == expected
    joints = {(r[6], r[7]) for r in rows[1:]}
    assert ("Rear Chassis", "strut_top") in joints
    assert ("Semi-Trailing Arm", "wheel_contact_centre") not in joints
    assert {(r[2], r[3], r[4]) for r in rows[1:]} == {("6", "0", "0"), ("2", "1", "0")}
    assert "-0.0" not in out.read_text()


# --------------------------------------------------------------------------
# run.yaml `forces:` and the sweep task
# --------------------------------------------------------------------------
@pytest.fixture
def runner_module():
    sys.path.insert(0, str(WORKING / "sweep_sets"))
    try:
        import runner

        yield runner
    finally:
        sys.path.remove(str(WORKING / "sweep_sets"))


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ([[0, 0, 0]], "must be > 0"),
        ([[6, 0]], "not three numbers"),
        ([[6, True, 0]], "not three numbers"),
        ("6,0,0", "must be a list"),
        ([], "must be a list"),
    ],
)
def test_force_cases_are_validated(runner_module, value, message):
    with pytest.raises(runner_module.SweepSetError, match=message):
        runner_module.parse_force_cases("01_bump", value)


def test_reporter_never_reads_the_forces_table_as_a_sweep(runner_module):
    sys.path.insert(0, str(WORKING / "sweep_sets"))
    try:
        import susreport_common
    finally:
        sys.path.remove(str(WORKING / "sweep_sets"))
    assert susreport_common.FORCES_TABLE_SUFFIX == runner_module.FORCES_SUFFIX


def test_force_cases_parse(runner_module):
    assert runner_module.parse_force_cases("01", None) == []
    assert runner_module.parse_force_cases("01", [[6, 0, 0], [2, 1, -1.5]]) == [
        (6.0, 0.0, 0.0),
        (2.0, 1.0, -1.5),
    ]


def test_sweep_task_writes_forces_and_reports_failures(
    suspensions, rear_states, aurora_dir, tmp_path
):
    sys.path.insert(0, str(WORKING / "sweep_sets"))
    try:
        import tasks
    finally:
        sys.path.remove(str(WORKING / "sweep_sets"))
    run = SimpleNamespace(
        suspension=suspensions[REAR],
        evaluated=SimpleNamespace(states=rear_states),
    )
    payload = {
        "force_cases": [[6, 0, 0]],
        "forces_config": str(aurora_dir / "forces.yaml"),
        "forces_csv": str(tmp_path / "01_bump_forces.csv"),
    }
    out = {"status": "ok"}
    tasks._forces_over_travel(run, payload, out)
    assert out == {"status": "ok"}
    assert (tmp_path / "01_bump_forces.csv").is_file()

    broken = tmp_path / "forces.yaml"
    data = yaml.safe_load((aurora_dir / "forces.yaml").read_text())
    data["vehicle"]["mass"] = -1
    broken.write_text(yaml.safe_dump(data))
    out = {"status": "ok"}
    tasks._forces_over_travel(run, {**payload, "forces_config": str(broken)}, out)
    assert out["status"] == "warn"
    assert out["message"].startswith("forces along travel failed")


def test_report_section_has_one_row_per_joint_and_a_plot(
    suspensions, rear_states, aurora_dir, tmp_path
):
    sys.path.insert(0, str(WORKING / "sweep_sets"))
    try:
        import susreport_common
    finally:
        sys.path.remove(str(WORKING / "sweep_sets"))
    run_force_travel(
        aurora_dir / "forces.yaml",
        suspensions[REAR],
        rear_states,
        [LoadCase(6, 0, 0)],
        tmp_path / f"01_bump{susreport_common.FORCES_TABLE_SUFFIX}.csv",
    )
    lines, plots = susreport_common.forces_section(
        tmp_path, [SimpleNamespace(name="01_bump")], tmp_path / "plots"
    )
    rows = [line for line in lines if line.startswith("| `")]
    # one row per joint, not per part: the strut ends and pivots appear once
    assert sorted(row.split("`")[1] for row in rows) == [
        "strut_bottom",
        "strut_top",
        "trailing_arm_pivot_a",
        "trailing_arm_pivot_b",
    ]
    assert plots == [tmp_path / "plots" / "01_bump_forces.png"]
    assert plots[0].is_file()
    # the damper force rises toward droop on Aurora (IR falls), so its peak
    # is at full droop and above its design value
    strut = next(row for row in rows if "`strut_top`" in row)
    cells = [cell.strip() for cell in strut.split("|")]
    assert cells[5] == f"{-TRAVEL:+.1f}"
    assert float(cells[6]) > 1.0


def test_no_forces_table_no_section(tmp_path):
    sys.path.insert(0, str(WORKING / "sweep_sets"))
    try:
        import susreport_common
    finally:
        sys.path.remove(str(WORKING / "sweep_sets"))
    lines, plots = susreport_common.forces_section(
        tmp_path, [SimpleNamespace(name="01_bump")], tmp_path / "plots"
    )
    assert (lines, plots) == ([], [])
