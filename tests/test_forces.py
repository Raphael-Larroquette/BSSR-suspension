"""Static force solve.

The load-distribution cases are checked against the closed-form transfer
formulas rather than against the code's own output, and the linkage solve is
checked against an independently assembled 20x20 system for the Aurora front
left corner. The remaining cases are invariants -- symmetry, per-part
equilibrium, and policy invariance -- that hold whatever the geometry is.
"""

from pathlib import Path

import numpy as np
import pytest
import yaml

from kinematics.cli.commands.forces import build_options, describe, load_inputs
from kinematics.cli.io.cases_loader import load_cases
from kinematics.cli.io.force_writer import ForceWriteOptions, write_forces
from kinematics.cli.io.forces_loader import load_forces_config
from kinematics.cli.io.loaders import load_geometry
from kinematics.core.enums import AxlePosition, OutputFrame, WheelLiftPolicy
from kinematics.core.loads.cases import LoadCase
from kinematics.core.loads.distribution import solve_patch_loads
from kinematics.core.loads.main import (
    ForceModelOptions,
    base_joint_name,
    part_residuals,
    solve_forces,
)
from kinematics.core.loads.structure import build_force_graph
from kinematics.core.loads.system import (
    ExternalLoad,
    MomentReference,
    SolveOptions,
    assemble,
    solve_subsystem,
)
from kinematics.core.loads.vehicle import build_vehicle
from kinematics.core.primitives.point_ref import Side

GRAVITY = 9.80665
MASS = 294.0

# Force on the named part at each joint, per 1000 N of vertical load at the
# front-left contact patch, from an independently assembled system.
GOLDEN_PER_KILONEWTON = {
    "upper_wishbone_inboard_front": (-15.713018, 129.341119, 6.918475),
    "upper_wishbone_inboard_rear": (-15.713018, 67.634405, 3.617774),
    "upper_wishbone_outboard": (31.426036, -196.975524, -10.536248),
    "lower_wishbone_inboard_front": (23.783241, -748.424010, 647.354675),
    "lower_wishbone_inboard_rear": (23.783241, -113.945768, 155.365122),
    "lower_wishbone_outboard": (-47.566483, 96.789681, 1004.850246),
}


@pytest.fixture
def suspensions(aurora_dir: Path):
    return (
        load_geometry(aurora_dir / "front.yaml"),
        load_geometry(aurora_dir / "rear.yaml"),
    )


@pytest.fixture
def vehicle(suspensions):
    return build_vehicle(suspensions, MASS, GRAVITY)


def normals(vehicle, case):
    return {load.patch.name: load.normal for load in solve_patch_loads(vehicle, case)}


def part_rows(run, part):
    return [
        row for block in run.solution.blocks if block.part == part for row in block.rows
    ]


def load_named(row, name):
    return next(load for load in row.loads if load.name == name)


# --------------------------------------------------------------------------
# Load distribution
# --------------------------------------------------------------------------
def test_static_normal_loads_sum_to_vehicle_weight(vehicle):
    total = sum(normals(vehicle, LoadCase(1, 0, 0)).values())
    assert total == pytest.approx(vehicle.weight)


def test_longitudinal_transfer_matches_the_closed_form(vehicle):
    static = normals(vehicle, LoadCase(1, 0, 0))
    braking = normals(vehicle, LoadCase(1, 1, 0))
    front = sum(value for name, value in braking.items() if name.startswith("front"))
    front_static = sum(
        value for name, value in static.items() if name.startswith("front")
    )
    expected = vehicle.cg_height / vehicle.wheelbase * vehicle.weight
    assert front - front_static == pytest.approx(expected)


def test_lateral_transfer_matches_the_closed_form_and_spares_the_rear(vehicle):
    static = normals(vehicle, LoadCase(1, 0, 0))
    cornering = normals(vehicle, LoadCase(1, 0, 1))
    track = vehicle.track(AxlePosition.FRONT)
    expected = vehicle.cg_height / track * vehicle.weight
    assert cornering["front_left"] - static["front_left"] == pytest.approx(expected)
    # A centreline rear wheel has no moment arm about X, so cornering cannot
    # change its normal load at all.
    assert cornering["rear"] == pytest.approx(static["rear"])


def test_horizontal_force_is_shared_in_proportion_to_normal_load(vehicle):
    loads = solve_patch_loads(vehicle, LoadCase(2, 1, 0))
    total_normal = sum(load.normal for load in loads)
    for load in loads:
        share = load.normal / total_normal
        assert load.force[0] == pytest.approx(-share * vehicle.weight)


def test_zero_bump_case_is_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        LoadCase(0, 0, 1)


