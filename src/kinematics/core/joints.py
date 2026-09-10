r"""Bearing misalignment geometry: rigid bodies, joints, and required angles.

Theory
------
A joint is where two rigid bodies meet at a shared point. Body ``A`` carries
the bearing housing; body ``B`` carries the bolt or ball. Two unit directions
matter, each fixed to its own body: the housing's centred direction
:math:`\hat n_A` and the bore axis :math:`\hat n_B`. At sweep step ``t`` the
bodies have rotated from their neutral pose by :math:`R_A(t)` and
:math:`R_B(t)`, so the angle the bearing must absorb is

.. math::

    \theta(t) = \angle\big(R_A(t)\hat n_A,\; R_B(t)\hat n_B\big)
               = \angle\big(\hat n_A,\; Q(t)\,\hat n_B\big),
    \qquad Q(t) = R_A(t)^{\top} R_B(t)

:math:`Q(t)` is the relative rotation of the two bodies expressed in the
housing's neutral frame, and it depends on **neither** direction. That is the
whole reason this module exports ``Q`` per step rather than an angle: any
candidate axis, on either side, is a closed-form evaluation against the
exported ``Q``. Choosing or optimising bearing axes therefore never requires
re-solving a sweep, and sweeps written by an older version of this code remain
valid input for axis models added later.

Writing :math:`Q(t)` as a rotation of angle :math:`\alpha_t` about unit axis
:math:`\hat q_t`, and :math:`\beta_t = \angle(\hat n, \hat q_t)` for a
housing installed centred (:math:`\hat n_A = \hat n_B = \hat n`):

.. math::

    \cos\theta_t = 1 - \sin^2\!\beta_t\,(1 - \cos\alpha_t)

Two limits explain the whole taxonomy. A bore lying **on** the relative
rotation axis sees :math:`\theta = 0`: the joint is a pure revolute about its
own bore, which is why a wishbone's inboard pivots can be plain bushings. A
bore **perpendicular** to it sees :math:`\theta = \alpha_t`, the full
relative rotation.

Indeterminate housings
----------------------
A member with spherical joints at both ends carries no axial torque, so its
roll about its own axis is undetermined -- the solver neither knows nor can
know it. :math:`R_A` for such a body is fixed here by parallel transport (zero
intrinsic spin), and a joint may declare its housing ``indeterminate`` to say
that the true orientation is that transport times an unknown spin
:math:`\psi_t`.

Because the assembly clocking :math:`\phi` and the spin :math:`\psi_t` enter
only as a sum, and :math:`\psi_t` is free at every step, the housing
direction is free on its cone at every step and the minimisation collapses to
a point-to-cone distance with no optimiser at all:

.. math::

    \theta_t^{\text{indet}}
        = \big|\,\gamma - \angle(\hat\ell_0,\; Q^0_t \hat n_B)\,\big|

with :math:`\hat\ell_0` the neutral link axis and :math:`\gamma` the cone
half-angle from it (90 degrees for a rod end, whose bore is perpendicular to
its shank). Physically this is the part of the bore's tilt that has gone
*along* the link: no amount of spinning relieves it. It is a lower bound, so
the report pairs it with the locked-spin value, which is a genuine
1-D optimisation over the clocking and is computed post hoc from ``Q``.

The transport convention is lossless for later work: any other spin model is
:math:`Q' = S(-\psi)\,Q` about the neutral link axis, recoverable from the
exported ``Q`` alone. The coupled case, where both ends of one link are
indeterminate at once and share a single :math:`\psi_t`, is therefore
reachable from existing sweep output without re-solving anything.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from kinematics.core.bodies import (
    RigidBody,
    RotationMode,
    angle_between_deg,
    build_bodies,
    resolve_body_modes,
    rotvec_from_rotation,
    unit,
)
from kinematics.core.enums import JointType
from kinematics.core.primitives.constants import EPS_GEOMETRIC
from kinematics.core.primitives.geometry import extract_array
from kinematics.core.primitives.point_ref import PointKey, point_key_name
from kinematics.core.schema.joints import (
    AxisSpec,
    JointSideSpec,
    JointSpec,
    PartSpec,
    PlaneSpec,
)

if TYPE_CHECKING:
    from kinematics.core.metrics.main import MetricRow
    from kinematics.core.metrics.registry import MetricSpec
    from kinematics.core.suspensions.base import Suspension

# Default cone half-angle between a housing's centred direction and the axis
# of the body carrying it. 90 degrees is a rod end, whose bore is
# perpendicular to its shank.
DEFAULT_CONE_DEG = 90.0

# Local-refinement simplex size, in radians, comparable to the spacing of the
# candidate lattice the refinement starts from.
REFINE_STEP = 0.02


# ==========================================================================
# 1. Resolving declared joints against an assembly
# ==========================================================================
class HousingMode(StrEnum):
    """How a joint's housing direction is determined."""

    AUTHORED = "authored"
    CENTRED = "centred"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class AxisConstraint:
    """The set a free direction is drawn from, as perpendicularity facts.

    Each entry is a neutral-frame axis the direction must be perpendicular to.
    No entries leaves two free degrees of freedom, one leaves a single
    clocking angle, and two pin the direction up to sign.
    """

    perpendiculars: tuple[tuple[float, float, float], ...] = ()

    @property
    def degrees_of_freedom(self) -> int:
        """Return how many degrees of freedom the constraint leaves."""
        return max(0, 2 - len(self.perpendiculars))


