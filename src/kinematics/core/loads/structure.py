"""
The structural body graph a force solve is built on.

``build_bodies`` derives the rigid bodies a suspension's elements make up, which
is a kinematic statement: a wheel and an axle are bodies there because they are
groups of points that move together. Structurally they are not separate parts,
and treating them as such invents joints that carry no load and leaves the
system singular.

This module applies a declared policy -- weld, attach, ground, ignore -- to turn
that kinematic body list into a structural one, works out where the joints are,
and splits the result into the independent subsystems a solve runs over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from kinematics.core.bodies import RigidBody, RotationMode, build_bodies
from kinematics.core.enums import PointID
from kinematics.core.primitives.geometry import extract_array
from kinematics.core.primitives.point_ref import (
    PointKey,
    PointRef,
    Side,
    point_key_name,
)
from kinematics.core.suspensions.base import Suspension

# An axle qualifies both corners' body names with the side they belong to.
# Weld and ground rules are written side-agnostically and matched against the
# remainder, so one rule covers both corners.
_SIDE_WORDS: dict[str, Side] = {"left": Side.LEFT, "right": Side.RIGHT}


def slug(name: str) -> str:
    """Normalize a body or point name into a stable match key."""
    return "".join(
        character if character.isalnum() else "_" for character in name.strip().lower()
    ).strip("_")


@dataclass(frozen=True)
class AttachRule:
    """Fold a loose point into whichever body already carries every anchor."""

    point: str
    anchors: tuple[str, ...]


@dataclass(frozen=True)
class StructurePolicy:
    """
    How the kinematic body list becomes a structural one.

    ``weld`` merges bodies into one part. The **first** entry of a group names
    the merged part and must be present for the group to apply at all, so a
    rule written for one architecture is simply inert on another.

    ``ground`` merges a body into the chassis, and ``ignore`` drops it. Both
    take body names; ``attach`` takes a point and the anchors identifying its
    carrier.
    """

    weld: tuple[tuple[str, ...], ...] = ()
    attach: tuple[AttachRule, ...] = ()
    ground: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()


# Bodies that are groups of points but not separate structural parts. The axle
# and wheel are rigid with whichever carrier holds them, and a rack held by the
# steering column cannot translate, so it reacts into the chassis.
DEFAULT_STRUCTURE = StructurePolicy(
    weld=(
        ("Upright", "Axle", "Wheel"),
        ("Semi-Trailing Arm", "Semi-Trailing Arm Carrier", "Axle", "Wheel"),
    ),
    ground=("Steering Rack",),
)


@dataclass(frozen=True)
class ForceBody:
    """One structural part: a named set of points that move rigidly together."""

    name: str
    side: Side
    points: tuple[PointKey, ...]
    is_ground: bool

    @property
    def base_name(self) -> str:
        """Return the part name without its side qualifier."""
        return split_side(self.name)[1]


@dataclass(frozen=True)
class ForceJoint:
    """One point where exactly two structural parts meet."""

    name: str
    point: PointKey
    position: NDArray[np.float64]
    bodies: tuple[str, str]

    def other(self, body: str) -> str:
        """Return the part on the far side of this joint."""
        if body == self.bodies[0]:
            return self.bodies[1]
        if body == self.bodies[1]:
            return self.bodies[0]
        raise KeyError(f"Joint '{self.name}' does not touch part '{body}'")

    def sign_for(self, body: str) -> float:
        """
        Return the sense in which the unknown force acts on one part.

        The unknown is the force applied to ``bodies[0]``; Newton's third law
        gives ``bodies[1]`` the negative of it.
        """
        return 1.0 if body == self.bodies[0] else -1.0


@dataclass(frozen=True)
class Subsystem:
    """
    One set of parts that only reach each other, and the ground.

    Corners are found rather than declared: delete the ground bodies and the
    connected components of what is left are the independently solvable
    systems. A model that couples its corners -- an anti-roll bar, or a rack
    left free to translate -- produces one larger component instead, with no
    special handling anywhere.
    """

    name: str
    bodies: tuple[ForceBody, ...]
    joints: tuple[ForceJoint, ...]

    def joints_on(self, body: str) -> tuple[ForceJoint, ...]:
        """Return every joint touching one part."""
        return tuple(joint for joint in self.joints if body in joint.bodies)


@dataclass(frozen=True)
class ForceGraph:
    """The structural parts, joints, and subsystems of one suspension model."""

    bodies: tuple[ForceBody, ...]
    joints: tuple[ForceJoint, ...]
    subsystems: tuple[Subsystem, ...]
    positions: Mapping[PointKey, object] = field(repr=False)

    @property
    def ground(self) -> ForceBody:
        """Return the grounded chassis part."""
        return next(body for body in self.bodies if body.is_ground)


def split_side(name: str) -> tuple[Side, str]:
    """Split an axle-qualified body name into its side and its base name."""
    head, _, rest = name.partition(" ")
    side = _SIDE_WORDS.get(head.lower())
    if side is not None and rest:
        return side, rest
    return Side.CENTER, name


def point_side(key: PointKey) -> Side:
    """Return the side a point key belongs to."""
    return key.side if isinstance(key, PointRef) else Side.CENTER


def build_force_graph(
    suspension: Suspension,
    policy: StructurePolicy = DEFAULT_STRUCTURE,
) -> ForceGraph:
    """
    Build the structural graph for one loaded suspension.

    Args:
        suspension: A loaded axle or corner model.
        policy: How to turn its kinematic bodies into structural parts.

    Returns:
        The parts, their joints, and the independent subsystems they form.

    Raises:
        ValueError: If a point is shared by more than two parts, or a part
            cannot transmit load because it has fewer than two joints.
    """
    positions = suspension.initial_state().positions
    assembly = suspension.assembly()
    kinematic = build_bodies(
        assembly.elements,
        assembly.points.fixed,
        suspension.rigid_attachments(),
    )
    bodies = _apply_policy(kinematic, policy, positions)
    joints = _find_joints(bodies, positions)
    _check_load_paths(bodies, joints)
    return ForceGraph(
        bodies=bodies,
        joints=joints,
        subsystems=_partition(bodies, joints),
        positions=positions,
    )


def _apply_policy(
    kinematic: Sequence[RigidBody],
    policy: StructurePolicy,
    positions: Mapping[PointKey, object],
) -> tuple[ForceBody, ...]:
    """Weld, attach, ground, and drop bodies to give the structural parts."""
    ground_name = next(
        (body.name for body in kinematic if body.mode is RotationMode.GROUND),
        None,
    )
    if ground_name is None:
        raise ValueError(
            "The suspension has no fixed points, so it has no chassis to react "
            "against and no static solution."
        )

    ignored = {slug(name) for name in policy.ignore}
    live = [body for body in kinematic if slug(split_side(body.name)[1]) not in ignored]

    # Merge with union-find, keyed on the full (side-qualified) body name so
    # that a side-agnostic rule never welds the two corners together.
    parent = {body.name: body.name for body in live}

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    def union(into: str, other: str) -> None:
        parent[find(other)] = find(into)

    by_side: dict[Side, dict[str, str]] = {}
    for body in live:
        side, base = split_side(body.name)
        by_side.setdefault(side, {})[slug(base)] = body.name

    for group in policy.weld:
        if not group:
            continue
        head = slug(group[0])
        for members in by_side.values():
            if head not in members:
                continue
            target = members[head]
            for member in group[1:]:
                name = members.get(slug(member))
                if name is not None:
                    union(target, name)
            # Re-root onto this group's named part so a later rule that also
            # touches these bodies does not rename the merged part.
            parent[find(target)] = target
            parent[target] = target

    grounded = {slug(name) for name in policy.ground}
    for body in live:
        if slug(split_side(body.name)[1]) in grounded:
            union(ground_name, body.name)

    merged: dict[str, list[PointKey]] = {}
    for body in live:
        bucket = merged.setdefault(find(body.name), [])
        for point in body.points:
            if point not in bucket:
                bucket.append(point)

    for rule in policy.attach:
        _apply_attachment(rule, merged, positions)

    return tuple(
        ForceBody(
            name=name,
            side=split_side(name)[0],
            points=tuple(points),
            is_ground=name == ground_name,
        )
        for name, points in merged.items()
    )


def _apply_attachment(
    rule: AttachRule,
    merged: dict[str, list[PointKey]],
    positions: Mapping[PointKey, object],
) -> None:
    """Fold one declared point into whichever part carries all of its anchors."""
    for side in (Side.LEFT, Side.RIGHT, Side.CENTER):
        point = _resolve_point(rule.point, side, positions)
        anchors = [_resolve_point(name, side, positions) for name in rule.anchors]
        if point is None or any(anchor is None for anchor in anchors):
            continue
        wanted = set(anchors)
        for points in merged.values():
            if wanted <= set(points) and point not in points:
                points.append(point)
                break
        else:
            raise ValueError(
                f"Attachment of '{rule.point}' names anchors "
                f"{list(rule.anchors)}, which no single part carries."
            )


def _resolve_point(
    name: str,
    side: Side,
    positions: Mapping[PointKey, object],
) -> PointKey | None:
    """Resolve a bare point name against one side of a suspension."""
    wanted = slug(name)
    for key in positions:
        if point_side(key) is not side:
            continue
        base = key.point if isinstance(key, PointRef) else key
        if isinstance(base, PointID) and slug(base.name) == wanted:
            return key
    return None


def _find_joints(
    bodies: Sequence[ForceBody],
    positions: Mapping[PointKey, object],
) -> tuple[ForceJoint, ...]:
    """Pair up the parts meeting at each point."""
    carriers: dict[PointKey, list[str]] = {}
    for body in bodies:
        for point in body.points:
            carriers.setdefault(point, []).append(body.name)

    joints: list[ForceJoint] = []
    for point, names in carriers.items():
        if len(names) < 2:
            # Interior to one part, or a fixed point nothing attaches to.
            continue
        if len(names) > 2:
            found = ", ".join(f"'{name}'" for name in sorted(names))
            raise ValueError(
                f"Point '{point_key_name(point)}' is carried by {len(names)} parts "
                f"({found}). A joint is where exactly two parts meet; weld the "
                "ones that are a single part in 'structure.weld'."
            )
        joints.append(
            ForceJoint(
                name=point_key_name(point),
                point=point,
                position=extract_array(positions[point]),
                bodies=(names[0], names[1]),
            )
        )
    return tuple(sorted(joints, key=lambda joint: joint.name))


def _check_load_paths(
    bodies: Sequence[ForceBody],
    joints: Sequence[ForceJoint],
) -> None:
    """Reject a part that cannot transmit load because it is barely attached."""
    counts = {body.name: 0 for body in bodies}
    for joint in joints:
        for name in joint.bodies:
            counts[name] += 1
    for body in bodies:
        if body.is_ground:
            continue
        if counts[body.name] < 2:
            raise ValueError(
                f"Part '{body.name}' has {counts[body.name]} joint(s), so it cannot "
                "transmit load. Its pickup is probably carried by another part "
                "without being declared: add it under 'structure.attach', or fix "
                "the topology's rigid_attachments()."
            )


def _partition(
    bodies: Sequence[ForceBody],
    joints: Sequence[ForceJoint],
) -> tuple[Subsystem, ...]:
    """Split the graph into the components left once ground is removed."""
    moving = {body.name: body for body in bodies if not body.is_ground}
    parent = {name: name for name in moving}

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    for joint in joints:
        first, second = joint.bodies
        if first in moving and second in moving:
            parent[find(second)] = find(first)

    grouped: dict[str, list[ForceBody]] = {}
    for name, body in moving.items():
        grouped.setdefault(find(name), []).append(body)

    subsystems: list[Subsystem] = []
    for members in grouped.values():
        names = {body.name for body in members}
        member_joints = tuple(joint for joint in joints if names & set(joint.bodies))
        subsystems.append(
            Subsystem(
                name=_subsystem_name(members),
                bodies=tuple(sorted(members, key=lambda body: body.name)),
                joints=member_joints,
            )
        )
    return tuple(sorted(subsystems, key=lambda subsystem: subsystem.name))


def _subsystem_name(bodies: Sequence[ForceBody]) -> str:
    """Name a subsystem by the side it belongs to, or by its parts."""
    sides = {body.side for body in bodies}
    if len(sides) == 1:
        side = next(iter(sides))
        if side is not Side.CENTER:
            return side.name.lower()
        return "centre"
    return "coupled"
