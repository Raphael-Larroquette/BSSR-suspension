"""Shock linkages for a trailing arm: direct, or a rocker with a rod.

Five configurations, set by three choices (see ``docs/reference/geometry.md``):

=====  ==================  ================  =================================
type   ``rocker_mount``    ``spring.base``   layout
=====  ==================  ================  =================================
A      (direct)            chassis           shock chassis -> arm
B      chassis             chassis           rod arm -> rocker, shock -> chassis
C      chassis             arm               rod arm -> rocker, shock -> arm
D      arm                 chassis           dogbone chassis -> rocker, shock -> chassis
E      arm                 arm               dogbone chassis -> rocker, shock -> arm
=====  ==================  ================  =================================

Point names are shared by every rocker layout:

* ``rocker_axis_a/b``: the rocker pivot axis, on the chassis or the arm.
* ``pushrod_inboard``: the rod's end on the rocker.
* ``pushrod_outboard``: the rod's other end, on the arm (B, C; a push or pull
  rod) or on the chassis (D, E; a dogbone).
* ``strut_bottom``: the shock's moving end, on the rocker (on the arm for A).
* ``strut_top``: the shock's base end, on the chassis or the arm.

Kinematics. Every point fixed to the arm is a derived point, placed by the
arm's rotation about its pivot axis, exactly as the arm's own pickups are. The
rocker's two pickups (``pushrod_inboard``, ``strut_bottom``) are the only new
free points: the rod fixes its length, the pivot holds ``pushrod_inboard`` on a
circle, and ``strut_bottom`` is rigid to the rocker. Every layout is one degree
of freedom, driven by the arm.

Statics. Rod and shock are spherical at both ends (two-force members) and the
rocker pivot is a revolute pair closed by ``solve.pivot_axial``, so every
layout is statically determinate without a joint-type declaration.

Planar intent, 3D solve: the layouts are designed in side view, but solved in
3D. A rocker axis that is not parallel to the arm pivot axis solves, and is
warned about, because the linkage then moves out of its plane.
"""

from __future__ import annotations

import warnings
from collections import OrderedDict
from dataclasses import dataclass
from math import atan2, degrees
from typing import TYPE_CHECKING

import numpy as np