@dataclass(frozen=True)
class ResolvedJoint:
    """One declared joint, resolved against neutral geometry.

    ``bore_axis`` is ``None`` when the bore direction is left for the report
    to optimise. Everything here is neutral-pose data; per-step behaviour
    comes from the exported relative rotation.
    """

    name: str
    label: str
    joint_type: JointType
    point: PointKey
    housing_body: RigidBody
    bore_body: RigidBody
    housing_mode: HousingMode
    housing_axis: tuple[float, float, float] | None
    bore_axis: tuple[float, float, float] | None
    bore_constraint: AxisConstraint
    spin_axis: tuple[float, float, float] | None
    cone_deg: float

    @property
    def is_optimised(self) -> bool:
        """Whether the bore direction is solved for after the sweep."""
        return self.bore_axis is None

    @property
    def install_offset_deg(self) -> float | None:
        """Return the neutral-pose angle between housing and bore directions.

        Non-zero means the bearing is installed deliberately off centre and
        starts life already eating part of its cone. It is reported on its own
        so that an accidental offset cannot hide inside the travel demand.
        """
        if self.bore_axis is None:
            return None
        bore = np.asarray(self.bore_axis, dtype=np.float64)
        if self.housing_mode is HousingMode.CENTRED:
            return 0.0
        if self.housing_mode is HousingMode.INDETERMINATE:
            spin = np.asarray(self.spin_axis, dtype=np.float64)
            return abs(self.cone_deg - angle_between_deg(spin, bore))
        return angle_between_deg(np.asarray(self.housing_axis), bore)

    def describe(self) -> str:
        """Return a one-line account of how this joint was resolved."""
        return (
            f"{self.label}: housing on '{self.housing_body.name}' "
            f"({self.housing_body.mode.description}), bore on "
            f"'{self.bore_body.name}' ({self.bore_body.mode.description}), "
            f"housing {self.housing_mode.value}"
        )


def _slug(name: str) -> str:
    """Normalize an authored joint key into a stable column identity."""
    return "".join(
        character if character.isalnum() else "_" for character in name.strip().lower()
    ).strip("_")


def _resolve_axis_spec(
    spec: AxisSpec,
    neutral: Mapping[PointKey, object],
) -> NDArray[np.float64]:
    """Resolve one authored direction against the neutral pose.

    Joints are always evaluated at corner scope, where positions are keyed on
    bare ``PointID`` values, so an authored point name needs no side
    qualification here.
    """
    from kinematics.core.schema.sweep import AXIS_VECTORS

    if spec.chassis_axis is not None:
        return unit(np.asarray(AXIS_VECTORS[spec.chassis_axis], dtype=np.float64))
    if spec.vector is not None:
        return unit(np.asarray(tuple(spec.vector), dtype=np.float64))
    if spec.x is not None:
        return unit(np.asarray([spec.x, spec.y, spec.z], dtype=np.float64))
    start = _require_point(spec.from_point, neutral)
    end = _require_point(spec.to_point, neutral)
    return unit(extract_array(end) - extract_array(start))