def test_wheel_lift_is_flagged_and_the_loaded_side_still_solves(suspensions):
    run = solve_forces(suspensions, [LoadCase(1, 0, 1.2)], MASS, GRAVITY)
    assert any("lifted" in issue for issue in run.solution.diagnostics)
    flagged = [row for block in run.solution.blocks for row in block.rows if row.flags]
    assert flagged, "a lifted wheel must flag its own corner's rows"
    left = [row for row in part_rows(run, "Upright") if row.side is Side.LEFT]
    assert load_named(left[0], "wheel_contact_centre").force[2] > 0.0


def test_wheel_lift_can_be_made_fatal(suspensions):
    options = ForceModelOptions(on_wheel_lift=WheelLiftPolicy.FAIL)
    with pytest.raises(ValueError, match="lifted"):
        solve_forces(suspensions, [LoadCase(1, 0, 1.2)], MASS, GRAVITY, options)


# --------------------------------------------------------------------------
# Structural graph
# --------------------------------------------------------------------------
def test_axle_and_wheel_are_welded_into_the_upright(suspensions):
    graph = build_force_graph(suspensions[0])
    names = {body.name for body in graph.bodies}
    assert "Left Axle" not in names and "Left Wheel" not in names
    upright = next(body for body in graph.bodies if body.name == "Left Upright")
    assert any("WHEEL_CONTACT_CENTRE" in point.name for point in upright.points)


def test_the_rack_is_grounded_so_the_front_corners_are_independent(suspensions):
    graph = build_force_graph(suspensions[0])
    assert {subsystem.name for subsystem in graph.subsystems} == {"left", "right"}


def test_the_spring_pickups_reach_the_parts_that_carry_them(suspensions):
    # Covered in detail by tests/test_rigid_attachments.py; here it is the
    # difference between a solvable graph and a damper reacting against
    # nothing, so the force graph asserts it too.
    front = build_force_graph(suspensions[0])
    wishbone = next(body for body in front.bodies if body.name == "Left Lower Wishbone")
    assert any(point.name == "LEFT_STRUT_BOTTOM" for point in wishbone.points)

    rear = build_force_graph(suspensions[1])
    arm = next(body for body in rear.bodies if body.name == "Semi-Trailing Arm")
    assert any(point.name == "STRUT_BOTTOM" for point in arm.points)


def test_coaxial_pivot_pairs_are_found_without_being_declared(suspensions, vehicle):
    run = solve_forces(suspensions, [LoadCase(1, 0, 0)], MASS, GRAVITY)
    left = next(corner for corner in run.corners if corner.subsystem.name == "left")
    found = {
        tuple(sorted(joint.name for joint in pair.joints))
        for pair in left.catalog.coaxial
    }
    assert found == {
        ("left_lower_wishbone_inboard_front", "left_lower_wishbone_inboard_rear"),
        ("left_upper_wishbone_inboard_front", "left_upper_wishbone_inboard_rear"),
    }


def test_every_subsystem_is_square_and_full_rank(suspensions):
    run = solve_forces(suspensions, [LoadCase(1, 0, 0)], MASS, GRAVITY)
    for corner in run.corners:
        matrix, _ = assemble(corner.catalog, (), SolveOptions())
        assert matrix.shape[0] == matrix.shape[1]
        assert np.linalg.matrix_rank(matrix) == matrix.shape[0]


# --------------------------------------------------------------------------
# Solved forces
# --------------------------------------------------------------------------
def test_front_left_corner_matches_an_independent_solve(suspensions, vehicle):
    run = solve_forces(suspensions, [LoadCase(1, 0, 0)], MASS, GRAVITY)
    normal = normals(vehicle, LoadCase(1, 0, 0))["front_left"]
    scale = normal / 1000.0

    for part in ("Upper Wishbone", "Lower Wishbone"):
        row = next(row for row in part_rows(run, part) if row.side is Side.LEFT)
        for load in row.loads:
            if load.name not in GOLDEN_PER_KILONEWTON:
                continue
            expected = np.array(GOLDEN_PER_KILONEWTON[load.name]) * scale
            assert load.force == pytest.approx(expected, rel=1e-9, abs=1e-6)


def test_every_part_is_in_equilibrium(suspensions, aurora_dir):
    cases = load_cases(aurora_dir / "cases.csv")
    run = solve_forces(suspensions, cases, MASS, GRAVITY)
    for block in run.solution.blocks:
        scale = max(
            float(np.max(np.abs(load.force)))
            for row in block.rows
            for load in row.loads
        )
        for row in block.rows:
            force, moment = part_residuals(row)
            assert force == pytest.approx(0.0, abs=1e-6 * max(scale, 1.0))
            assert moment == pytest.approx(0.0, abs=1e-3 * max(scale, 1.0))