from kinematics.core.constraints import Constraint, DistanceConstraint
from kinematics.core.elements import (
    ElementType,
    RigidLinkElement,
    RockerElement,
    RockerPickup,
    RockerPickupType,
    SuspensionElement,
    VariableLengthLinkElement,
)
from kinematics.core.enums import LinkageMount, PointID, Scope
from kinematics.core.metrics.registry import MetricKind, MetricSpec
from kinematics.core.metrics.units import MetricUnit
from kinematics.core.primitives.constants import EPS_GEOMETRIC
from kinematics.core.primitives.geometry import Point3, extract_array
from kinematics.core.primitives.point_ref import PointKey
from kinematics.core.primitives.vector_utils.geometric import (
    compute_point_point_distance,
    compute_point_to_line_distance,
)
from kinematics.core.state import SuspensionState
from kinematics.core.suspensions.corner.attachments import (
    chiral_rigid_point_constraints,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from kinematics.core.metrics.main import MetricRow

#: Rocker axis more than this far from parallel to the arm pivot axis is warned.
PLANAR_TOLERANCE_DEG = 2.0

ROD_TRANSMISSION_SPEC = MetricSpec(
    "rod_transmission_angle",
    "Rod Transmission Angle",
    MetricUnit.DEG,
    MetricKind.STATE,
    Scope.CORNER,
    "linkage",
)
SHOCK_TRANSMISSION_SPEC = MetricSpec(
    "shock_transmission_angle",
    "Shock Transmission Angle",
    MetricUnit.DEG,
    MetricKind.STATE,
    Scope.CORNER,
    "linkage",
)
ROCKER_ANGLE_SPEC = MetricSpec(
    "rocker_angle",
    "Rocker Angle",
    MetricUnit.DEG,
    MetricKind.STATE,
    Scope.CORNER,
    "linkage",
)

ROCKER_POINTS = (PointID.ROCKER_AXIS_A, PointID.ROCKER_AXIS_B)
ROCKER_FREE_POINTS = (PointID.PUSHROD_INBOARD, PointID.STRUT_BOTTOM)


def transmission_angle_deg(
    line_a: np.ndarray,
    line_b: np.ndarray,
    lever_root: np.ndarray,
    lever_tip: np.ndarray,
    axis: np.ndarray,
) -> float:
    """
    Return the transmission angle between a line and a lever, in degrees.

    Both are projected onto the plane normal to the lever's rotation ``axis``
    and the acute angle between them is returned: 90 means the line pushes
    square on the lever (best leverage), 0 means it pushes along the lever
    (toggle: no leverage, forces unbounded).
    """
    axis = axis / np.linalg.norm(axis)

    def planar(vector: np.ndarray) -> np.ndarray:
        return vector - axis * float(np.dot(vector, axis))

    line = planar(line_b - line_a)
    lever = planar(lever_tip - lever_root)
    norms = float(np.linalg.norm(line) * np.linalg.norm(lever))
    if norms <= EPS_GEOMETRIC:
        return float("nan")
    cosine = min(1.0, abs(float(np.dot(line, lever))) / norms)
    return degrees(float(np.arccos(cosine)))


def _foot(point: np.ndarray, axis_a: np.ndarray, axis_b: np.ndarray) -> np.ndarray:
    """Return the foot of the perpendicular from a point onto a line."""
    direction = (axis_b - axis_a) / np.linalg.norm(axis_b - axis_a)
    return axis_a + direction * float(np.dot(point - axis_a, direction))


@dataclass(frozen=True)
class TrailingArmLinkage:
    """
    The shock layout of a trailing arm.

    ``rocker_mount`` is ``None`` for direct actuation (layout A). The arm is
    identified to this class only by its pivot points; the suspension supplies
    the arm's rotation through its derived-point machinery.
    """

    rocker_mount: LinkageMount | None = None
    base: LinkageMount = LinkageMount.CHASSIS

    def __post_init__(self) -> None:
        """Reject the one combination with no physical meaning."""
        if self.rocker_mount is None and self.base is LinkageMount.ARM:
            raise ValueError(
                "spring.base: arm needs a rocker (actuation.type: pushrod_rocker). "
                "With direct actuation both shock ends would be on the arm."
            )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    @property
    def has_rocker(self) -> bool:
        """Whether a rocker and rod sit between the arm and the shock."""
        return self.rocker_mount is not None

    @property
    def layout(self) -> str:
        """Return the layout letter used in the docs (A-E)."""
        if not self.has_rocker:
            return "A"
        return {
            (LinkageMount.CHASSIS, LinkageMount.CHASSIS): "B",
            (LinkageMount.CHASSIS, LinkageMount.ARM): "C",
            (LinkageMount.ARM, LinkageMount.CHASSIS): "D",
            (LinkageMount.ARM, LinkageMount.ARM): "E",
        }[(self.rocker_mount, self.base)]

    @property
    def rod_label(self) -> str:
        """Return the rod's part name: a pushrod off the arm, else a dogbone."""
        return "Dogbone" if self.rocker_mount is LinkageMount.ARM else "Pushrod"

    # ------------------------------------------------------------------
    # Points
    # ------------------------------------------------------------------
    def required_points(self) -> frozenset[PointID]:
        """Return every point this layout needs authored."""
        points = {PointID.STRUT_TOP, PointID.STRUT_BOTTOM}
        if self.has_rocker:
            points |= {
                *ROCKER_POINTS,
                PointID.PUSHROD_INBOARD,
                PointID.PUSHROD_OUTBOARD,
            }
        return frozenset(points)

    def free_points(self) -> tuple[PointID, ...]:
        """Return the rocker's solved pickups; direct actuation adds none."""
        return ROCKER_FREE_POINTS if self.has_rocker else ()

    def arm_points(self) -> tuple[PointID, ...]:
        """Return the points fixed to the arm, placed by its rotation."""
        if not self.has_rocker:
            return (PointID.STRUT_BOTTOM,)
        points: list[PointID] = []
        if self.rocker_mount is LinkageMount.CHASSIS:
            points.append(PointID.PUSHROD_OUTBOARD)
        else:
            points.extend(ROCKER_POINTS)
        if self.base is LinkageMount.ARM:
            points.append(PointID.STRUT_TOP)
        return tuple(points)

    def output_points(self) -> tuple[PointID, ...]:
        """Return the layout's points in export order."""
        if not self.has_rocker:
            return (PointID.STRUT_TOP, PointID.STRUT_BOTTOM)
        return (
            *ROCKER_POINTS,
            PointID.PUSHROD_OUTBOARD,
            PointID.PUSHROD_INBOARD,
            PointID.STRUT_TOP,
            PointID.STRUT_BOTTOM,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(
        self,
        hardpoints: Mapping[PointKey, Point3],
        pivot_axis: np.ndarray,
    ) -> None:
        """Reject degenerate rockers; warn on a non-planar rocker axis."""
        if not self.has_rocker:
            return
        axis_a = hardpoints[PointID.ROCKER_AXIS_A]
        axis_b = hardpoints[PointID.ROCKER_AXIS_B]
        if compute_point_point_distance(axis_a, axis_b) <= EPS_GEOMETRIC:
            raise ValueError("ROCKER_AXIS_A/B must be distinct points.")
        direction = (axis_b - axis_a).normalize()
        for point in ROCKER_FREE_POINTS:
            if (
                compute_point_to_line_distance(hardpoints[point], axis_a, direction)
                <= EPS_GEOMETRIC
            ):
                raise ValueError(
                    f"{point.name} must not lie on the rocker axis: a pickup on "
                    "the pivot has no lever arm."
                )
        if (
            compute_point_point_distance(
                hardpoints[PointID.PUSHROD_INBOARD],
                hardpoints[PointID.PUSHROD_OUTBOARD],
            )
            <= EPS_GEOMETRIC
        ):
            raise ValueError("PUSHROD_INBOARD and PUSHROD_OUTBOARD must differ.")
        rocker_axis = extract_array(axis_b) - extract_array(axis_a)
        cosine = abs(float(np.dot(rocker_axis, pivot_axis))) / float(
            np.linalg.norm(rocker_axis) * np.linalg.norm(pivot_axis)
        )
        skew = degrees(float(np.arccos(min(1.0, cosine))))
        if skew > PLANAR_TOLERANCE_DEG:
            warnings.warn(
                f"The rocker axis is {skew:.1f} deg from parallel to the trailing "
                "arm pivot axis. The linkage is designed in side view and solved "
                "in 3D, so it will move out of its plane; check this is intended.",
                stacklevel=2,
            )

    # ------------------------------------------------------------------
    # Kinematics
    # ------------------------------------------------------------------
    def constraints(self, initial: SuspensionState) -> list[Constraint]:
        """Fix the rod length, the rocker pivot, and the shock end to the rocker."""
        if not self.has_rocker:
            return []
        positions = initial.positions

        def distance(point_a: PointID, point_b: PointID) -> DistanceConstraint:
            return DistanceConstraint(
                point_a,
                point_b,
                compute_point_point_distance(positions[point_a], positions[point_b]),
            )

        return [
            distance(PointID.PUSHROD_OUTBOARD, PointID.PUSHROD_INBOARD),
            distance(PointID.PUSHROD_INBOARD, PointID.ROCKER_AXIS_A),
            distance(PointID.PUSHROD_INBOARD, PointID.ROCKER_AXIS_B),
            *chiral_rigid_point_constraints(
                initial,
                PointID.STRUT_BOTTOM,
                (
                    PointID.ROCKER_AXIS_A,
                    PointID.ROCKER_AXIS_B,
                    PointID.PUSHROD_INBOARD,
                ),
            ),
        ]

    # ------------------------------------------------------------------
    # Elements
    # ------------------------------------------------------------------
    def elements(self) -> tuple[SuspensionElement, ...]:
        """Return the rod, rocker and shock; direct actuation is the shock only."""
        spring_damper = VariableLengthLinkElement(
            label="Spring/Damper",
            type=ElementType.SPRING_DAMPER,
            point_a=PointID.STRUT_TOP,
            point_b=PointID.STRUT_BOTTOM,
        )
        if not self.has_rocker:
            return (spring_damper,)
        return (
            RigidLinkElement(
                label=self.rod_label,
                type=ElementType.PUSHROD,
                point_a=PointID.PUSHROD_OUTBOARD,
                point_b=PointID.PUSHROD_INBOARD,
            ),
            RockerElement(
                label="Rocker",
                rotation_axis=ROCKER_POINTS,
                pickups=(
                    RockerPickup(PointID.PUSHROD_INBOARD, RockerPickupType.PUSHROD),
                    RockerPickup(PointID.STRUT_BOTTOM, RockerPickupType.DAMPER),
                ),
            ),
            spring_damper,
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    def metric_specs(self) -> tuple[MetricSpec, ...]:
        """Declare the transmission angles, and the rocker angle with a rocker."""
        if not self.has_rocker:
            return (SHOCK_TRANSMISSION_SPEC,)
        return (ROD_TRANSMISSION_SPEC, SHOCK_TRANSMISSION_SPEC, ROCKER_ANGLE_SPEC)

    def metric_values(
        self,
        state: SuspensionState,
        initial: SuspensionState,
        pivot_points: tuple[PointID, PointID],
        arm_point: PointID,
    ) -> MetricRow:
        """Return transmission angles and, with a rocker, the rocker angle.

        ``pivot_points`` are the arm's pivot axis and ``arm_point`` is any
        point of the arm off that axis (its solved anchor).
        """

        def at(source: SuspensionState, point: PointID) -> np.ndarray:
            return extract_array(source.get(point))

        pivot_a, pivot_b = (at(state, point) for point in pivot_points)
        top = at(state, PointID.STRUT_TOP)
        bottom = at(state, PointID.STRUT_BOTTOM)
        row: MetricRow = OrderedDict()

        if not self.has_rocker:
            row["shock_transmission_angle"] = transmission_angle_deg(
                top, bottom, _foot(bottom, pivot_a, pivot_b), bottom, pivot_b - pivot_a
            )
            return row

        axis_a, axis_b = (at(state, point) for point in ROCKER_POINTS)
        axis = axis_b - axis_a
        inboard = at(state, PointID.PUSHROD_INBOARD)
        outboard = at(state, PointID.PUSHROD_OUTBOARD)
        row["rod_transmission_angle"] = transmission_angle_deg(
            outboard, inboard, _foot(inboard, axis_a, axis_b), inboard, axis
        )
        row["shock_transmission_angle"] = transmission_angle_deg(
            top, bottom, _foot(bottom, axis_a, axis_b), bottom, axis
        )
        row["rocker_angle"] = self._rocker_angle(
            state, initial, pivot_points, arm_point
        )
        return row

    def _rocker_angle(
        self,
        state: SuspensionState,
        initial: SuspensionState,
        pivot_points: tuple[PointID, PointID],
        arm_point: PointID,
    ) -> float:
        """
        Return the rocker's rotation relative to whatever carries it, in degrees.

        Signed by the right-hand rule about ``rocker_axis_a -> rocker_axis_b``
        at design. On the chassis that is the rocker's rotation; on the arm the
        arm's own rotation (about the same direction) is subtracted.
        """

        def at(source: SuspensionState, point: PointID) -> np.ndarray:
            return extract_array(source.get(point))

        def rotation(point: PointID, axis_points: tuple[PointID, PointID]) -> float:
            """Rotation of a point about a (possibly moving) axis, design -> now."""
            design_a, design_b = (at(initial, p) for p in axis_points)
            now_a, now_b = (at(state, p) for p in axis_points)
            reference = design_b - design_a
            reference /= np.linalg.norm(reference)
            before = at(initial, point) - _foot(at(initial, point), design_a, design_b)
            after = at(state, point) - _foot(at(state, point), now_a, now_b)
            return atan2(
                float(np.dot(np.cross(before, after), reference)),
                float(np.dot(before, after)),
            )

        angle = rotation(PointID.PUSHROD_INBOARD, ROCKER_POINTS)
        if self.rocker_mount is LinkageMount.ARM:
            # The arm turns about its pivot axis; count that turn about the
            # rocker's axis direction (they are parallel by design intent).
            design_a, design_b = (at(initial, p) for p in ROCKER_POINTS)
            pivot_a, pivot_b = (at(initial, p) for p in pivot_points)
            rocker_axis = design_b - design_a
            pivot_axis = pivot_b - pivot_a
            sign = 1.0 if float(np.dot(rocker_axis, pivot_axis)) >= 0.0 else -1.0
            angle -= sign * rotation(arm_point, pivot_points)
        return degrees(angle)
