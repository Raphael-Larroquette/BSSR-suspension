"""
Whole-vehicle assembly for a static force solve.

One geometry file describes one axle or one corner. A load case is a
whole-vehicle statement, so the front/rear split cannot be found from either
file alone: this module composes them, checks that they agree about the
vehicle they belong to, and collects the tyre contact patches the load is
distributed over.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

from kinematics.core.enums import AxlePosition, PointID
from kinematics.core.primitives.geometry import extract_array
from kinematics.core.primitives.point_ref import PointKey, PointRef, Side
from kinematics.core.suspensions.base import Suspension

# Both files describe one vehicle in one frame, so the distance between the
# axles must reproduce the authored wheelbase. A millimetre of slack absorbs
# contact-patch construction; anything larger means the files disagree.
WHEELBASE_TOLERANCE_MM = 1.0

# Slack allowed between two files' authored centre-of-gravity coordinates.
CG_TOLERANCE_MM = 1e-6


@dataclass(frozen=True)
class ContactPatch:
    """
    One tyre contact patch, in vehicle coordinates at the design condition.

    ``name`` is the stable identity used in output and diagnostics, and
    ``point`` is the key the patch is known by inside its own suspension, which
    is how the force solve finds the body that carries the wheel.
    """

    name: str
    axle: AxlePosition
    side: Side
    point: PointKey
    position: NDArray[np.float64]

    @property
    def point_name(self) -> str:
        """Return the unqualified point name, for use as an output column."""
        base = self.point.point if isinstance(self.point, PointRef) else self.point
        return base.name.lower()


@dataclass(frozen=True)
class VehicleModel:
    """A composed vehicle: mass, centre of gravity, and its contact patches."""

    mass: float
    gravity: float
    cg: NDArray[np.float64]
    wheelbase: float
    patches: tuple[ContactPatch, ...]

    @property
    def weight(self) -> float:
        """Return the static vehicle weight in newtons."""
        return self.mass * self.gravity

    @property
    def road_height(self) -> float:
        """Return the road plane's height, as the contact patches place it.

        At the design condition this is nominally zero, but the contact patch
        is constructed from the tyre radius and the axle position, so it lands
        a fraction of a millimetre off. Measuring the centre-of-gravity height
        from here rather than from ``z = 0`` is what makes the closed-form
        transfer formulas reproduce the solved answer exactly.
        """
        return float(np.mean([patch.position[2] for patch in self.patches]))

    @property
    def cg_height(self) -> float:
        """Return the centre-of-gravity height above the road plane."""
        return float(self.cg[2]) - self.road_height

    def patches_on(self, axle: AxlePosition) -> tuple[ContactPatch, ...]:
        """Return the contact patches belonging to one axle."""
        return tuple(patch for patch in self.patches if patch.axle is axle)

    def track(self, axle: AxlePosition) -> float | None:
        """
        Return an axle's track width, or ``None`` when it has no lateral span.

        A single centreline wheel has no track. It is not an error: it is the
        reason a three-wheeler carries all of its lateral load transfer on the
        other axle.
        """
        patches = self.patches_on(axle)
        if len(patches) != 2:
            return None
        return abs(float(patches[0].position[1] - patches[1].position[1]))


def build_vehicle(
    suspensions: Sequence[Suspension],
    mass: float,
    gravity: float,
) -> VehicleModel:
    """
    Compose one vehicle from the loaded suspensions, validating agreement.

    Args:
        suspensions: The loaded axle or corner models, in any order.
        mass: Total as-raced vehicle mass in kilograms.
        gravity: Gravitational acceleration in metres per second squared.

    Returns:
        The composed vehicle with its contact patches.

    Raises:
        ValueError: If the models disagree about the vehicle, if one carries no
            configuration, or if their axles are not one wheelbase apart.
    """
    if mass <= 0.0:
        raise ValueError(f"Vehicle mass must be positive, got {mass}")
    if gravity <= 0.0:
        raise ValueError(f"Gravitational acceleration must be positive, got {gravity}")

    configs = []
    for suspension in suspensions:
        if suspension.config is None:
            raise ValueError(f"Suspension '{suspension.name}' has no configuration")
        configs.append(suspension.config)

    reference = configs[0]
    for suspension, config in zip(suspensions[1:], configs[1:]):
        offset = float(
            np.max(
                np.abs(
                    extract_array(config.cg_position)
                    - extract_array(reference.cg_position)
                )
            )
        )
        if offset > CG_TOLERANCE_MM:
            raise ValueError(
                f"'{suspensions[0].name}' and '{suspension.name}' disagree about "
                f"cg_position: {tuple(extract_array(reference.cg_position))} versus "
                f"{tuple(extract_array(config.cg_position))}. Both files describe "
                "one vehicle and must state the same value."
            )
        if abs(config.wheelbase - reference.wheelbase) > CG_TOLERANCE_MM:
            raise ValueError(
                f"'{suspensions[0].name}' and '{suspension.name}' disagree about "
                f"wheelbase: {reference.wheelbase} versus {config.wheelbase}."
            )

    patches = tuple(
        patch for suspension in suspensions for patch in _contact_patches(suspension)
    )
    _check_axle_separation(patches, reference.wheelbase)

    return VehicleModel(
        mass=float(mass),
        gravity=float(gravity),
        cg=extract_array(reference.cg_position),
        wheelbase=float(reference.wheelbase),
        patches=patches,
    )


def _contact_patches(suspension: Suspension) -> tuple[ContactPatch, ...]:
    """Collect one suspension's wheel contact centres as vehicle contact patches."""
    if suspension.config is None or suspension.config.axle_position is None:
        raise ValueError(
            f"Suspension '{suspension.name}' does not declare axle_position, so "
            "its wheels cannot be placed on the vehicle."
        )
    axle = suspension.config.axle_position
    positions = suspension.initial_state().positions

    if suspension.is_axle:
        keys = [
            (side, PointRef(side, PointID.WHEEL_CONTACT_CENTRE))
            for side in sorted(suspension.corners)
        ]
    else:
        keys = [(suspension.side, PointID.WHEEL_CONTACT_CENTRE)]

    patches: list[ContactPatch] = []
    for side, key in keys:
        if key not in positions:
            raise ValueError(
                f"Suspension '{suspension.name}' has no wheel contact centre for "
                f"the {side.name.lower()} side."
            )
        patches.append(
            ContactPatch(
                name=_patch_name(axle, side),
                axle=axle,
                side=side,
                point=key,
                position=extract_array(positions[key]),
            )
        )
    return tuple(patches)


def _patch_name(axle: AxlePosition, side: Side) -> str:
    """Return the stable output identity for one contact patch."""
    if side is Side.CENTER:
        return axle.value
    return f"{axle.value}_{side.name.lower()}"


def _check_axle_separation(
    patches: Sequence[ContactPatch],
    wheelbase: float,
) -> None:
    """Require the composed axles to sit one authored wheelbase apart."""
    front = [patch for patch in patches if patch.axle is AxlePosition.FRONT]
    rear = [patch for patch in patches if patch.axle is AxlePosition.REAR]
    if not front or not rear:
        raise ValueError(
            "A force solve needs both a front and a rear model: got "
            f"{len(front)} front and {len(rear)} rear contact patches."
        )

    front_x = float(np.mean([patch.position[0] for patch in front]))
    rear_x = float(np.mean([patch.position[0] for patch in rear]))
    separation = front_x - rear_x
    if abs(separation - wheelbase) > WHEELBASE_TOLERANCE_MM:
        raise ValueError(
            f"The front and rear contact patches are {separation:.3f} mm apart but "
            f"the authored wheelbase is {wheelbase:.3f} mm. The two geometry files "
            "must describe one vehicle in one coordinate frame."
        )
