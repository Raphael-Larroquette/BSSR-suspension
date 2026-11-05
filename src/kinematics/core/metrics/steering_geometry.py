"""ISO-aligned steering geometry on the axle-local road plane.

The road datum is the ISO 8855 local or equivalent road plane expressed in
chassis coordinates. The supported environment is straight and level, so road
space and world space are aligned; these calculations nevertheless use the
local road datum directly and do not require the inferred vehicle pose.
"""

from __future__ import annotations

from math import asin, degrees
from typing import TYPE_CHECKING

from kinematics.core.primitives.constants import EPS_GEOMETRIC

if TYPE_CHECKING:
    from kinematics.core.metrics.context import MetricContext
    from kinematics.core.primitives.geometry import Direction3, Vector3


def _road_displacement(ctx: MetricContext) -> Vector3 | None:
    """Return a chassis-coordinate displacement between two road-plane points."""
    ground_intersection = ctx.steering_axis_ground_intersection
    if ground_intersection is None:
        return None
    return ground_intersection - ctx.wheel_contact_centre


def _tyre_road_axes(
    ctx: MetricContext,
) -> tuple[Direction3, Direction3] | None:
    """Return right-handed tyre ``X_T`` and ``Y_T`` axes in the road plane.

    ``X_T`` is forward and ``Z_T`` is the upward road normal. ``Y_T`` is
    constructed as ``Z_T × X_T``, so ``X_T × Y_T = Z_T`` on both sides. This
    makes tyre +Y outward on the left but inboard on the right; scalar metrics
    fold their signs explicitly where required.
    """
    ground_normal = ctx.road.normal
    projected_axis = ctx.wheel_axis.vector() - ground_normal * ctx.wheel_axis.dot(
        ground_normal
    )
    if projected_axis.norm() < EPS_GEOMETRIC:
        return None
    outboard = projected_axis.normalize()
    longitudinal = (ctx.side_sign * outboard.cross(ground_normal)).normalize()
    lateral = ground_normal.cross(longitudinal).normalize()
    return longitudinal, lateral


def calculate_scrub_radius(ctx: MetricContext) -> float | None:
    """Return ISO scrub radius in millimetres.

    Following ISO 8855:2011 scrub radius (§7.2.10), this is the
    distance in the axle-local road plane from the tyre contact centre to the
    steering-axis intersection with that plane. Both points are represented
    in chassis coordinates. The value is an unsigned road-plane magnitude,
    not the commonly conflated signed lateral steering-axis offset, and does
    not use world space or an inferred chassis pitch.

    Returns ``None`` when the steering axis is parallel to the road plane.
    """
    displacement = _road_displacement(ctx)
    return None if displacement is None else displacement.norm()


def calculate_steering_axis_offset_ground(ctx: MetricContext) -> float | None:
    """Return ISO steering-axis offset at ground in millimetres.

    Following ISO 8855:2011 steering-axis offset at ground (§7.2.6), this is
    the signed lateral
    component along tyre ``Y_T`` from the tyre contact centre to the
    steering-axis intersection with the axle-local road plane. The tyre axis
    and both points are expressed in chassis coordinates. Positive means that
    the intersection is inboard of the contact centre. World space and inferred
    chassis pitch are not used.

    Returns ``None`` when the steering axis is parallel to the road plane or
    the wheel spin axis has no lateral projection into it.
    """
    displacement = _road_displacement(ctx)
    axes = _tyre_road_axes(ctx)
    if displacement is None or axes is None:
        return None
    _, lateral = axes
    # Tyre +Y points outboard on the left and inboard on the right. Fold the
    # right-handed tyre basis into the documented inboard-positive convention.
    return -ctx.side_sign * float(displacement.dot(lateral))


def calculate_mechanical_trail(ctx: MetricContext) -> float | None:
    """Return wheel-relative mechanical trail in millimetres.

    This is ISO 8855:2011 castor offset at ground (§7.2.3, also called castor
    trail or kinematic trail): the signed longitudinal component along tyre ``X_T``
    from the tyre contact centre to the steering-axis intersection with the
    axle-local road plane. The tyre axis and both points are expressed in
    chassis coordinates. Positive means that the intersection is ahead of the
    contact centre.

    It is deliberately not a raw chassis-X difference. At non-zero steer the
    tyre longitudinal axis rotates away from chassis X, and mechanical trail
    remains a wheel-relative steering-force lever arm. World space and inferred
    chassis pitch are not used.

    Returns ``None`` when the steering axis is parallel to the road plane or
    the wheel spin axis has no lateral projection into it.
    """
    displacement = _road_displacement(ctx)
    axes = _tyre_road_axes(ctx)
    if displacement is None or axes is None:
        return None
    longitudinal, _ = axes
    return float(displacement.dot(longitudinal))


def calculate_road_camber(ctx: MetricContext) -> float:
    """Return road-relative camber in degrees.

    This is the magnitude of ISO 8855:2011 inclination angle (§7.1.16): the
    angle between the road normal ``Z_T`` and the wheel plane, measured about
    the tyre axis ``X_T`` (the line where the wheel plane meets the road
    plane). Because ``X_T`` turns with the wheel, steer does not leak into it,
    which is how it differs from :func:`calculate_camber` (ISO §7.1.17, measured
    about the vehicle ``X_V`` axis against chassis +Z).

    **Deliberate deviation from ISO: the sign is mirrored like camber.** ISO
    signs inclination as a right-hand rotation about ``X_T`` for every wheel,
    so the same outward lean reads negative on the left and positive on the
    right. Here, as for camber, negative means the top of the wheel leans in
    towards the vehicle centreline and positive means it leans out, on both
    sides. The two are related by ``road_camber = -side_sign * inclination``
    (side_sign +1 left, -1 right).

    The wheel plane is normal to the spin axis, so the wheel is upright on the
    road exactly when the outboard spin axis ``a`` is perpendicular to the road
    normal ``n``. Any lean shows up as a component of ``a`` along ``n``: the
    outboard end of the axle drops when the top of the wheel leans out, so

        road_camber = -asin(a . n)

    with ``a`` from inboard to outboard and ``n`` the upward normal of the
    axle-local road plane, both in chassis coordinates. No side sign is needed.

    On a level road with the wheel straight ahead this equals ``camber``. The
    road plane is the one tangent to both wheel discs, so it tilts against the
    chassis in an asymmetric (roll) state; that tilt is not body roll, because
    the chassis is ground and no spring stiffness is modelled.
    """
    component = float(ctx.wheel_axis.dot(ctx.road.normal))
    return degrees(-asin(max(-1.0, min(1.0, component))))
