"""
Solved joint loads, arranged the way they are reported.

Output is grouped by part rather than by joint: a part's block is the load set
an FEA run applies to that one component, and because the externally applied
tyre force is included alongside the joint reactions, every block sums to zero.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from kinematics.core.loads.cases import LoadCase
from kinematics.core.loads.vehicle import VehicleModel
from kinematics.core.primitives.point_ref import Side

# Flag raised on a case where a tyre normal load has gone negative.
WHEEL_LIFT = "WHEEL_LIFT"


@dataclass(frozen=True)
class JointLoad:
    """
    One load acting on a part, in vehicle axes and newtons.

    ``moment`` is always ``None`` today: every unknown in the current model is a
    pure force, so no joint carries one. It is carried here so that a joint
    model that does -- a revolute rocker, or a bushing with rotational
    stiffness -- becomes a solver change alone, with the results type and the
    writer already able to express it.
    """

    name: str
    position: NDArray[np.float64]
    force: NDArray[np.float64]
    moment: NDArray[np.float64] | None = None
    applied: bool = False

    @property
    def column_name(self) -> str:
        """Return the name this load is written under."""
        return f"{self.name} (applied)" if self.applied else self.name


@dataclass(frozen=True)
class PartCaseLoads:
    """Every load on one part, for one case, on one side of the vehicle."""

    part: str
    side: Side
    case: LoadCase
    loads: tuple[JointLoad, ...]
    flags: tuple[str, ...] = ()

    @property
    def side_label(self) -> str:
        """Return the side as it is written in output."""
        return "centre" if self.side is Side.CENTER else self.side.name.lower()


@dataclass(frozen=True)
class PartBlock:
    """One part's output block: a stable column set and its rows."""

    part: str
    columns: tuple[str, ...]
    rows: tuple[PartCaseLoads, ...]

    @property
    def has_moments(self) -> bool:
        """Whether any load in this block carries a moment."""
        return any(load.moment is not None for row in self.rows for load in row.loads)


@dataclass(frozen=True)
class ForceSolution:
    """The complete result of a force solve."""

    vehicle: VehicleModel
    cases: tuple[LoadCase, ...]
    blocks: tuple[PartBlock, ...]
    diagnostics: tuple[str, ...] = ()
    max_condition: float = 0.0


def build_blocks(rows: list[PartCaseLoads]) -> tuple[PartBlock, ...]:
    """
    Group solved rows into per-part blocks with a stable column set.

    A part's columns are fixed across every case and both sides, so a block is
    a rectangle even when one case flags a lifted wheel.
    """
    ordered: dict[str, list[PartCaseLoads]] = {}
    for row in rows:
        ordered.setdefault(row.part, []).append(row)

    blocks: list[PartBlock] = []
    for part, part_rows in ordered.items():
        columns: list[str] = []
        for row in part_rows:
            for load in row.loads:
                if load.column_name not in columns:
                    columns.append(load.column_name)
        blocks.append(
            PartBlock(part=part, columns=tuple(columns), rows=tuple(part_rows))
        )
    return tuple(blocks)


def disambiguate_part_names(
    names: dict[tuple[str, str], str],
) -> dict[tuple[str, str], str]:
    """
    Qualify part names by axle only where two axles share one base name.

    Keys are ``(axle, base name)``. A vehicle whose front and rear both carry an
    'Upper Wishbone' gets 'Front Upper Wishbone' and 'Rear Upper Wishbone'; one
    that does not keeps the plain name.
    """
    counts: dict[str, set[str]] = {}
    for axle, base in names:
        counts.setdefault(base, set()).add(axle)
    return {
        (axle, base): (f"{axle.title()} {base}" if len(counts[base]) > 1 else base)
        for axle, base in names
    }
