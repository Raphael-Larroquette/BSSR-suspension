r"""Rigid bodies derived from a suspension's declared elements.

A suspension model declares physical elements; this module turns them into the
rigid bodies those elements make up, and recovers each body's rotation from a
solved state. Elements are grouped by the ``body_group`` each topology
declares, so a weldment modelled as several two-point links -- an A-arm as a
front and a rear leg -- resolves to one body. An implicit ground body collects
every fixed point, so a link's chassis pickup resolves to a joint between that
link and ground rather than dangling.

Both the bearing-misalignment report and the static force solve build on this
grouping. Nothing here knows about either: a body is a named set of points
plus a statement of how much of its orientation the geometry determines.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from kinematics.core.elements import SuspensionElement
from kinematics.core.primitives.constants import EPS_GEOMETRIC
from kinematics.core.primitives.geometry import extract_array
from kinematics.core.primitives.point_ref import PointKey, point_key_name

# A body's orientation is only determined when its points span a plane. Below
# this singular-value ratio the point cloud is treated as a line, and the
# two-point transport convention is used instead of a full fit.
PLANARITY_RATIO = 1e-6


# ==========================================================================
# 1. Rotation primitives
# ==========================================================================
def unit(vector: NDArray[np.float64]) -> NDArray[np.float64]:
    """Normalize a vector, rejecting one with no direction."""
    norm = float(np.linalg.norm(vector))
    if norm < EPS_GEOMETRIC:
        raise ValueError("Cannot normalize a zero-length direction")
    return np.asarray(vector, dtype=np.float64) / norm


def kabsch_rotation(
    neutral: NDArray[np.float64],
    current: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Return the rotation carrying a neutral point cloud onto its current pose.

    Both arrays are ``(N, 3)`` in matching point order. The fit is the
    orthogonal Procrustes / Kabsch solution about each cloud's centroid, with
    the reflection case corrected so the result is always a proper rotation.
    A rigid body's points move rigidly, so for exact input this recovers the
    rotation exactly rather than approximating it.
    """
    if neutral.shape != current.shape or neutral.ndim != 2 or neutral.shape[1] != 3:
        raise ValueError("Kabsch input must be two matching (N, 3) point arrays")
    if neutral.shape[0] < 3:
        raise ValueError("A determined rotation fit needs at least three points")

    neutral_centred = neutral - neutral.mean(axis=0)
    current_centred = current - current.mean(axis=0)
    covariance = neutral_centred.T @ current_centred
    left, _, right_t = np.linalg.svd(covariance)
    correction = np.eye(3)
    correction[2, 2] = float(np.sign(np.linalg.det(right_t.T @ left.T)))
    return right_t.T @ correction @ left.T


