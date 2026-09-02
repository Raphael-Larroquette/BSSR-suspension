"""Validated declarations for bearing misalignment reporting.

A joint is where two rigid bodies meet at a shared point. Two unit directions
determine how much misalignment the bearing there must absorb:

``bore``
    The bolt / ball bore axis, fixed to one part.
``housing``
    The bearing housing's centred direction, fixed to the other part.

These are declared independently, so the two need not coincide at the neutral
pose. When they do not, the bearing is installed deliberately off centre and
the difference is reported as the joint's install offset. Forcing them to
coincide would hide both an assembly error and a legitimate design move: a
pre-tilted housing can roughly halve the required misalignment rating when the
excursion is one-sided.

Only joints declared here produce output. Nothing is reported for a point that
is not listed.
"""

from __future__ import annotations

from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kinematics.core.enums import JointType
from kinematics.core.schema.decoding import AxisValue, PointIDValue


class AxisSpec(BaseModel):
    """One neutral-pose direction, in any of four equivalent spellings.

    All four resolve against the neutral state in chassis coordinates:

    - ``{from: a, to: b}``   the direction between two authored points
    - ``{vector: [x, y, z]}``  an explicit vector, normalized on resolution
    - ``{x: .., y: .., z: ..}``  the same, spelled componentwise
    - ``{chassis_axis: z}``  a principal chassis axis

    The two-point form is the one to reach for in practice: it names the
    kingpin axis, a wishbone pivot axis, a link's own axis, or a rocker axis
    without hard-coding numbers that go stale the moment a hardpoint moves.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    from_point: PointIDValue | None = Field(default=None, alias="from")
    to_point: PointIDValue | None = Field(default=None, alias="to")
    vector: Sequence[float] | None = None
    chassis_axis: AxisValue | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None

    @model_validator(mode="after")
    def check_exactly_one_spelling(self) -> "AxisSpec":
        """Require exactly one complete direction spelling."""
        two_point = self.from_point is not None or self.to_point is not None
        components = self.x is not None or self.y is not None or self.z is not None
        selected = [
            two_point,
            self.vector is not None,
            self.chassis_axis is not None,
            components,
        ]
        if sum(selected) != 1:
            raise ValueError(
                "An axis takes exactly one of: 'from'/'to', 'vector', "
                "'chassis_axis', or 'x'/'y'/'z' components"
            )
        if two_point and (self.from_point is None or self.to_point is None):
            raise ValueError("A two-point axis requires both 'from' and 'to'")
        if two_point and self.from_point == self.to_point:
            raise ValueError("A two-point axis requires two distinct points")
        if components and (self.x is None or self.y is None or self.z is None):
            raise ValueError("A componentwise axis requires all of 'x', 'y', 'z'")
        if self.vector is not None and len(tuple(self.vector)) != 3:
            raise ValueError("An axis vector must have three components")
        return self


class PartSpec(BaseModel):
    """An explicit rigid body, named by the points that define it.

    The escape hatch for a joint whose bodies the assembly does not already
    declare. Three or more non-collinear points give a fully determined
    orientation; two points leave a spin about their own axis undetermined and
    are handled by the transport convention.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    points: tuple[PointIDValue, ...]

    @model_validator(mode="after")
    def check_point_count(self) -> "PartSpec":
        """Require at least the two points that fix a direction."""
        if len(self.points) < 2:
            raise ValueError("An explicit part requires at least two points")
        if len(set(self.points)) != len(self.points):
            raise ValueError("An explicit part lists a point more than once")
        return self


class PlaneSpec(BaseModel):
    """A plane, by its normal or by three points lying in it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    normal: AxisSpec | None = None
    points: tuple[PointIDValue, ...] | None = None

    @model_validator(mode="after")
    def check_exactly_one_spelling(self) -> "PlaneSpec":
        """Require exactly one complete plane spelling."""
        if (self.normal is None) == (self.points is None):
            raise ValueError("A plane takes exactly one of 'normal' or 'points'")
        if self.points is not None and len(self.points) != 3:
            raise ValueError("A plane through points requires exactly three points")
        if self.points is not None and len(set(self.points)) != 3:
            raise ValueError("A plane through points requires three distinct points")
        return self


class JointSideSpec(BaseModel):
    """One side of a joint: the part, and the direction fixed to it.

    ``perpendicular_to`` and ``in_plane`` state the same kind of fact -- the
    direction is perpendicular to some axis -- and both narrow the search when
    the direction is optimised. Giving both pins the direction exactly (up to
    sign), which is how a housing whose bore must lie in the wishbone's plane
    *and* perpendicular to its own shank is declared.

    ``cone_deg`` is the half-angle between the direction and the axis of the
    body carrying it, used when that body's spin is undetermined. It defaults
    to a rod end's 90 degrees, whose bore is perpendicular to its shank.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    part: str | PartSpec | None = None
    axis: AxisSpec | Literal["optimize", "centred", "indeterminate"] | None = None
    perpendicular_to: AxisSpec | None = None
    in_plane: PlaneSpec | None = None
    cone_deg: float = 90.0

    @model_validator(mode="after")
    def check_cone(self) -> "JointSideSpec":
        """Require a physically meaningful cone half-angle."""
        if not 0.0 <= self.cone_deg <= 180.0:
            raise ValueError(f"cone_deg must be in [0, 180], got {self.cone_deg}")
        return self

    @property
    def is_optimize(self) -> bool:
        """Whether this direction is left for the report to solve."""
        return self.axis == "optimize"

    @property
    def is_centred(self) -> bool:
        """Whether this direction is pinned to the opposite side's."""
        return self.axis == "centred"

    @property
    def is_indeterminate(self) -> bool:
        """Whether this direction rides a body whose spin is undetermined."""
        return self.axis == "indeterminate"

    @property
    def authored_axis(self) -> AxisSpec | None:
        """Return the authored direction, if one was given."""
        return self.axis if isinstance(self.axis, AxisSpec) else None


class JointSpec(BaseModel):
    """One declared joint to report misalignment for."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str | None = None
    type: JointType = JointType.SPHERICAL
    bore: JointSideSpec = Field(default_factory=JointSideSpec)
    housing: JointSideSpec = Field(default_factory=JointSideSpec)

    @model_validator(mode="after")
    def check_resolvable(self) -> "JointSpec":
        """Reject combinations phase-one evaluation cannot resolve."""
        if self.bore.is_centred:
            raise ValueError(
                "'centred' belongs on the housing: it pins the housing "
                "direction to the authored bore axis"
            )
        if self.bore.is_indeterminate:
            raise ValueError(
                "'indeterminate' belongs on the housing, which is the side "
                "carried by a body whose spin is undetermined"
            )
        if self.housing.is_optimize:
            raise ValueError(
                "Optimising the housing direction is not implemented yet. "
                "Use 'centred' to install the housing on the bore axis, or "
                "'indeterminate' when the housing rides a two-point link."
            )
        return self


JointsSpec = dict[str, JointSpec]