def _require_point(
    point: PointKey | None,
    neutral: Mapping[PointKey, object],
) -> object:
    """Return a neutral position, naming the point when it is absent."""
    if point is None or point not in neutral:
        name = "<unset>" if point is None else point_key_name(point)
        raise ValueError(
            f"Joint declaration references point '{name}', which is not present "
            "in this suspension"
        )
    return neutral[point]


def _resolve_plane_normal(
    spec: PlaneSpec,
    neutral: Mapping[PointKey, object],
) -> NDArray[np.float64]:
    """Resolve a declared plane to its unit normal."""
    if spec.normal is not None:
        return _resolve_axis_spec(spec.normal, neutral)
    corners = [
        extract_array(_require_point(point, neutral)) for point in spec.points or ()
    ]
    normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
    if float(np.linalg.norm(normal)) < EPS_GEOMETRIC:
        raise ValueError("A plane through three collinear points has no normal")
    return unit(normal)


def _resolve_constraint(
    side: JointSideSpec,
    neutral: Mapping[PointKey, object],
) -> AxisConstraint:
    """Collect the perpendicularity facts constraining one free direction."""
    perpendiculars: list[tuple[float, float, float]] = []
    if side.perpendicular_to is not None:
        axis = _resolve_axis_spec(side.perpendicular_to, neutral)
        perpendiculars.append(_as_tuple(axis))
    if side.in_plane is not None:
        perpendiculars.append(_as_tuple(_resolve_plane_normal(side.in_plane, neutral)))
    return AxisConstraint(tuple(perpendiculars))


def _as_tuple(vector: NDArray[np.float64]) -> tuple[float, float, float]:
    """Freeze a direction into a hashable triple."""
    return (float(vector[0]), float(vector[1]), float(vector[2]))


def _bodies_at(
    bodies: Sequence[RigidBody],
    point: PointKey,
) -> tuple[RigidBody, ...]:
    """Return every body that carries a point."""
    return tuple(body for body in bodies if point in body.points)


def _explicit_body(
    part: str | PartSpec,
    bodies: Sequence[RigidBody],
    neutral: Mapping[PointKey, object],
    side_name: str,
    joint_name: str,
) -> RigidBody:
    """Resolve an explicitly named or explicitly listed part."""
    if isinstance(part, PartSpec):
        points = tuple(part.points)
        for point in points:
            _require_point(point, neutral)
        explicit = RigidBody(
            name=f"{joint_name} {side_name}",
            points=points,
            mode=RotationMode.FITTED if len(points) >= 3 else RotationMode.TRANSPORT,
        )
        return resolve_body_modes((explicit,), neutral)[0]

    wanted = _slug(part)
    matches = [body for body in bodies if _slug(body.name) == wanted]
    if not matches:
        available = ", ".join(sorted(_slug(body.name) for body in bodies))
        raise ValueError(
            f"Joint '{joint_name}' names part '{part}', which is not a body in this "
            f"suspension. Available parts: {available}"
        )
    return matches[0]


def _pair_bodies(
    spec: JointSpec,
    candidates: Sequence[RigidBody],
    bodies: Sequence[RigidBody],
    neutral: Mapping[PointKey, object],
    joint_name: str,
) -> tuple[RigidBody, RigidBody]:
    """Assign the housing and bore bodies for one joint.

    An explicitly declared side wins. Where a side is not declared it takes
    whichever of the two bodies meeting at the point is left over, and when
    neither is declared the pair is assigned by convention: the housing goes
    to the part the bearing is pressed or threaded into -- the two-point
    member over a fully located one, and either over the chassis.

    The assignment is safe to make automatically because the misalignment
    angle is symmetric under swapping the two bodies. It still decides which
    side may be called ``indeterminate`` and which frame the exported relative
    rotation is expressed in, so callers report it rather than hiding it.
    """
    housing = (
        _explicit_body(spec.housing.part, bodies, neutral, "housing", joint_name)
        if spec.housing.part is not None
        else None
    )
    bore = (
        _explicit_body(spec.bore.part, bodies, neutral, "bore", joint_name)
        if spec.bore.part is not None
        else None
    )
    if housing is not None and bore is not None:
        return housing, bore

    if len(candidates) != 2:
        found = ", ".join(f"'{body.name}'" for body in candidates) or "none"
        raise ValueError(
            f"Joint '{joint_name}' needs exactly two bodies meeting at its point, "
            f"but {len(candidates)} carry it: {found}. Declare the sides "
            "explicitly with 'part', either by body name or as {points: [...]}."
        )

    if housing is not None:
        remaining = [body for body in candidates if body.name != housing.name]
        return housing, (remaining[0] if remaining else candidates[0])
    if bore is not None:
        remaining = [body for body in candidates if body.name != bore.name]
        return (remaining[0] if remaining else candidates[0]), bore

    ranked = sorted(
        candidates,
        key=lambda body: (
            0 if body.mode is RotationMode.TRANSPORT else 1,
            1 if body.mode is RotationMode.GROUND else 0,
        ),
    )
    return ranked[0], ranked[1]


