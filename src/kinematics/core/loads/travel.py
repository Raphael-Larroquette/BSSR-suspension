"""
Static force solve repeated along a solved sweep.

Each step of a sweep is a pose; at every pose the same load cases are solved
with the moving suspension's joints where that step put them. The load is the
**constant case load**: every wheel's contact-patch force is found once, at the
design condition, and applied at the posed contact patch. What changes along
travel is therefore only the geometry: how the linkage leverages that load
into its joints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from kinematics.core.enums import AxlePosition, PointID
from kinematics.core.loads.cases import LoadCase
from kinematics.core.loads.main import ForceModelOptions, solve_forces
from kinematics.core.loads.results import PartCaseLoads
from kinematics.core.primitives.geometry import extract_array
from kinematics.core.primitives.point_ref import PointRef, Side
from kinematics.core.state import SuspensionState
from kinematics.core.suspensions.base import Suspension


@dataclass(frozen=True)
class TravelRow:
    """One part's loads, for one case, at one step of the sweep."""

    step: int
    wheel_travel: float  # wheel-centre z from design on this row's side, mm
    loads: PartCaseLoads


@dataclass(frozen=True)
class ForceTravel:
    """Forces along a sweep: the moving axle's parts and chassis, every step."""

    axle: AxlePosition
    cases: tuple[LoadCase, ...]
    steps: int
    rows: tuple[TravelRow, ...]
    diagnostics: tuple[str, ...]


def solve_forces_over_travel(
    suspensions: Sequence[Suspension],
    moving: int,
    states: Sequence[SuspensionState],
    cases: Sequence[LoadCase],
    mass: float,
    gravity: float,
    options: ForceModelOptions = ForceModelOptions(),
) -> ForceTravel:
    """
    Solve ``cases`` at every state of ``suspensions[moving]``.

    The other suspensions stay at their design condition. Only rows of the
    moving suspension's axle are kept: the others do not move, so their loads
    are the static solve's at every step.

    Args:
        suspensions: The vehicle's models, as for :func:`solve_forces`.
        moving: Index of the swept suspension in ``suspensions``.
        states: The sweep's solved states, in step order.
        cases: The load cases to solve at every step.
        mass: Total as-raced vehicle mass in kilograms.
        gravity: Gravitational acceleration in metres per second squared.
        options: Structure, axial-split, and numerical policy.
    """
    if not states:
        raise ValueError("A force-over-travel solve needs at least one state")
    swept = suspensions[moving]
    if swept.config is None or swept.config.axle_position is None:
        raise ValueError(f"Suspension '{swept.name}' does not declare axle_position")
    axle = swept.config.axle_position
    design = swept.initial_state()

    rows: list[TravelRow] = []
    diagnostics: dict[str, None] = {}
    for step, state in enumerate(states):
        poses: list[SuspensionState | None] = [None] * len(suspensions)
        poses[moving] = state
        run = solve_forces(suspensions, cases, mass, gravity, options, poses)
        for message in run.solution.diagnostics:
            diagnostics.setdefault(f"step {step}: {message}")
        for block in (*run.solution.blocks, *run.solution.chassis):
            for row in block.rows:
                if row.axle is axle:
                    rows.append(
                        TravelRow(
                            step=step,
                            wheel_travel=_wheel_travel(swept, design, state, row.side),
                            loads=row,
                        )
                    )
    return ForceTravel(
        axle=axle,
        cases=tuple(cases),
        steps=len(states),
        rows=tuple(rows),
        diagnostics=tuple(diagnostics),
    )


def _wheel_travel(
    suspension: Suspension,
    design: SuspensionState,
    state: SuspensionState,
    side: Side,
) -> float:
    """Return one side's wheel-centre z from design, in millimetres."""
    key = (
        PointRef(side, PointID.WHEEL_CENTER)
        if suspension.is_axle
        else (PointID.WHEEL_CENTER)
    )
    return float(extract_array(state.get(key))[2] - extract_array(design.get(key))[2])