def test_chassis_reactions_close_on_the_contact_patch(suspensions):
    run = solve_forces(suspensions, [LoadCase(2, 1, 1)], MASS, GRAVITY)
    corner = next(item for item in run.corners if item.subsystem.name == "left")
    ground = {
        base_joint_name(joint.name)
        for joint in corner.subsystem.joints
        if any(name == "Chassis" for name in joint.bodies)
    }

    reactions = np.zeros(3)
    applied = np.zeros(3)
    for block in run.solution.blocks:
        for row in block.rows:
            if row.side is not Side.LEFT:
                continue
            for load in row.loads:
                if load.applied:
                    applied += load.force
                elif load.name in ground:
                    reactions += load.force
    # Nothing else enters or leaves the corner, so what the chassis hands the
    # linkage is exactly the tyre force, reversed.
    assert reactions == pytest.approx(-applied, abs=1e-6)


def test_two_force_members_are_equal_and_opposite(suspensions):
    run = solve_forces(suspensions, [LoadCase(2, 1, 1)], MASS, GRAVITY)
    for part in ("Track Rod", "Front Spring/Damper"):
        for row in part_rows(run, part):
            first, second = row.loads
            assert first.force == pytest.approx(-second.force, abs=1e-9)


def test_the_two_front_corners_are_mirror_images(suspensions):
    # The authored centre of gravity is off the centreline, so the two corners
    # never see the same load. Feed both the same force, mirrored, and the
    # linkage itself must mirror -- which is the sign convention under test.
    run = solve_forces(suspensions, [LoadCase(1, 0, 0)], MASS, GRAVITY)
    corners = {item.subsystem.name: item for item in run.corners}
    force = np.array([300.0, 200.0, 1000.0])

    solved = {}
    for name, mirror in (("left", 1.0), ("right", -1.0)):
        corner = corners[name]
        solved[name] = solve_subsystem(
            corner.catalog,
            externals=(
                ExternalLoad(
                    body=corner.loaded_body.name,
                    name=corner.patch.point_name,
                    position=corner.patch.position,
                    force=force * np.array([1.0, mirror, 1.0]),
                ),
            ),
        )

    for name, value in solved["left"].forces.items():
        partner = solved["right"].forces["right" + name.removeprefix("left")]
        assert value == pytest.approx(
            partner * np.array([1.0, -1.0, 1.0]), rel=1e-9, abs=1e-6
        )


def test_axial_policy_changes_only_the_axial_split(suspensions):
    even = solve_forces(suspensions, [LoadCase(2, 1, 1)], MASS, GRAVITY)
    carried = solve_forces(
        suspensions,
        [LoadCase(2, 1, 1)],
        MASS,
        GRAVITY,
        ForceModelOptions(
            axial_overrides={"Lower Wishbone": "lower_wishbone_inboard_front"}
        ),
    )
    row_even = next(
        row for row in part_rows(even, "Lower Wishbone") if row.side is Side.LEFT
    )
    row_carried = next(
        row for row in part_rows(carried, "Lower Wishbone") if row.side is Side.LEFT
    )
    for load_even, load_carried in zip(row_even.loads, row_carried.loads):
        if load_even.name.endswith(("inboard_front", "inboard_rear")):
            # Only the component along the pivot axis is allowed to move.
            assert load_even.force[1] == pytest.approx(load_carried.force[1], abs=1e-6)
            assert load_even.force[2] == pytest.approx(load_carried.force[2], abs=1e-6)
        else:
            assert load_even.force == pytest.approx(load_carried.force, abs=1e-6)

    front_even = load_named(row_even, "lower_wishbone_inboard_front").force[0]
    rear_even = load_named(row_even, "lower_wishbone_inboard_rear").force[0]
    assert front_even == pytest.approx(rear_even, abs=1e-6)

    rear_carried = load_named(row_carried, "lower_wishbone_inboard_rear").force[0]
    assert rear_carried == pytest.approx(0.0, abs=1e-6)


def test_moment_reference_does_not_change_the_answer(suspensions):
    centroid = solve_forces(suspensions, [LoadCase(2, 1, 1)], MASS, GRAVITY)
    origin = solve_forces(
        suspensions,
        [LoadCase(2, 1, 1)],
        MASS,
        GRAVITY,
        ForceModelOptions(solve=SolveOptions(moment_reference=MomentReference.ORIGIN)),
    )
    for block_a, block_b in zip(centroid.solution.blocks, origin.solution.blocks):
        for row_a, row_b in zip(block_a.rows, block_b.rows):
            for load_a, load_b in zip(row_a.loads, row_b.loads):
                assert load_a.force == pytest.approx(load_b.force, rel=1e-6, abs=1e-6)
    # ...but it does change the conditioning, which is why centroid is default.
    assert centroid.solution.max_condition < origin.solution.max_condition


