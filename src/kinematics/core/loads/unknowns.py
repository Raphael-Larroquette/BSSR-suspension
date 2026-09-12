r"""
The unknown scalar forces a subsystem is solved for.

Most joints contribute three unknown force components. Two cases do not, and
both are found from the geometry rather than declared:

*Two-force members.* A part with exactly two joints and no external load can
only carry load along the line joining them, so its two joints share one
unknown axial magnitude and the part itself contributes no equations.

*Coaxial joint pairs.* Two joints connecting the same pair of parts are a
redundancy statics cannot resolve. Writing :math:`\hat u` for the direction
between them, their separation is parallel to it, so

.. math::

    \mathbf r_F \times \hat u = \mathbf r_R \times \hat u

and the two axial components enter every force and moment row only as their
sum. This is the locating-bearing / floating-bearing problem, and it is closed
either by sharing the axial load equally -- one extra constraint row -- or by
naming the joint that carries all of it, which drops the other joint's axial
column.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from kinematics.core.loads.structure import (
    ForceBody,
    ForceJoint,
    Subsystem,
    slug,
    split_side,
)
from kinematics.core.primitives.constants import EPS_GEOMETRIC

# Policy value selecting an equal axial share across a coaxial joint pair.
EVEN = "even"


class UnknownKind(StrEnum):
    """What one block of unknown columns represents."""

    JOINT = "joint"
    LINK = "link"


@dataclass(frozen=True)
class Unknown:
    """One block of columns in the assembled system."""

    name: str
    kind: UnknownKind
    start: int
    basis: NDArray[np.float64]

    @property
    def width(self) -> int:
        """Return how many columns this unknown occupies."""
        return int(self.basis.shape[1])


@dataclass(frozen=True)
class JointBinding:
    """
    How one joint's force is read out of the unknown columns.

    ``orientation`` is +1 for an ordinary joint and carries the axial sense for
    a joint on a two-force member, so every caller can write the force on
    ``joint.bodies[0]`` as ``orientation * basis @ x`` without knowing which
    kind it is holding.
    """

    joint: ForceJoint
    unknown: Unknown
    orientation: float

    def force(self, solution: NDArray[np.float64]) -> NDArray[np.float64]:
        """Return the solved force acting on this joint's first part."""
        block = solution[self.unknown.start : self.unknown.start + self.unknown.width]
        return self.orientation * (self.unknown.basis @ block)


@dataclass(frozen=True)
class CoaxialPair:
    """Two joints between one pair of parts, and how their axial load is split."""

    bodies: tuple[str, str]
    joints: tuple[ForceJoint, ForceJoint]
    axis: NDArray[np.float64]
    carrier: str | None

    def describe(self) -> str:
        """Return a one-line account of the pair and the policy applied to it."""
        policy = EVEN if self.carrier is None else f"carrier '{self.carrier}'"
        return (
            f"{self.joints[0].name} / {self.joints[1].name} between "
            f"'{self.bodies[0]}' and '{self.bodies[1]}': {policy}"
        )


@dataclass(frozen=True)
class Constraint:
    """One extra row closing a redundancy the equilibrium equations leave open."""

    name: str
    row: NDArray[np.float64]


@dataclass(frozen=True)
class UnknownCatalog:
    """The complete unknown list and equation set for one subsystem."""

    subsystem: Subsystem
    unknowns: tuple[Unknown, ...]
    bindings: Mapping[str, JointBinding]
    equation_bodies: tuple[ForceBody, ...]
    two_force_bodies: tuple[ForceBody, ...]
    coaxial: tuple[CoaxialPair, ...]
    constraints: tuple[Constraint, ...]

    @property
    def width(self) -> int:
        """Return the total number of unknown columns."""
        return sum(unknown.width for unknown in self.unknowns)

    @property
    def rows(self) -> int:
        """Return the total number of equations."""
        return 6 * len(self.equation_bodies) + len(self.constraints)


