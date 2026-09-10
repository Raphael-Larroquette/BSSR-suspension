"""
Validated schema for a force-solve configuration file.

Every key is required. There are no built-in defaults to fall back to, so a
missing or misspelt key is an error naming it and a dry run is a complete
configuration check -- the same rule ``models/Sweep_Set/run.yaml`` follows, and
for the same reason: two places holding the same default is two places that can
disagree.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from kinematics.core.enums import (
    MomentReporting,
    OutputFrame,
    RackTreatment,
    TorqueReaction,
    WheelLiftPolicy,
)
from kinematics.core.loads.system import MomentReference
from kinematics.core.schema.decoding import Point3Value


class ForcesModel(BaseModel):
    """Strict base for every force-configuration section."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")


class VehicleMassConfig(ForcesModel):
    """The vehicle's mass and the gravity it is solved under."""

    mass: float
    g: float

    @field_validator("mass", "g")
    @classmethod
    def check_positive(cls, value: float) -> float:
        """Require a positive quantity."""
        if not value > 0.0:
            raise ValueError(f"must be greater than zero, got {value}")
        return value


class GeometryPathsConfig(ForcesModel):
    """Which geometry files compose the vehicle."""

    front: str
    rear: str


class ToleranceConfig(ForcesModel):
    """Numerical limits the solve is checked against."""

    rank: float
    residual: float


class PivotAxialConfig(ForcesModel):
    """
    How the axial load is split across each coaxial joint pair.

    ``default`` is ``"even"`` or the name of the joint that carries all of it.
    ``overrides`` keys that policy by part name, side-agnostically, so one
    entry covers both corners of an axle.
    """

    default: str
    overrides: dict[str, str]


class SolveConfig(ForcesModel):
    """Solver policy: references, redundancy closure, and load-path choices."""

    moment_reference: MomentReference | Point3Value
    pivot_axial: PivotAxialConfig
    rack: RackTreatment
    brake_torque_reaction: TorqueReaction
    on_wheel_lift: WheelLiftPolicy
    tolerances: ToleranceConfig

    @field_validator("rack")
    @classmethod
    def check_rack(cls, value: RackTreatment) -> RackTreatment:
        """Reject the rack treatment that is not implemented."""
        if value is RackTreatment.FLOATING:
            raise ValueError(
                "rack 'floating' is not implemented. A free rack chains three "
                "two-force members through one joint and couples both front "
                "corners into a single system, which the unknown catalogue does "
                "not yet express. Use 'grounded'."
            )
        return value

    @field_validator("brake_torque_reaction")
    @classmethod
    def check_brake_reaction(cls, value: TorqueReaction) -> TorqueReaction:
        """Reject the brake reaction path that is not implemented."""
        if value is TorqueReaction.SPRUNG:
            raise ValueError(
                "brake_torque_reaction 'sprung' (an inboard brake) is not "
                "implemented. The linkage would see the longitudinal force at "
                "wheel-centre height rather than at the ground, which changes "
                "wishbone and upright loads substantially. Use 'unsprung', an "
                "outboard brake. See 'Limitations' in docs/force.md."
            )
        return value


class AttachConfig(ForcesModel):
    """One point folded into whichever part carries all of its anchors."""

    point: str
    anchors: list[str]


class StructureConfig(ForcesModel):
    """How the kinematic body list is turned into a structural one."""

    weld: list[list[str]]
    attach: list[AttachConfig]
    ground: list[str]
    ignore: list[str]


class OutputConfig(ForcesModel):
    """How the result is written."""

    frame: OutputFrame
    moments: MomentReporting
    per_part_files: bool


class ForcesConfig(ForcesModel):
    """A complete, validated force-solve configuration."""

    version: str
    vehicle: VehicleMassConfig
    geometry: GeometryPathsConfig
    cases: str
    solve: SolveConfig
    structure: StructureConfig
    output: OutputConfig

    @field_validator("version")
    @classmethod
    def check_version(cls, value: str) -> str:
        """Require a version string so a file can be migrated later."""
        if not value.strip():
            raise ValueError("version must not be empty")
        return value
