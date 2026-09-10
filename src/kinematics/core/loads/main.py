"""
End-to-end static force solve.

Composes the vehicle, builds each model's structural graph, and runs every load
case over the independent subsystems that graph falls into. The geometry never
moves, so the unknown catalogue and the coefficient matrix depend only on the
model: a case changes the right-hand side and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np

from kinematics.core.enums import AxlePosition, WheelLiftPolicy
from kinematics.core.loads.cases import LoadCase
from kinematics.core.loads.distribution import PatchLoad, solve_patch_loads
from kinematics.core.loads.results import (
    WHEEL_LIFT,
    ForceSolution,
    JointLoad,
    PartCaseLoads,
    build_blocks,
    disambiguate_part_names,
)
from kinematics.core.loads.structure import (
    DEFAULT_STRUCTURE,
    ForceBody,
    ForceGraph,
    StructurePolicy,
    Subsystem,
    build_force_graph,
)
from kinematics.core.loads.system import (
    ExternalLoad,
    SolveOptions,
    SubsystemSolution,
    skew,
    solve_subsystem,
)
from kinematics.core.loads.unknowns import EVEN, UnknownCatalog, build_unknowns
from kinematics.core.loads.vehicle import ContactPatch, VehicleModel, build_vehicle
from kinematics.core.primitives.point_ref import Side
from kinematics.core.suspensions.base import Suspension

_SIDE_ORDER = {Side.LEFT: 0, Side.RIGHT: 1, Side.CENTER: 2}


@dataclass(frozen=True)
class ForceModelOptions:
    """Everything about a force solve that is a policy rather than geometry."""

    structure: StructurePolicy = DEFAULT_STRUCTURE
    axial_default: str = EVEN
    axial_overrides: Mapping[str, str] = field(default_factory=dict)
    solve: SolveOptions = SolveOptions()
    on_wheel_lift: WheelLiftPolicy = WheelLiftPolicy.REPORT


@dataclass(frozen=True)
class CornerModel:
    """One subsystem, its unknowns, and the contact patch that loads it."""

    axle: AxlePosition
    graph: ForceGraph
    subsystem: Subsystem
    catalog: UnknownCatalog
    patch: ContactPatch
    loaded_body: ForceBody


@dataclass(frozen=True)
class ForceRun:
    """A solved force run, with the models kept for reporting."""

    solution: ForceSolution
    vehicle: VehicleModel
    corners: tuple[CornerModel, ...]


def build_corner_models(
    suspensions: Sequence[Suspension],
    vehicle: VehicleModel,
    options: ForceModelOptions = ForceModelOptions(),
) -> tuple[CornerModel, ...]:
    """
    Build one solvable corner model per contact patch.

    Raises:
        ValueError: If a contact patch is not carried by any structural part,
            or if a subsystem carries no wheel and therefore no load.
    """
    corners: list[CornerModel] = []
    for suspension in suspensions:
        graph = build_force_graph(suspension, options.structure)
        patches = [
            patch
            for patch in vehicle.patches
            if patch.point in {point for body in graph.bodies for point in body.points}
        ]
        for patch in patches:
            loaded = next(
                (body for body in graph.bodies if patch.point in body.points),
                None,
            )
            if loaded is None:
                raise ValueError(
                    f"Contact patch '{patch.name}' is not carried by any part of "
                    f"'{suspension.name}'."
                )
            subsystem = next(
                subsystem
                for subsystem in graph.subsystems
                if loaded.name in {body.name for body in subsystem.bodies}
            )
            corners.append(
                CornerModel(
                    axle=patch.axle,
                    graph=graph,
                    subsystem=subsystem,
                    catalog=build_unknowns(
                        subsystem,
                        loaded_bodies=(loaded.name,),
                        axial_default=options.axial_default,
                        axial_overrides=options.axial_overrides,
                    ),
                    patch=patch,
                    loaded_body=loaded,
                )
            )
    return tuple(corners)


def solve_forces(
    suspensions: Sequence[Suspension],
    cases: Sequence[LoadCase],
    mass: float,
    gravity: float,
    options: ForceModelOptions = ForceModelOptions(),
) -> ForceRun:
    """
    Solve every load case over every corner of the composed vehicle.

    Args:
        suspensions: The loaded axle and corner models.
        cases: The load cases to solve.
        mass: Total as-raced vehicle mass in kilograms.
        gravity: Gravitational acceleration in metres per second squared.
        options: Structure, axial-split, and numerical policy.

    Returns:
        The solved run, with the corner models retained for reporting.
    """
    if not cases:
        raise ValueError("A force solve needs at least one load case")

    vehicle = build_vehicle(suspensions, mass, gravity)
    corners = build_corner_models(suspensions, vehicle, options)
    part_names = disambiguate_part_names(
        {
            (corner.axle.value, body.base_name): ""
            for corner in corners
            for body in corner.subsystem.bodies
            if not body.is_ground
        }
    )

    rows: list[PartCaseLoads] = []
    diagnostics: list[str] = []
    worst_condition = 0.0

    for case in cases:
        patch_loads = {
            load.patch.name: load for load in solve_patch_loads(vehicle, case)
        }
        for corner in corners:
            load = patch_loads[corner.patch.name]
            if load.lifted:
                message = (
                    f"Case {case.label}: '{corner.patch.name}' normal load is "
                    f"{load.normal:.1f} N. That wheel has lifted and this "
                    "corner's loads describe a tyre pulling on the road; do "
                    "not use them."
                )
                if options.on_wheel_lift is WheelLiftPolicy.FAIL:
                    raise ValueError(message)
                diagnostics.append(message)
            solution = solve_subsystem(
                corner.catalog,
                externals=(
                    ExternalLoad(
                        body=corner.loaded_body.name,
                        name=corner.patch.point_name,
                        position=corner.patch.position,
                        force=load.force,
                    ),
                ),
                options=options.solve,
            )
            worst_condition = max(worst_condition, solution.condition)
            rows.extend(_rows_for_corner(corner, case, solution, load, part_names))

    rows.sort(
        key=lambda row: (
            cases.index(row.case),
            _SIDE_ORDER[row.side],
        )
    )
    return ForceRun(
        solution=ForceSolution(
            vehicle=vehicle,
            cases=tuple(cases),
            blocks=build_blocks(rows),
            diagnostics=tuple(diagnostics),
            max_condition=worst_condition,
        ),
        vehicle=vehicle,
        corners=corners,
    )


def _rows_for_corner(
    corner: CornerModel,
    case: LoadCase,
    solution: SubsystemSolution,
    patch_load: PatchLoad,
    part_names: Mapping[tuple[str, str], str],
) -> list[PartCaseLoads]:
    """Turn one corner's solved forces into one output row per part."""
    flags = (WHEEL_LIFT,) if patch_load.lifted else ()
    rows: list[PartCaseLoads] = []
    for body in corner.subsystem.bodies:
        if body.is_ground:
            continue
        loads = [
            JointLoad(
                name=base_joint_name(joint.name),
                position=joint.position,
                force=joint.sign_for(body.name) * solution.forces[joint.name],
            )
            for joint in sorted(
                corner.subsystem.joints_on(body.name), key=lambda item: item.name
            )
        ]
        if body.name == corner.loaded_body.name:
            loads.append(
                JointLoad(
                    name=corner.patch.point_name,
                    position=corner.patch.position,
                    force=patch_load.force,
                    applied=True,
                )
            )
        rows.append(
            PartCaseLoads(
                part=part_names[(corner.axle.value, body.base_name)],
                side=body.side,
                case=case,
                loads=tuple(loads),
                flags=flags,
            )
        )
    return rows


def base_joint_name(name: str) -> str:
    """Strip the side qualifier so both corners share one column set."""
    for prefix in ("left_", "right_"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def part_residuals(row: PartCaseLoads) -> tuple[float, float]:
    """
    Return one reported row's force and moment closure, in N and N-mm.

    Both should be zero to solver tolerance. They are computed from the loads
    the output actually carries, including the applied tyre force, so they
    exercise the signs a reader would apply in an FEA run rather than the
    matrix the solve was assembled from.
    """
    force = np.zeros(3)
    moment = np.zeros(3)
    for load in row.loads:
        force += load.force
        moment += skew(load.position) @ load.force
        if load.moment is not None:
            moment += load.moment
    return float(np.max(np.abs(force))), float(np.max(np.abs(moment)))