def resolve_joints(suspension: "Suspension") -> tuple[ResolvedJoint, ...]:
    """Resolve every joint a suspension declares against its neutral pose.

    Only declared joints are resolved; a point that is not listed produces no
    body lookup, no columns, and no report entry.
    """
    declarations = suspension.joints
    if not declarations:
        return ()

    neutral = suspension.initial_state().positions
    assembly = suspension.assembly()
    bodies = resolve_body_modes(
        build_bodies(
            assembly.elements,
            assembly.points.fixed,
            suspension.rigid_attachments(),
        ),
        neutral,
    )

    resolved: list[ResolvedJoint] = []
    for key, spec in declarations.items():
        point = _joint_point(key, neutral)
        name = _slug(key)
        housing_body, bore_body = _pair_bodies(
            spec,
            _bodies_at(bodies, point),
            bodies,
            neutral,
            key,
        )
        resolved.append(
            _resolve_one(key, name, spec, point, housing_body, bore_body, neutral)
        )
    return tuple(resolved)


def _joint_point(key: str, neutral: Mapping[PointKey, object]) -> PointKey:
    """Resolve an authored joint key to the point it names."""
    from kinematics.core.enums import PointID
    from kinematics.core.schema.decoding import parse_enum

    try:
        point = parse_enum(PointID, key)
    except ValueError as error:
        raise ValueError(f"Joint '{key}' does not name a suspension point") from error
    _require_point(point, neutral)
    return point


def _resolve_one(
    key: str,
    name: str,
    spec: JointSpec,
    point: PointKey,
    housing_body: RigidBody,
    bore_body: RigidBody,
    neutral: Mapping[PointKey, object],
) -> ResolvedJoint:
    """Resolve one joint's directions and constraints."""
    bore_authored = spec.bore.authored_axis
    bore_axis = (
        _as_tuple(_resolve_axis_spec(bore_authored, neutral))
        if bore_authored is not None
        else None
    )
    if bore_authored is None and not spec.bore.is_optimize:
        raise ValueError(
            f"Joint '{key}' needs a bore axis: give 'bore.axis' a direction, or "
            "'optimize' to have the report solve for one."
        )

    spin_axis = housing_body.axis(neutral)
    housing_authored = spec.housing.authored_axis
    if spec.housing.is_indeterminate:
        if spin_axis is None:
            raise ValueError(
                f"Joint '{key}' declares an indeterminate housing, but part "
                f"'{housing_body.name}' is {housing_body.mode.description}. A spin "
                "is only undetermined on a two-point member."
            )
        mode = HousingMode.INDETERMINATE
        housing_axis = None
    elif housing_authored is not None:
        mode = HousingMode.AUTHORED
        housing_axis = _as_tuple(_resolve_axis_spec(housing_authored, neutral))
    else:
        # An undeclared housing is installed centred on the bore axis, which is
        # the ordinary case: the bearing starts life square in its cone.
        mode = HousingMode.CENTRED
        housing_axis = None

    joint = ResolvedJoint(
        name=name,
        label=spec.label or key,
        joint_type=spec.type,
        point=point,
        housing_body=housing_body,
        bore_body=bore_body,
        housing_mode=mode,
        housing_axis=housing_axis,
        bore_axis=bore_axis,
        bore_constraint=_resolve_constraint(spec.bore, neutral),
        spin_axis=None if spin_axis is None else _as_tuple(spin_axis),
        cone_deg=spec.housing.cone_deg,
    )
    _warn_on_constraint_violation(joint, key)
    return joint