def build_unknowns(
    subsystem: Subsystem,
    loaded_bodies: Sequence[str] = (),
    axial_default: str = EVEN,
    axial_overrides: Mapping[str, str] | None = None,
) -> UnknownCatalog:
    """
    Catalogue the unknowns and extra constraints for one subsystem.

    Args:
        subsystem: The parts and joints to solve.
        loaded_bodies: Parts carrying an external load, which are therefore
            never reduced to two-force members.
        axial_default: ``"even"``, or a point name carrying the axial load at
            every coaxial pair.
        axial_overrides: Per-part policy, keyed by part name.

    Returns:
        The catalogue, ready to assemble.

    Raises:
        ValueError: If more than two joints connect one pair of parts, if a
            named axial carrier is not one of the pair, or if a two-force
            member has no length.
    """
    overrides = {slug(key): value for key, value in (axial_overrides or {}).items()}
    loaded = set(loaded_bodies)

    members = tuple(
        body
        for body in subsystem.bodies
        if not body.is_ground
        and body.name not in loaded
        and len(subsystem.joints_on(body.name)) == 2
    )
    member_names = {body.name for body in members}
    chained = [
        joint
        for joint in subsystem.joints
        if joint.bodies[0] in member_names and joint.bodies[1] in member_names
    ]
    if chained:
        names = ", ".join(sorted(joint.name for joint in chained))
        raise ValueError(
            f"Joint(s) {names} connect two two-force members directly. Their axial "
            "unknowns would share one joint and the system cannot be assembled. "
            "Give one of the parts a third attachment, or ground it."
        )
    equation_bodies = tuple(
        body
        for body in subsystem.bodies
        if not body.is_ground and body.name not in member_names
    )

    pairs = _coaxial_pairs(subsystem, member_names, overrides, axial_default)
    restricted = {
        pair.joints[1 if pair.carrier == pair.joints[0].name else 0].name: pair.axis
        for pair in pairs
        if pair.carrier is not None
    }

    unknowns: list[Unknown] = []
    bindings: dict[str, JointBinding] = {}
    cursor = 0

    for body in members:
        first, second = sorted(
            subsystem.joints_on(body.name), key=lambda joint: joint.name
        )
        span = second.position - first.position
        length = float(np.linalg.norm(span))
        if length < EPS_GEOMETRIC:
            raise ValueError(
                f"Two-force member '{body.name}' has coincident joints "
                f"'{first.name}' and '{second.name}', so it has no line of action."
            )
        axis = span / length
        unknown = Unknown(
            name=body.name,
            kind=UnknownKind.LINK,
            start=cursor,
            basis=axis.reshape(3, 1),
        )
        unknowns.append(unknown)
        cursor += unknown.width
        # Positive is tension: the member pulls the parts it joins toward each
        # other, so the neighbour at the tail of the axis is pulled along it and
        # the neighbour at the head is pulled back against it.
        for joint, sense in ((first, 1.0), (second, -1.0)):
            neighbour = joint.other(body.name)
            bindings[joint.name] = JointBinding(
                joint=joint,
                unknown=unknown,
                orientation=sense * joint.sign_for(neighbour),
            )

    for joint in sorted(subsystem.joints, key=lambda item: item.name):
        if joint.name in bindings:
            continue
        axis = restricted.get(joint.name)
        basis = np.eye(3) if axis is None else _plane_basis(axis)
        unknown = Unknown(
            name=joint.name,
            kind=UnknownKind.JOINT,
            start=cursor,
            basis=basis,
        )
        unknowns.append(unknown)
        cursor += unknown.width
        bindings[joint.name] = JointBinding(
            joint=joint, unknown=unknown, orientation=1.0
        )

    constraints = tuple(
        _even_split_constraint(pair, bindings, cursor)
        for pair in pairs
        if pair.carrier is None
    )

    return UnknownCatalog(
        subsystem=subsystem,
        unknowns=tuple(unknowns),
        bindings=bindings,
        equation_bodies=equation_bodies,
        two_force_bodies=members,
        coaxial=pairs,
        constraints=constraints,
    )


def _coaxial_pairs(
    subsystem: Subsystem,
    member_names: set[str],
    overrides: Mapping[str, str],
    axial_default: str,
) -> tuple[CoaxialPair, ...]:
    """Find joint pairs sharing a part pair, and resolve their axial policy."""
    grouped: dict[tuple[str, str], list[ForceJoint]] = {}
    for joint in subsystem.joints:
        if set(joint.bodies) & member_names:
            continue
        grouped.setdefault(tuple(sorted(joint.bodies)), []).append(joint)

    pairs: list[CoaxialPair] = []
    for bodies, joints in sorted(grouped.items()):
        if len(joints) < 2:
            continue
        if len(joints) > 2:
            names = ", ".join(sorted(joint.name for joint in joints))
            raise ValueError(
                f"Parts '{bodies[0]}' and '{bodies[1]}' meet at {len(joints)} joints "
                f"({names}). Only a pair is supported; three or more leave a "
                "redundancy this solver cannot close."
            )
        first, second = sorted(joints, key=lambda joint: joint.name)
        span = second.position - first.position
        length = float(np.linalg.norm(span))
        if length < EPS_GEOMETRIC:
            raise ValueError(
                f"Joints '{first.name}' and '{second.name}' are coincident, so the "
                f"redundancy between '{bodies[0]}' and '{bodies[1]}' has no axis."
            )
        pairs.append(
            CoaxialPair(
                bodies=bodies,
                joints=(first, second),
                axis=span / length,
                carrier=_carrier_for(bodies, (first, second), overrides, axial_default),
            )
        )
    return tuple(pairs)


def _carrier_for(
    bodies: tuple[str, str],
    joints: tuple[ForceJoint, ForceJoint],
    overrides: Mapping[str, str],
    axial_default: str,
) -> str | None:
    """Resolve which joint of a pair carries the axial load, if either does."""
    policy = axial_default
    for body in bodies:
        for key in (slug(body), slug(split_side(body)[1])):
            if key in overrides:
                policy = overrides[key]
    if policy == EVEN:
        return None

    wanted = slug(policy)
    for joint in joints:
        if slug(joint.name) == wanted or slug(joint.name).endswith(f"_{wanted}"):
            return joint.name
    raise ValueError(
        f"Axial carrier '{policy}' is not one of the joints between "
        f"'{bodies[0]}' and '{bodies[1]}' ('{joints[0].name}', '{joints[1].name}'). "
        f"Use one of those names, or '{EVEN}'."
    )


def _even_split_constraint(
    pair: CoaxialPair,
    bindings: Mapping[str, JointBinding],
    width: int,
) -> Constraint:
    """Build the row making both joints of a pair carry the same axial load."""
    reference = pair.bodies[0]
    row = np.zeros(width)
    for joint, sense in zip(pair.joints, (1.0, -1.0)):
        binding = bindings[joint.name]
        scale = sense * binding.orientation * joint.sign_for(reference)
        block = scale * (pair.axis @ binding.unknown.basis)
        row[binding.unknown.start : binding.unknown.start + binding.unknown.width] += (
            block
        )
    return Constraint(
        name=f"even_axial:{pair.joints[0].name}|{pair.joints[1].name}",
        row=row,
    )


def _plane_basis(axis: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return two unit columns spanning the plane perpendicular to an axis."""
    seed = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(seed, axis))) > 0.9:
        seed = np.array([0.0, 1.0, 0.0])
    first = np.cross(axis, seed)
    first /= float(np.linalg.norm(first))
    second = np.cross(axis, first)
    return np.stack([first, second], axis=1)