def transport_rotation(
    neutral_axis: NDArray[np.float64],
    current_axis: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Return the minimal rotation carrying one direction onto another.

    This is the parallel-transport (zero intrinsic spin) convention used for a
    body whose points define only an axis. It rotates about the common
    perpendicular by exactly the angle between the two directions, adding no
    roll about the axis itself.
    """
    start = unit(neutral_axis)
    end = unit(current_axis)
    axis = np.cross(start, end)
    sin_angle = float(np.linalg.norm(axis))
    cos_angle = float(np.dot(start, end))
    if sin_angle < EPS_GEOMETRIC:
        if cos_angle > 0.0:
            return np.eye(3)
        # Antiparallel: a half turn about any perpendicular. Suspension travel
        # never reverses a link, so this only guards degenerate input.
        seed = np.array([1.0, 0.0, 0.0])
        if abs(float(np.dot(seed, start))) > 0.9:
            seed = np.array([0.0, 1.0, 0.0])
        perpendicular = unit(np.cross(start, seed))
        return rotation_from_rotvec(perpendicular * np.pi)
    angle = float(np.arctan2(sin_angle, cos_angle))
    return rotation_from_rotvec(axis / sin_angle * angle)


def rotation_from_rotvec(rotvec: NDArray[np.float64]) -> NDArray[np.float64]:
    """Build a rotation matrix from a rotation vector, in radians."""
    angle = float(np.linalg.norm(rotvec))
    if angle < EPS_GEOMETRIC:
        return np.eye(3)
    axis = rotvec / angle
    cross = np.array(
        [
            [0.0, -axis[2], axis[1]],
            [axis[2], 0.0, -axis[0]],
            [-axis[1], axis[0], 0.0],
        ]
    )
    return np.eye(3) + np.sin(angle) * cross + (1.0 - np.cos(angle)) * (cross @ cross)


def rotvec_from_rotation(rotation: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return the rotation vector of a rotation matrix, in radians.

    The magnitude is the rotation angle and the direction is its axis. This is
    the lossless three-number encoding exported per joint: suspension travel
    never reaches a half turn, so the representation is unambiguous.
    """
    trace = float(np.trace(rotation))
    cos_angle = float(np.clip((trace - 1.0) / 2.0, -1.0, 1.0))
    angle = float(np.arccos(cos_angle))
    if angle < EPS_GEOMETRIC:
        return np.zeros(3)
    if np.pi - angle < 1e-7:
        # Near a half turn the skew part vanishes; recover the axis from the
        # symmetric part instead.
        symmetric = (rotation + np.eye(3)) / 2.0
        axis = np.sqrt(np.clip(np.diag(symmetric), 0.0, None))
        largest = int(np.argmax(axis))
        axis = symmetric[:, largest] / axis[largest]
        return unit(axis) * angle
    skew = np.array(
        [
            rotation[2, 1] - rotation[1, 2],
            rotation[0, 2] - rotation[2, 0],
            rotation[1, 0] - rotation[0, 1],
        ]
    )
    return skew / (2.0 * np.sin(angle)) * angle


def angle_between_deg(first: NDArray[np.float64], second: NDArray[np.float64]) -> float:
    """Return the unsigned angle between two directions, in degrees."""
    cosine = float(np.clip(np.dot(unit(first), unit(second)), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


# ==========================================================================
# 2. Rigid bodies
# ==========================================================================
class RotationMode(StrEnum):
    """How a body's rotation is recovered from a solved state."""

    GROUND = "ground"
    FITTED = "fitted"
    TRANSPORT = "transport"

    @property
    def description(self) -> str:
        """Return a report-friendly account of the rotation source."""
        if self is RotationMode.GROUND:
            return "fixed to chassis"
        if self is RotationMode.FITTED:
            return "fitted from >=3 points"
        return "2-point link, transport (spin undetermined)"


@dataclass(frozen=True)
class RigidBody:
    """One rigid body in the assembly, and how to recover its rotation.

    ``GROUND`` bodies never rotate. ``FITTED`` bodies span a plane, so their
    orientation is fully determined by their points. ``TRANSPORT`` bodies are
    two-point links whose roll about their own axis no kinematic model can
    determine; their rotation follows the parallel-transport convention and
    their joints may be declared ``indeterminate``.
    """

    name: str
    points: tuple[PointKey, ...]
    mode: RotationMode

    def rotation(
        self,
        neutral: Mapping[PointKey, object],
        current: Mapping[PointKey, object],
    ) -> NDArray[np.float64]:
        """Return this body's rotation from the neutral pose to a solved one."""
        if self.mode is RotationMode.GROUND:
            return np.eye(3)
        if self.mode is RotationMode.TRANSPORT:
            start, end = self.points[0], self.points[1]
            return transport_rotation(
                extract_array(neutral[end]) - extract_array(neutral[start]),
                extract_array(current[end]) - extract_array(current[start]),
            )
        return kabsch_rotation(
            self._stack(neutral),
            self._stack(current),
        )

    def axis(self, neutral: Mapping[PointKey, object]) -> NDArray[np.float64] | None:
        """Return the neutral axis of a two-point link, if this is one."""
        if self.mode is not RotationMode.TRANSPORT:
            return None
        start, end = self.points[0], self.points[1]
        return unit(extract_array(neutral[end]) - extract_array(neutral[start]))

    def _stack(self, positions: Mapping[PointKey, object]) -> NDArray[np.float64]:
        """Stack this body's points into an ``(N, 3)`` array."""
        return np.asarray(
            [extract_array(positions[point]) for point in self.points],
            dtype=np.float64,
        )


@dataclass(frozen=True)
class RigidAttachment:
    """A point carried rigidly by the body that owns ``anchors``.

    Declared by a topology for a pickup that no element groups with its
    carrier -- an inboard spring pickup riding a wishbone, for example. The
    anchors identify the body; naming it directly would couple mechanism code
    to element labels.
    """

    point: PointKey
    anchors: tuple[PointKey, ...]


def build_bodies(
    elements: Sequence[SuspensionElement],
    fixed_points: frozenset[PointKey],
    attachments: Sequence[RigidAttachment] = (),
) -> tuple[RigidBody, ...]:
    """Derive the assembly's rigid bodies from declared element groups.

    Elements are grouped by ``body_key``, which each topology declares. An
    implicit ground body collects every fixed point, so a link's chassis
    pickup resolves to a joint between that link and ground. Rigid
    attachments then fold extra pickups into whichever body owns their
    anchors.

    A body's rotation mode is chosen from its neutral point count alone, not
    from what kind of element it came from.
    """
    grouped: dict[str, list[PointKey]] = {}
    for element in elements:
        bucket = grouped.setdefault(element.body_key, [])
        for point in element.point_keys:
            if point not in bucket:
                bucket.append(point)

    for attachment in attachments:
        anchors = set(attachment.anchors)
        for name, points in grouped.items():
            if anchors <= set(points) and attachment.point not in points:
                points.append(attachment.point)
                break

    bodies = [
        RigidBody(
            name=name,
            points=tuple(points),
            mode=(RotationMode.FITTED if len(points) >= 3 else RotationMode.TRANSPORT),
        )
        for name, points in grouped.items()
    ]
    if fixed_points:
        bodies.append(
            RigidBody(
                name="Chassis",
                points=tuple(sorted(fixed_points, key=point_key_name)),
                mode=RotationMode.GROUND,
            )
        )
    return tuple(bodies)


def resolve_body_modes(
    bodies: Sequence[RigidBody],
    neutral: Mapping[PointKey, object],
) -> tuple[RigidBody, ...]:
    """Demote bodies whose points turn out to be collinear.

    Point count alone can overstate a body's determinacy: three points strung
    along one line fix an axis, not an orientation. Fitting a rotation to them
    would return an arbitrary roll, so they fall back to transport.
    """
    resolved: list[RigidBody] = []
    for body in bodies:
        if body.mode is not RotationMode.FITTED:
            resolved.append(body)
            continue
        cloud = np.asarray(
            [extract_array(neutral[point]) for point in body.points],
            dtype=np.float64,
        )
        centred = cloud - cloud.mean(axis=0)
        singular = np.linalg.svd(centred, compute_uv=False)
        if singular[0] <= EPS_GEOMETRIC or singular[1] / singular[0] < PLANARITY_RATIO:
            extreme = _extreme_pair(cloud)
            resolved.append(
                RigidBody(
                    name=body.name,
                    points=(body.points[extreme[0]], body.points[extreme[1]]),
                    mode=RotationMode.TRANSPORT,
                )
            )
            continue
        resolved.append(body)
    return tuple(resolved)


def _extreme_pair(cloud: NDArray[np.float64]) -> tuple[int, int]:
    """Return the indices of the two most separated points in a cloud."""
    separations = np.linalg.norm(cloud[:, None, :] - cloud[None, :, :], axis=-1)
    flat = int(np.argmax(separations))
    return divmod(flat, separations.shape[0])