def _warn_on_constraint_violation(joint: ResolvedJoint, key: str) -> None:
    """Reject an authored bore axis that breaks its own declared constraints."""
    if joint.bore_axis is None:
        return
    bore = np.asarray(joint.bore_axis, dtype=np.float64)
    for perpendicular in joint.bore_constraint.perpendiculars:
        deviation = abs(90.0 - angle_between_deg(np.asarray(perpendicular), bore))
        if deviation > 1e-6:
            raise ValueError(
                f"Joint '{key}' declares a bore axis {deviation:.3f} degrees away "
                "from the perpendicularity it also declares. Drop the constraint, "
                "or author an axis that satisfies it."
            )


# ==========================================================================
# 2. Per-state evaluation and export
# ==========================================================================
def relative_rotation(
    joint: ResolvedJoint,
    neutral: Mapping[PointKey, object],
    current: Mapping[PointKey, object],
) -> NDArray[np.float64]:
    """Return ``Q = R_A^T R_B`` for one joint at one solved state."""
    housing = joint.housing_body.rotation(neutral, current)
    bore = joint.bore_body.rotation(neutral, current)
    return housing.T @ bore


def misalignment_deg(
    joint: ResolvedJoint,
    relative: NDArray[np.float64],
) -> float | None:
    """Return the angle the bearing must absorb at one state.

    ``None`` when the bore axis is left to the report to optimise, since no
    per-step angle exists until an axis is chosen.
    """
    if joint.bore_axis is None:
        return None
    bore = np.asarray(joint.bore_axis, dtype=np.float64)
    rotated = relative @ bore
    if joint.housing_mode is HousingMode.INDETERMINATE:
        spin = np.asarray(joint.spin_axis, dtype=np.float64)
        return abs(joint.cone_deg - angle_between_deg(spin, rotated))
    housing = (
        bore
        if joint.housing_mode is HousingMode.CENTRED
        else np.asarray(joint.housing_axis, dtype=np.float64)
    )
    return angle_between_deg(housing, rotated)


def rotation_column_names(joint: ResolvedJoint) -> tuple[str, str, str]:
    """Return the three relative-rotation column identities for a joint."""
    return (
        f"joint_{joint.name}_rx",
        f"joint_{joint.name}_ry",
        f"joint_{joint.name}_rz",
    )


def misalignment_column_name(joint: ResolvedJoint) -> str:
    """Return the misalignment column identity for a joint."""
    return f"misalign_{joint.name}"


def joint_metric_specs(joints: Sequence[ResolvedJoint]) -> "tuple[MetricSpec, ...]":
    """Return export metadata for every declared joint's columns."""
    from kinematics.core.enums import Scope
    from kinematics.core.metrics.registry import MetricKind, MetricSpec
    from kinematics.core.metrics.units import MetricUnit

    specs: list[MetricSpec] = []
    for joint in joints:
        for column, component in zip(rotation_column_names(joint), "XYZ"):
            specs.append(
                MetricSpec(
                    column,
                    f"{joint.label} relative rotation {component}",
                    MetricUnit.DEG,
                    MetricKind.STATE,
                    Scope.CORNER,
                    "joint",
                )
            )
        if joint.bore_axis is not None:
            specs.append(
                MetricSpec(
                    misalignment_column_name(joint),
                    f"{joint.label} required {joint.joint_type.demand_label}",
                    MetricUnit.DEG,
                    MetricKind.STATE,
                    Scope.CORNER,
                    "joint",
                )
            )
    return tuple(specs)


def joint_metric_values(
    joints: Sequence[ResolvedJoint],
    neutral: Mapping[PointKey, object],
    current: Mapping[PointKey, object],
) -> "MetricRow":
    """Compute every declared joint's columns for one solved state."""
    row: OrderedDict[str, float | None] = OrderedDict()
    for joint in joints:
        relative = relative_rotation(joint, neutral, current)
        rotvec = np.degrees(rotvec_from_rotation(relative))
        for column, value in zip(rotation_column_names(joint), rotvec):
            row[column] = float(value)
        if joint.bore_axis is not None:
            row[misalignment_column_name(joint)] = misalignment_deg(joint, relative)
    return row