# --------------------------------------------------------------------------
# Configuration and input files
# --------------------------------------------------------------------------
def test_the_shipped_aurora_configuration_solves(aurora_dir):
    loaded = load_inputs(aurora_dir / "forces.yaml")
    assert len(loaded.cases) == 4
    assert len(loaded.run.corners) == 3
    assert "coaxial" in describe(loaded)


def test_a_missing_configuration_key_is_named(aurora_dir, tmp_path):
    data = yaml.safe_load((aurora_dir / "forces.yaml").read_text())
    del data["solve"]["rack"]
    path = tmp_path / "forces.yaml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="solve.rack: required key is missing"):
        load_forces_config(path)


def test_an_unknown_configuration_key_is_named(aurora_dir, tmp_path):
    data = yaml.safe_load((aurora_dir / "forces.yaml").read_text())
    data["solve"]["pivot_axail"] = "even"
    path = tmp_path / "forces.yaml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="pivot_axail: unknown key"):
        load_forces_config(path)


def test_unimplemented_policies_say_so(aurora_dir, tmp_path):
    for section, key, value, message in (
        ("solve", "rack", "floating", "not implemented"),
        ("solve", "brake_torque_reaction", "sprung", "not implemented"),
    ):
        data = yaml.safe_load((aurora_dir / "forces.yaml").read_text())
        data[section][key] = value
        path = tmp_path / f"{key}.yaml"
        path.write_text(yaml.safe_dump(data))
        with pytest.raises(ValueError, match=message):
            load_forces_config(path)


def test_case_files_reject_unknown_columns(tmp_path):
    path = tmp_path / "cases.csv"
    path.write_text("bump,brake,corner,wind\n1,0,0,0\n")
    with pytest.raises(ValueError, match="unexpected column"):
        load_cases(path)


def test_case_files_name_the_offending_row(tmp_path):
    path = tmp_path / "cases.csv"
    path.write_text("# a comment\nbump,brake,corner\n1,0,0\n0,0,1\n")
    with pytest.raises(ValueError, match="data row 3"):
        load_cases(path)


def test_case_comments_are_ignored_anywhere(aurora_dir):
    cases = load_cases(aurora_dir / "cases.csv")
    assert cases[0] == LoadCase(2, 1, 1)


def test_configuration_maps_onto_solver_options(aurora_dir):
    options = build_options(load_forces_config(aurora_dir / "forces.yaml"))
    assert options.axial_default == "even"
    assert options.solve.moment_reference is MomentReference.CENTROID
    assert "Steering Rack" in options.structure.ground


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def test_written_blocks_carry_the_applied_tyre_force(suspensions, tmp_path):
    run = solve_forces(suspensions, [LoadCase(2, 1, 1)], MASS, GRAVITY)
    path = tmp_path / "forces.csv"
    write_forces(run.solution, path)
    text = path.read_text()
    assert "PART:,Upright" in text
    assert "wheel_contact_centre (applied)" in text
    # No joint carries a moment under the current model, so 'auto' emits none.
    assert ",mx," not in text


def test_part_frame_mirrors_the_right_side(suspensions, tmp_path):
    run = solve_forces(suspensions, [LoadCase(2, 1, 1)], MASS, GRAVITY)
    vehicle_path = tmp_path / "vehicle.csv"
    part_path = tmp_path / "part.csv"
    write_forces(run.solution, vehicle_path)
    write_forces(run.solution, part_path, ForceWriteOptions(frame=OutputFrame.PART))

    def right_row(path: Path) -> list[str]:
        for line in path.read_text().splitlines():
            if line.startswith("2,1,1,right"):
                return line.split(",")
        raise AssertionError("no right-side row written")

    vehicle_row = right_row(vehicle_path)
    part_row = right_row(part_path)
    assert float(part_row[5]) == pytest.approx(-float(vehicle_row[5]))
    assert float(part_row[4]) == pytest.approx(float(vehicle_row[4]))


def test_unsupported_output_format_is_rejected(suspensions, tmp_path):
    run = solve_forces(suspensions, [LoadCase(1, 0, 0)], MASS, GRAVITY)
    with pytest.raises(ValueError, match="Unsupported force output format"):
        write_forces(run.solution, tmp_path / "forces.txt")
