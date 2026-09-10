"""
File-to-file force-solve command service.

Holds no terminal behaviour: it resolves paths, loads and validates every
input, runs the solve, and writes the result. The CLI layer above it decides
what to print.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from kinematics.cli.io.cases_loader import load_cases
from kinematics.cli.io.force_writer import (
    ForceWriteOptions,
    write_forces,
    write_per_part_files,
)
from kinematics.cli.io.forces_loader import load_forces_config
from kinematics.cli.io.loaders import load_geometry
from kinematics.cli.io.provenance import compute_file_hash
from kinematics.core.loads.cases import LoadCase
from kinematics.core.loads.main import (
    ForceModelOptions,
    ForceRun,
    part_residuals,
    solve_forces,
)
from kinematics.core.loads.results import PartBlock, PartCaseLoads
from kinematics.core.loads.structure import AttachRule, StructurePolicy
from kinematics.core.loads.system import MomentReference, SolveOptions
from kinematics.core.primitives.geometry import extract_array
from kinematics.core.schema.loads import ForcesConfig
from kinematics.core.suspensions.base import Suspension

DEFAULT_CONFIG_NAME = "forces.yaml"


@dataclass(frozen=True)
class ForcePaths:
    """The input files a run actually used, after CLI overrides."""

    config: Path
    front: Path
    rear: Path
    cases: Path


@dataclass(frozen=True)
class ForceCommandRun:
    """Everything a completed force command produced."""

    config: ForcesConfig
    paths: ForcePaths
    suspensions: tuple[Suspension, ...]
    cases: tuple[LoadCase, ...]
    run: ForceRun
    output_path: Path | None = None
    per_part_paths: tuple[Path, ...] = ()


def resolve_paths(
    config: ForcesConfig,
    config_path: Path,
    front: Path | None = None,
    rear: Path | None = None,
    cases: Path | None = None,
) -> ForcePaths:
    """Resolve input paths, taking CLI overrides over the configuration file.

    A configuration file names its geometry relative to itself, so the pair
    travels together. The joined path is normalized but deliberately not
    resolved to an absolute one: it goes into the output file's provenance
    header, where a machine-specific path would make two identical runs on two
    machines look different.
    """
    base = config_path.parent

    def relative(value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return Path(os.path.normpath(base / path))

    return ForcePaths(
        config=config_path,
        front=front or relative(config.geometry.front),
        rear=rear or relative(config.geometry.rear),
        cases=cases or relative(config.cases),
    )


def build_options(config: ForcesConfig) -> ForceModelOptions:
    """Translate a validated configuration into solver options."""
    reference = config.solve.moment_reference
    if isinstance(reference, MomentReference):
        solve = SolveOptions(
            moment_reference=reference,
            rank_tolerance=config.solve.tolerances.rank,
            residual_tolerance=config.solve.tolerances.residual,
        )
    else:
        solve = SolveOptions(
            moment_reference=MomentReference.POINT,
            reference_point=extract_array(reference),
            rank_tolerance=config.solve.tolerances.rank,
            residual_tolerance=config.solve.tolerances.residual,
        )

    return ForceModelOptions(
        structure=StructurePolicy(
            weld=tuple(tuple(group) for group in config.structure.weld),
            attach=tuple(
                AttachRule(point=rule.point, anchors=tuple(rule.anchors))
                for rule in config.structure.attach
            ),
            ground=tuple(config.structure.ground),
            ignore=tuple(config.structure.ignore),
        ),
        axial_default=config.solve.pivot_axial.default,
        axial_overrides=dict(config.solve.pivot_axial.overrides),
        solve=solve,
        on_wheel_lift=config.solve.on_wheel_lift,
    )


def load_inputs(
    config_path: Path = Path(DEFAULT_CONFIG_NAME),
    front: Path | None = None,
    rear: Path | None = None,
    cases: Path | None = None,
    mass: float | None = None,
) -> ForceCommandRun:
    """
    Load and validate every input, then solve, without writing anything.

    This is what ``--dry-run``, ``--describe``, and ``--check`` all run: any
    problem with the configuration, the geometry, or the cases surfaces here.
    """
    config = load_forces_config(config_path)
    paths = resolve_paths(config, config_path, front, rear, cases)
    suspensions = (load_geometry(paths.front), load_geometry(paths.rear))
    case_list = load_cases(paths.cases)
    run = solve_forces(
        suspensions,
        case_list,
        mass=mass if mass is not None else config.vehicle.mass,
        gravity=config.vehicle.g,
        options=build_options(config),
    )
    return ForceCommandRun(
        config=config,
        paths=paths,
        suspensions=suspensions,
        cases=case_list,
        run=run,
    )


def run_force_files(
    config_path: Path = Path(DEFAULT_CONFIG_NAME),
    front: Path | None = None,
    rear: Path | None = None,
    cases: Path | None = None,
    out: Path | None = None,
    mass: float | None = None,
    per_part_dir: Path | None = None,
) -> ForceCommandRun:
    """Load, solve, and write one force run."""
    loaded = load_inputs(config_path, front, rear, cases, mass)
    options = ForceWriteOptions(
        frame=loaded.config.output.frame,
        moments=loaded.config.output.moments,
        metadata=_provenance(loaded.paths),
    )

    if out is not None:
        write_forces(loaded.run.solution, out, options)

    written: tuple[Path, ...] = ()
    directory = per_part_dir
    if directory is None and loaded.config.output.per_part_files and out is not None:
        directory = out.parent / f"{out.stem}_parts"
    if directory is not None:
        written = write_per_part_files(loaded.run.solution, directory, options)

    return ForceCommandRun(
        config=loaded.config,
        paths=loaded.paths,
        suspensions=loaded.suspensions,
        cases=loaded.cases,
        run=loaded.run,
        output_path=out,
        per_part_paths=written,
    )


def describe(loaded: ForceCommandRun) -> str:
    """
    Render the structural model the solve was built on.

    Printed rather than solved for, because every name ``forces.yaml`` can
    refer to appears here: part names for ``structure``, and joint names for
    ``pivot_axial``.
    """
    lines: list[str] = []
    vehicle = loaded.run.vehicle
    centre = tuple(round(float(value), 3) for value in vehicle.cg)
    lines.append(
        f"vehicle: {vehicle.mass} kg, cg {centre}, wheelbase {vehicle.wheelbase} mm"
    )
    for patch in vehicle.patches:
        position = tuple(round(float(value), 3) for value in patch.position)
        lines.append(f"  contact patch {patch.name}: {position}")

    for corner in loaded.run.corners:
        catalog = corner.catalog
        lines.append("")
        lines.append(
            f"subsystem '{corner.subsystem.name}' ({corner.axle.value}), loaded at "
            f"'{corner.loaded_body.name}'"
        )
        for body in corner.subsystem.bodies:
            if body.is_ground:
                continue
            kind = (
                "two-force member"
                if body in catalog.two_force_bodies
                else f"{len(corner.subsystem.joints_on(body.name))} joints"
            )
            lines.append(f"  part {body.name} ({kind})")
        for joint in sorted(corner.subsystem.joints, key=lambda item: item.name):
            lines.append(f"  joint {joint.name}: {joint.bodies[0]} | {joint.bodies[1]}")
        for pair in catalog.coaxial:
            lines.append(f"  coaxial {pair.describe()}")
        lines.append(
            f"  system: {catalog.rows} equations, {catalog.width} unknowns "
            f"({len(catalog.constraints)} constraint row(s))"
        )
    lines.append("")
    lines.append(f"worst condition number: {loaded.run.solution.max_condition:.3e}")
    return "\n".join(lines)


def check(loaded: ForceCommandRun) -> tuple[str, bool]:
    """
    Render per-part equilibrium residuals for every reported row.

    Returns the report and whether every part closed within tolerance.
    """
    limit = loaded.config.solve.tolerances.residual
    lines: list[str] = []
    worst_force = 0.0
    worst_moment = 0.0
    failures = 0

    for block in loaded.run.solution.blocks:
        scale = _block_scale(block)
        for row in block.rows:
            force, moment = part_residuals(row)
            worst_force = max(worst_force, force)
            worst_moment = max(worst_moment, moment)
            if force > limit * max(scale, 1.0) or moment > limit * max(
                scale * _lever(row), 1.0
            ):
                failures += 1
                lines.append(
                    f"FAIL {block.part} [{row.case.label} {row.side_label}]: "
                    f"|sum F| = {force:.6g} N, |sum M| = {moment:.6g} N-mm"
                )

    lines.append(
        f"worst residual: |sum F| = {worst_force:.3e} N, "
        f"|sum M| = {worst_moment:.3e} N-mm over "
        f"{sum(len(block.rows) for block in loaded.run.solution.blocks)} part-rows"
    )
    return "\n".join(lines), failures == 0


def _block_scale(block: PartBlock) -> float:
    """Return the largest force magnitude in one block, for a relative limit."""
    return max(
        (float(np.max(np.abs(load.force))) for row in block.rows for load in row.loads),
        default=0.0,
    )


def _lever(row: PartCaseLoads) -> float:
    """Return the largest moment arm in one row, for a relative limit."""
    return max(
        (float(np.max(np.abs(load.position))) for load in row.loads),
        default=1.0,
    )


def _provenance(paths: ForcePaths) -> dict[str, str]:
    """Hash every input file so a result can be traced back to it."""
    return {
        name: f"{path} sha256={compute_file_hash(path)}"
        for name, path in (
            ("config", paths.config),
            ("front", paths.front),
            ("rear", paths.rear),
            ("cases", paths.cases),
        )
    }