def describe_joints_for_export(
    joints: Sequence[ResolvedJoint],
) -> list[dict[str, object]]:
    """Describe declared joints for downstream reporting.

    Written into the results file's metadata header so that a report can
    optimise axes, name the parts involved, and state how each rotation was
    determined without re-reading the geometry file.
    """
    return [
        {
            "name": joint.name,
            "label": joint.label,
            "type": joint.joint_type.value,
            "point": point_key_name(joint.point),
            "housing_part": joint.housing_body.name,
            "housing_rotation": joint.housing_body.mode.value,
            "bore_part": joint.bore_body.name,
            "bore_rotation": joint.bore_body.mode.value,
            "housing_mode": joint.housing_mode.value,
            "housing_axis": joint.housing_axis,
            "bore_axis": joint.bore_axis,
            "bore_perpendiculars": [
                list(axis) for axis in joint.bore_constraint.perpendiculars
            ],
            "spin_axis": joint.spin_axis,
            "cone_deg": joint.cone_deg,
            "install_offset_deg": joint.install_offset_deg,
            "description": joint.describe(),
        }
        for joint in joints
    ]


# ==========================================================================
# 3. Post-sweep axis solving
#
# Everything below evaluates candidate axes against exported relative
# rotations. It never touches the solver, so a report can choose or re-choose
# bearing axes from sweep output alone, including output written before the
# axis model it is being asked about existed.
# ==========================================================================
def misalignment_series(
    relative: NDArray[np.float64],
    bore_axis: NDArray[np.float64],
    housing_mode: str,
    housing_axis: NDArray[np.float64] | None = None,
    spin_axis: NDArray[np.float64] | None = None,
    cone_deg: float = DEFAULT_CONE_DEG,
) -> NDArray[np.float64]:
    """Return the misalignment angle at every step, in degrees.

    ``relative`` is a ``(T, 3, 3)`` stack of per-step relative rotations.
    """
    return _candidate_angles(
        relative,
        np.asarray(bore_axis, dtype=np.float64).reshape(1, 3),
        housing_mode,
        housing_axis,
        spin_axis,
        cone_deg,
    )[0]


def _candidate_angles(
    relative: NDArray[np.float64],
    candidates: NDArray[np.float64],
    housing_mode: str,
    housing_axis: NDArray[np.float64] | None,
    spin_axis: NDArray[np.float64] | None,
    cone_deg: float,
) -> NDArray[np.float64]:
    """Return an ``(M, T)`` grid of angles for M candidate bore axes.

    Every housing mode reduces to projecting the candidates onto one per-step
    direction field, so all three are a single matrix product regardless of
    how many candidates are being scored.
    """
    if housing_mode == HousingMode.CENTRED.value:
        axes, angles = _rotation_axis_angle(relative)
        cos_beta = candidates @ axes.T
        cos_theta = 1.0 - (1.0 - cos_beta**2) * (1.0 - np.cos(angles))[None, :]
        return np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))

    if housing_mode == HousingMode.INDETERMINATE.value:
        if spin_axis is None:
            raise ValueError("An indeterminate housing needs its body's spin axis")
        pulled = np.einsum("tij,i->tj", relative, np.asarray(spin_axis, np.float64))
        tilt = np.degrees(np.arccos(np.clip(candidates @ pulled.T, -1.0, 1.0)))
        return np.abs(cone_deg - tilt)

    if housing_axis is None:
        raise ValueError("An authored housing needs its axis")
    pulled = np.einsum("tij,i->tj", relative, np.asarray(housing_axis, np.float64))
    return np.degrees(np.arccos(np.clip(candidates @ pulled.T, -1.0, 1.0)))


