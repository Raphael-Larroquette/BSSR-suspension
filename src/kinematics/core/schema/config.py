"""Suspension configuration schema models."""

from __future__ import annotations

from math import isfinite

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from kinematics.core.enums import (
    ArbType,
    AxlePosition,
    HeaveLinkType,
    SteeringType,
    TorqueReaction,
)
from kinematics.core.primitives.constants import EPS_GEOMETRIC, MM_PER_INCH
from kinematics.core.schema.decoding import Direction3Value, Point3Value


class TireConfig(BaseModel):
    """
    Tire dimensions, and the radius the design condition is measured at.

    Two radii matter and they are not the same number. The section dimensions
    give the **unloaded** radius, which is what the tyre measures off the car.
    Hardpoints, however, are authored at design ride height, where the tyre
    carries load and its centre therefore sits a deflection lower. That smaller
    number is the **loaded** radius, and it is the one that decides where the
    contact centre lands relative to the authored axle height.

    Leaving ``loaded_radius`` unset keeps the unloaded radius for both, which is
    the rigid-disc assumption the tool has always made. Stating it makes the
    model self-consistent: the contact centre then lands on ``z = 0`` exactly,
    instead of a deflection's worth below it, which is the condition
    ``MODELS.md`` warns about when it says a contact centre off the road plane
    means the tyre and axle points disagree.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    aspect_ratio: float
    section_width: float
    rim_diameter: float
    loaded_radius: float | None = None

    @field_validator("aspect_ratio")
    @classmethod
    def check_aspect_ratio(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError(f"aspect_ratio must be in [0, 1], got {value}")
        return value

    @model_validator(mode="after")
    def check_loaded_radius(self) -> "TireConfig":
        """
        Keep a stated loaded radius physically possible for this tyre.

        A loaded pneumatic tyre deflects, so its radius is smaller than the
        unloaded one; a larger value means the two inputs describe different
        tyres. Rejecting a value under half the unloaded radius catches a unit
        slip, which would otherwise put the contact centre somewhere plausible
        enough to go unnoticed.
        """
        if self.loaded_radius is None:
            return self
        unloaded = self.nominal_radius
        if not isfinite(self.loaded_radius) or self.loaded_radius <= 0.0:
            raise ValueError(
                f"loaded_radius must be finite and positive, got {self.loaded_radius}"
            )
        if self.loaded_radius > unloaded:
            raise ValueError(
                f"loaded_radius {self.loaded_radius} mm exceeds the unloaded "
                f"radius {unloaded:.3f} mm implied by the section dimensions. A "
                "loaded tyre deflects, so it cannot be larger; check which tyre "
                "each input describes."
            )
        if self.loaded_radius < unloaded / 2.0:
            raise ValueError(
                f"loaded_radius {self.loaded_radius} mm is less than half the "
                f"unloaded radius {unloaded:.3f} mm, which is more deflection "
                "than a tyre has. Check the units."
            )
        return self

    @property
    def sidewall_height(self) -> float:
        """Calculate sidewall height in mm."""
        return self.aspect_ratio * self.section_width

    @property
    def rim_diameter_mm(self) -> float:
        """Convert rim diameter from inches to mm."""
        return self.rim_diameter * MM_PER_INCH

    @property
    def nominal_radius(self) -> float:
        """Calculate nominal unloaded tire radius in mm."""
        return (self.rim_diameter_mm + 2 * self.sidewall_height) / 2

    @property
    def design_radius(self) -> float:
        """
        Return the radius the design condition is measured at, in mm.

        The stated loaded radius when there is one, else the unloaded radius.
        Every geometric consumer — the contact centre, the axle ground closure,
        the road-plane metrics and the drawn wheel — uses this, so a model that
        states a loaded radius is treated consistently everywhere rather than in
        some places only.
        """
        return self.nominal_radius if self.loaded_radius is None else self.loaded_radius


class WheelConfig(BaseModel):
    """Wheel offset and tire configuration."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    offset: float
    tire: TireConfig


class CamberShimConfig(BaseModel):
    """Geometry and design/setup thickness for an outboard camber shim."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    shim_face_point_a: Point3Value
    shim_face_point_b: Point3Value
    shim_face_normal: Direction3Value
    design_thickness: float
    setup_thickness: float

    @model_validator(mode="after")
    def validate_face_definition(self) -> "CamberShimConfig":
        datum_separation = (self.shim_face_point_b - self.shim_face_point_a).norm()
        if datum_separation < EPS_GEOMETRIC:
            raise ValueError("shim_face_point_a and shim_face_point_b must be distinct")
        return self


class VehicleConfig(BaseModel):
    """Vehicle-wide configuration shared across all axles."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    cg_position: Point3Value
    wheelbase: float
    front_brake_bias: float | None = None
    driven_axle: AxlePosition | None = None
    # Where the driven wheel's torque is reacted, which selects the force line
    # anti-squat is built on. There is no default: a hub motor and an inboard
    # motor give answers a tyre radius of leverage apart, so anti-squat is left
    # undefined rather than guessed. Required alongside driven_axle.
    drive_torque_reaction: TorqueReaction | None = None

    @field_validator("wheelbase")
    @classmethod
    def check_positive_vehicle_length(cls, value: float) -> float:
        """Require a finite positive wheelbase for vehicle-level metrics."""
        if not isfinite(value) or value <= 0.0:
            raise ValueError("Vehicle length inputs must be finite and positive")
        return value

    @field_validator("front_brake_bias")
    @classmethod
    def check_front_brake_bias(cls, value: float | None) -> float | None:
        """Require front brake bias to be a fraction of total braking force."""
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError(f"front_brake_bias must be in [0, 1], got {value}")
        return value


class AntiRollConfig(BaseModel):
    """Selected axle anti-roll mechanism."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: ArbType


class HeaveLinkConfig(BaseModel):
    """Selected axle heave-link mechanism."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: HeaveLinkType


class SteeringConfig(BaseModel):
    """Selected steering actuator for one axle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: SteeringType


class AxleConfig(BaseModel):
    """Configuration and shared mechanisms owned by one axle."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    axle_position: AxlePosition
    steering: SteeringConfig
    wheel: WheelConfig
    anti_roll: AntiRollConfig
    heave_link: HeaveLinkConfig


class CornerConfig(BaseModel):
    """Side-local setup applied to one corner model."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    camber_shim: CamberShimConfig | None = None


class SuspensionConfig(VehicleConfig):
    """Complete runtime configuration for one built corner suspension."""

    steering: SteeringConfig
    wheel: WheelConfig
    axle_position: AxlePosition | None = None
    camber_shim: CamberShimConfig | None = None

    @classmethod
    def from_parts(
        cls,
        vehicle: VehicleConfig,
        axle: AxleConfig,
        corner: CornerConfig,
    ) -> "SuspensionConfig":
        """Combine shared vehicle data with one corner's local setup."""
        return cls.model_validate(
            {
                **vehicle.model_dump(),
                "steering": axle.steering,
                "wheel": axle.wheel,
                "axle_position": axle.axle_position,
                "camber_shim": corner.camber_shim,
            }
        )
