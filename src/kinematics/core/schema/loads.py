"""
Validated schema for a force-solve configuration file.

Every key is required. There are no built-in defaults to fall back to, so a
missing or misspelt key is an error naming it and a dry run is a complete
configuration check -- the same rule ``Working/sweep_sets/run.yaml`` follows, and
for the same reason: two places holding the same default is two places that can
disagree.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    """The vehicle's mass and the gravity it is solved under.

    The sprung/unsprung split and the front wheel rate are optional and are
    not used by the static force solve, which treats the whole car as one point
    mass at ``cg_position``. They are read only by the quasi-static corner
    sweep (``Working/sweep_sets/corner.py``). ``unsprung_mass_front`` is per
    wheel; ``unsprung_mass_rear`` is the single rear wheel; ``sprung_mass``
    excludes every wheel and suspension part. ``wheel_rate_front`` is the
    vertical stiffness at one front wheel centre, in N/mm, taken as constant.
    """

    mass: float
    g: float
    sprung_mass: float | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    unsprung_mass_front: float | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    unsprung_mass_rear: float | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    wheel_rate_front: float | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @field_validator("mass", "g")
    @classmethod
    def check_positive(cls, value: float) -> float:
        """Require a positive quantity."""
        if not value > 0.0:
            raise ValueError(f"must be greater than zero, got {value}")
        return value

    @field_validator(
        "sprung_mass", "unsprung_mass_front", "unsprung_mass_rear", "wheel_rate_front"
    )
    @classmethod
    def check_optional_positive(cls, value: float | None) -> float | None:
        """Require a positive quantity when one is given."""
        if value is not None and not value > 0.0:
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
                "outboard brake. See 'Not modelled' in docs/reference/forces.md."
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
    # A block per axle with the force on the chassis at every hardpoint.
    chassis: bool = True


class ForcesConfig(ForcesModel):
    """A complete, validated force-solve configuration."""

    version: str
    vehicle: VehicleMassConfig
    geometry: GeometryPathsConfig
    # Optional: a caller that shares one case file across configurations
    # passes it as --cases instead. resolve_paths() requires one or the other.
    cases: str | None = None
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