def _rotation_axis_angle(
    relative: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Decompose a stack of rotations into unit axes and angles in radians.

    A step with no relative rotation has no defined axis; any unit vector
    serves, because its angle is zero and the misalignment formula multiplies
    the axis term by ``1 - cos(0) = 0``.
    """
    rotvecs = np.asarray(
        [rotvec_from_rotation(rotation) for rotation in relative], dtype=np.float64
    )
    angles = np.linalg.norm(rotvecs, axis=1)
    safe = np.where(angles[:, None] < EPS_GEOMETRIC, np.array([1.0, 0.0, 0.0]), rotvecs)
    norms = np.linalg.norm(safe, axis=1, keepdims=True)
    return safe / norms, angles


def fibonacci_directions(count: int = 20000) -> NDArray[np.float64]:
    """Return near-uniformly spaced unit directions covering the whole sphere.

    The full sphere rather than a hemisphere: reversing a bore axis reverses
    the sense of its misalignment against a fixed housing, so antipodal
    candidates are not interchangeable in general.
    """
    indices = np.arange(count, dtype=np.float64) + 0.5
    z = 1.0 - 2.0 * indices / count
    radius = np.sqrt(np.clip(1.0 - z**2, 0.0, None))
    golden = np.pi * (1.0 + 5.0**0.5)
    theta = golden * indices
    return np.stack([radius * np.cos(theta), radius * np.sin(theta), z], axis=1)


def circle_directions(
    pole: NDArray[np.float64],
    count: int = 3600,
    cone_deg: float = 90.0,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return directions on a cone about ``pole``, with their clocking angles.

    At the default 90 degrees this is the great circle perpendicular to the
    pole: the set a rod end's bore can occupy as it is clocked on its shank.
    """
    axis = unit(np.asarray(pole, dtype=np.float64))
    seed = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(seed, axis))) > 0.9:
        seed = np.array([0.0, 1.0, 0.0])
    first = unit(np.cross(axis, seed))
    second = np.cross(axis, first)
    clocking = np.linspace(0.0, 2.0 * np.pi, count, endpoint=False)
    half = np.radians(cone_deg)
    directions = np.cos(half) * axis[None, :] + np.sin(half) * (
        np.cos(clocking)[:, None] * first[None, :]
        + np.sin(clocking)[:, None] * second[None, :]
    )
    return directions, np.degrees(clocking)


def candidate_axes(
    perpendiculars: Sequence[Sequence[float]] = (),
    samples: int = 20000,
) -> NDArray[np.float64]:
    """Build the candidate set a free direction is drawn from.

    No perpendicularity leaves two degrees of freedom and gets a sphere
    lattice; one leaves a clocking circle; two pin the direction up to sign,
    which is returned as the two antipodal solutions.
    """
    if not perpendiculars:
        return fibonacci_directions(samples)
    if len(perpendiculars) == 1:
        return circle_directions(
            np.asarray(perpendiculars[0], dtype=np.float64), count=3600
        )[0]
    first = unit(np.asarray(perpendiculars[0], dtype=np.float64))
    second = unit(np.asarray(perpendiculars[1], dtype=np.float64))
    pinned = np.cross(first, second)
    if float(np.linalg.norm(pinned)) < EPS_GEOMETRIC:
        raise ValueError(
            "Two parallel perpendicularity constraints do not pin a direction"
        )
    pinned = unit(pinned)
    return np.stack([pinned, -pinned])


def optimize_bore_axis(
    relative: NDArray[np.float64],
    housing_mode: str,
    housing_axis: NDArray[np.float64] | None = None,
    spin_axis: NDArray[np.float64] | None = None,
    cone_deg: float = DEFAULT_CONE_DEG,
    perpendiculars: Sequence[Sequence[float]] = (),
    samples: int = 20000,
    chunk: int = 2000,
) -> tuple[NDArray[np.float64], float]:
    """Return the bore axis minimising the worst misalignment over a sweep set.

    A dense candidate sweep followed by a local refinement. The objective is
    Lipschitz in the geodesic metric with a constant of order one, so a
    lattice at roughly half a degree already brackets the global optimum and
    the refinement only polishes it. Cost is one matrix product per chunk, so
    the whole solve is a fraction of a second for a full sweep set.
    """
    candidates = candidate_axes(perpendiculars, samples)
    best_axis = candidates[0]
    best_value = float("inf")
    for start in range(0, len(candidates), chunk):
        block = candidates[start : start + chunk]
        worst = _candidate_angles(
            relative, block, housing_mode, housing_axis, spin_axis, cone_deg
        ).max(axis=1)
        index = int(np.argmin(worst))
        if float(worst[index]) < best_value:
            best_value = float(worst[index])
            best_axis = block[index]

    if len(perpendiculars) >= 2:
        return best_axis, best_value
    return _refine_axis(
        best_axis,
        best_value,
        relative,
        housing_mode,
        housing_axis,
        spin_axis,
        cone_deg,
        perpendiculars,
    )


