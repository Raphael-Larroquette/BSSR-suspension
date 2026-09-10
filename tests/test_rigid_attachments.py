"""Rigid attachments reaching the bodies they belong to.

A mechanism pickup that rides a locating member appears in none of that
member's elements, so a topology declares it with ``rigid_attachments()``.
Two ways of losing that declaration both leave the pickup in a body of its
own, where a joint resolves to a single body and a load path stops dead.
"""

from pathlib import Path

from kinematics.cli.io.loaders import load_geometry
from kinematics.core.bodies import build_bodies
from kinematics.core.enums import PointID
from kinematics.core.primitives.point_ref import PointRef, Side


def bodies_for(path: Path):
    suspension = load_geometry(path)
    assembly = suspension.assembly()
    return {
        body.name: set(body.points)
        for body in build_bodies(
            assembly.elements,
            assembly.points.fixed,
            suspension.rigid_attachments(),
        )
    }


def test_a_centreline_trailing_arm_carries_its_spring_pickup(aurora_dir: Path):
    bodies = bodies_for(aurora_dir / "rear.yaml")
    assert PointID.STRUT_BOTTOM in bodies["Semi-Trailing Arm"]


def test_a_sided_trailing_arm_carries_its_spring_pickup(test_data_dir: Path):
    bodies = bodies_for(test_data_dir / "trailing_arm_coilover_geometry.yaml")
    arm = next(name for name in bodies if name.endswith("Semi-Trailing Arm"))
    assert PointID.STRUT_BOTTOM in bodies[arm]


def test_an_axle_side_qualifies_its_corners_attachments(aurora_dir: Path):
    # An axle keys every point on a side, so a corner's attachment has to be
    # requalified rather than passed through or dropped.
    bodies = bodies_for(aurora_dir / "front.yaml")
    for side in (Side.LEFT, Side.RIGHT):
        wishbone = bodies[f"{side.name.title()} Lower Wishbone"]
        assert PointRef(side, PointID.STRUT_BOTTOM) in wishbone


def test_a_corner_and_its_axle_agree_on_the_pickup_carrier(aurora_dir: Path):
    corner = load_geometry(aurora_dir / "front.yaml").corners[Side.LEFT]
    assembly = corner.assembly()
    corner_bodies = {
        body.name: set(body.points)
        for body in build_bodies(
            assembly.elements, assembly.points.fixed, corner.rigid_attachments()
        )
    }
    assert PointID.STRUT_BOTTOM in corner_bodies["Lower Wishbone"]