def _refine_axis(
    seed: NDArray[np.float64],
    seed_value: float,
    relative: NDArray[np.float64],
    housing_mode: str,
    housing_axis: NDArray[np.float64] | None,
    spin_axis: NDArray[np.float64] | None,
    cone_deg: float,
    perpendiculars: Sequence[Sequence[float]],
) -> tuple[NDArray[np.float64], float]:
    """Polish a lattice winner with a local search in a tangent chart."""
    from scipy.optimize import minimize

    if perpendiculars:
        pole = unit(np.asarray(perpendiculars[0], dtype=np.float64))
        basis = _tangent_basis(pole)
        start_angle = float(np.arctan2(np.dot(seed, basis[1]), np.dot(seed, basis[0])))

        def build(parameters: NDArray[np.float64]) -> NDArray[np.float64]:
            """Place a direction on the clocking circle."""
            angle = float(parameters[0])
            return np.cos(angle) * basis[0] + np.sin(angle) * basis[1]

        start = np.array([start_angle])
    else:
        basis = _tangent_basis(seed)

        def build(parameters: NDArray[np.float64]) -> NDArray[np.float64]:
            """Step away from the seed inside its own tangent plane."""
            offset = parameters[0] * basis[0] + parameters[1] * basis[1]
            return unit(seed + offset)

        start = np.zeros(2)

    def objective(parameters: NDArray[np.float64]) -> float:
        """Return the worst misalignment for one candidate direction."""
        direction = build(np.atleast_1d(parameters))
        return float(
            _candidate_angles(
                relative,
                direction.reshape(1, 3),
                housing_mode,
                housing_axis,
                spin_axis,
                cone_deg,
            ).max()
        )

    # Nelder-Mead's default simplex is a small relative step, which from a
    # start of zero collapses to a fraction of the lattice spacing and leaves
    # the search unable to reach the true optimum. Size the simplex to the
    # lattice instead, so the refinement actually explores the cell it landed
    # in.
    simplex = np.vstack(
        [start] + [start + REFINE_STEP * row for row in np.eye(len(start))]
    )
    result = minimize(
        objective,
        start,
        method="Nelder-Mead",
        options={
            "initial_simplex": simplex,
            "xatol": 1e-10,
            "fatol": 1e-12,
            "maxiter": 2000,
        },
    )
    if float(result.fun) < seed_value:
        return unit(build(np.atleast_1d(result.x))), float(result.fun)
    return seed, seed_value


def _tangent_basis(
    axis: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return two unit directions spanning the plane perpendicular to an axis."""
    normalized = unit(axis)
    seed = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(seed, normalized))) > 0.9:
        seed = np.array([0.0, 1.0, 0.0])
    first = unit(np.cross(normalized, seed))
    return first, np.cross(normalized, first)


def locked_clocking(
    relative: NDArray[np.float64],
    bore_axis: NDArray[np.float64],
    spin_axis: NDArray[np.float64],
    cone_deg: float = DEFAULT_CONE_DEG,
    count: int = 3600,
) -> tuple[float, float]:
    """Return the best fixed clocking for a housing on a two-point member.

    The indeterminate result assumes the member spins freely to the most
    favourable position at every instant, which is a lower bound. This is the
    other end of the band: the member does not spin at all, so a single
    clocking angle chosen at assembly must serve the whole sweep. The true
    demand lies between the two, depending on how freely the member actually
    turns in service.

    Returns the clocking angle in degrees and the worst misalignment it gives.
    """
    directions, clocking = circle_directions(spin_axis, count=count, cone_deg=cone_deg)
    rotated = np.einsum("tij,j->ti", relative, unit(np.asarray(bore_axis, np.float64)))
    cosines = np.clip(directions @ rotated.T, -1.0, 1.0)
    worst = np.degrees(np.arccos(cosines)).max(axis=1)
    best = int(np.argmin(worst))
    return float(clocking[best]), float(worst[best])
