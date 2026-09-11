"""
Force-solve output: one block per part, in the reference layout.

A part's block is the load set an FEA run applies to that one component. The
externally applied tyre force is included alongside the joint reactions, so
every block sums to zero and the file carries its own check.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from kinematics.core.enums import MomentReporting, OutputFrame
from kinematics.core.loads.cases import format_g
from kinematics.core.loads.results import WHEEL_LIFT, ForceSolution, PartBlock
from kinematics.core.primitives.point_ref import Side

CASE_COLUMNS = ("bump", "brake", "corner", "side")
# Each vector is written as its components followed by its resultant, so a
# joint reads left to right as x, y, z, magnitude.
FORCE_COMPONENTS = ("x", "y", "z", "mag")
MOMENT_COMPONENTS = ("mx", "my", "mz", "mmag")
FLAGS_COLUMN = "flags"

LOAD_TRANSFER_COLUMNS = (
    "bump",
    "brake",
    "corner",
    "wheel",
    "normal_load_N",
    "effective_mass_kg",
    "percent_of_case",
    "percent_of_static_weight",
    "transfer_from_baseline_N",
    "flags",
)

# Relative size below which a moment counts as zero rather than as a result.
MOMENT_EPSILON = 1e-6


@dataclass(frozen=True)
class ForceWriteOptions:
    """How the solved forces are written."""

    frame: OutputFrame = OutputFrame.VEHICLE
    moments: MomentReporting = MomentReporting.AUTO
    metadata: dict[str, str] | None = None


def write_forces(
    solution: ForceSolution,
    output_path: Path,
    options: ForceWriteOptions = ForceWriteOptions(),
) -> None:
    """
    Write a solved run to CSV or XLSX.

    Raises:
        ValueError: If the output extension is not supported.
    """
    suffix = output_path.suffix.lower()
    if suffix == ".csv":
        _write_csv(solution, output_path, options)
    elif suffix == ".xlsx":
        _write_xlsx(solution, output_path, options)
    else:
        raise ValueError(
            f"Unsupported force output format '{suffix}'. Use .csv or .xlsx."
        )


def write_per_part_files(
    solution: ForceSolution,
    directory: Path,
    options: ForceWriteOptions = ForceWriteOptions(),
) -> tuple[Path, ...]:
    """Write one flat CSV per part, for direct import into an FEA run."""
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for block in solution.blocks:
        path = directory / f"{_slug(block.part)}.csv"
        components = _components_for(block, options)
        header = [
            *CASE_COLUMNS,
            *(
                f"{column}_{component}"
                for column in block.columns
                for component in components
            ),
            FLAGS_COLUMN,
        ]
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(header)
            for row in _data_rows(block, components, options):
                writer.writerow(row)
        written.append(path)
    return tuple(written)


def _write_csv(
    solution: ForceSolution,
    output_path: Path,
    options: ForceWriteOptions,
) -> None:
    """Write the block layout to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as handle:
        for line in _header_lines(solution, options):
            handle.write(f"# {line}\n")
        handle.write("#\n")
        writer = csv.writer(handle, lineterminator="\n")
        for block in solution.blocks:
            for row in _block_rows(block, options):
                writer.writerow(row)
            writer.writerow([])


def _write_xlsx(
    solution: ForceSolution,
    output_path: Path,
    options: ForceWriteOptions,
) -> None:
    """Write the block layout to a worksheet."""
    try:
        from openpyxl import Workbook
    except ImportError as error:
        raise ValueError(
            "Writing .xlsx needs openpyxl, which is not installed. Install with "
            'pip install "kinematics[xlsx]", or write a .csv instead.'
        ) from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "forces"
    for line in _header_lines(solution, options):
        sheet.append([f"# {line}"])
    sheet.append([])
    for block in solution.blocks:
        for row in _block_rows(block, options):
            sheet.append(row)
        sheet.append([])
    workbook.save(output_path)


def _header_lines(
    solution: ForceSolution,
    options: ForceWriteOptions,
) -> list[str]:
    """Build the provenance and convention banner."""
    vehicle = solution.vehicle
    lines = [
        "kinematics forces, format 1",
        f"frame: {options.frame.value} (ISO 8855: X forward, Y left, Z up)",
        "units: N, N-mm | sign: force acting ON the named part AT that joint",
        f"mass: {vehicle.mass} kg | g: {vehicle.gravity} | "
        f"wheelbase: {vehicle.wheelbase} mm",
        f"worst condition number: {solution.max_condition:.3e}",
    ]
    for key, value in (options.metadata or {}).items():
        lines.append(f"{key}: {value}")
    lines.extend(f"WARNING: {issue}" for issue in solution.diagnostics)
    return lines


def _components_for(
    block: PartBlock,
    options: ForceWriteOptions,
) -> tuple[str, ...]:
    """Decide this block's per-joint component set."""
    if options.moments is MomentReporting.NEVER:
        return FORCE_COMPONENTS
    if options.moments is MomentReporting.ALWAYS:
        return FORCE_COMPONENTS + MOMENT_COMPONENTS
    return (
        FORCE_COMPONENTS + MOMENT_COMPONENTS
        if _carries_moment(block)
        else FORCE_COMPONENTS
    )


def _carries_moment(block: PartBlock) -> bool:
    """Whether any load in this block has a moment worth reporting."""
    scale = max(
        (float(np.max(np.abs(load.force))) for row in block.rows for load in row.loads),
        default=0.0,
    )
    limit = MOMENT_EPSILON * max(scale, 1.0)
    return any(
        load.moment is not None and float(np.max(np.abs(load.moment))) > limit
        for row in block.rows
        for load in row.loads
    )


def _block_rows(
    block: PartBlock,
    options: ForceWriteOptions,
) -> list[list[object]]:
    """Build one part block: its two header rows and its data rows."""
    components = _components_for(block, options)
    width = len(components)
    names: list[object] = ["Case", "", "", ""]
    units: list[object] = list(CASE_COLUMNS)
    for column in block.columns:
        names.extend([column, *([""] * (width - 1))])
        units.extend(components)
    names.append(FLAGS_COLUMN)
    units.append("")
    return [
        ["PART:", block.part],
        names,
        units,
        *_data_rows(block, components, options),
    ]


def _data_rows(
    block: PartBlock,
    components: tuple[str, ...],
    options: ForceWriteOptions,
) -> list[list[object]]:
    """Build one row per case and side, in the block's fixed column order."""
    rows: list[list[object]] = []
    for row in block.rows:
        by_name = {load.column_name: load for load in row.loads}
        mirror = options.frame is OutputFrame.PART and row.side is Side.RIGHT
        cells: list[object] = [
            format_g(row.case.bump),
            format_g(row.case.brake),
            format_g(row.case.corner),
            row.side_label,
        ]
        for column in block.columns:
            load = by_name.get(column)
            if load is None:
                cells.extend([None] * len(components))
                continue
            cells.extend(_vector_cells(_mirrored(load.force, mirror)))
            if len(components) > len(FORCE_COMPONENTS):
                moment = load.moment
                if moment is None:
                    cells.extend([None] * len(MOMENT_COMPONENTS))
                else:
                    cells.extend(_vector_cells(_mirrored_moment(moment, mirror)))
        cells.append(" ".join(row.flags))
        rows.append(cells)
    return rows


def _vector_cells(vector: np.ndarray) -> list[float]:
    """Return one vector's components followed by its resultant magnitude.

    The magnitude is written rather than left to a spreadsheet formula so that
    the number an FEA run is sized against is the same number in every copy of
    the file, and so sorting a column by worst case is a sort rather than a
    recalculation.
    """
    return [
        *(round(float(value), 3) for value in vector),
        round(float(np.linalg.norm(vector)), 3),
    ]


def write_load_transfer(
    solution: ForceSolution,
    output_path: Path,
    options: ForceWriteOptions = ForceWriteOptions(),
) -> None:
    """
    Write the per-wheel vertical load for every case.

    Two share columns rather than one, because "percent of the vehicle" is
    ambiguous the moment ``bump`` is not 1: ``percent_of_case`` is the wheel's
    fraction of that case's own total and sums to 100 across the wheels, while
    ``percent_of_static_weight`` is its fraction of ``m g`` and sums to
    100 x bump.
    """
    transfer = solution.load_transfer
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as handle:
        for line in _header_lines(solution, options):
            handle.write(f"# {line}\n")
        handle.write(
            "# normal_load_N is the vertical force the road applies to that tyre; "
            "effective_mass_kg is that force divided by g\n"
        )
        handle.write(
            "# transfer_from_baseline_N is measured against the same case with "
            "brake and corner set to zero, so a pure bump case reads zero\n"
        )
        handle.write("#\n")
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(LOAD_TRANSFER_COLUMNS)
        for share in transfer.shares:
            writer.writerow(
                [
                    format_g(share.case.bump),
                    format_g(share.case.brake),
                    format_g(share.case.corner),
                    share.wheel,
                    round(share.normal, 3),
                    round(share.effective_mass, 4),
                    round(100.0 * share.share_of_case, 4),
                    round(100.0 * share.share_of_weight, 4),
                    round(share.transfer, 3),
                    WHEEL_LIFT if share.lifted else "",
                ]
            )


def _mirrored(force: np.ndarray, mirror: bool) -> np.ndarray:
    """Reflect a force through the vehicle centre plane when asked."""
    return force * np.array([1.0, -1.0, 1.0]) if mirror else force


def _mirrored_moment(moment: np.ndarray, mirror: bool) -> np.ndarray:
    """Reflect a moment through the vehicle centre plane when asked.

    A moment is a pseudovector, so reflecting in the ``y = 0`` plane negates
    the components a force does not, and preserves the one it does.
    """
    return moment * np.array([-1.0, 1.0, -1.0]) if mirror else moment


def _slug(name: str) -> str:
    """Normalize a part name into a filename stem."""
    return "".join(
        character if character.isalnum() else "_" for character in name.strip().lower()
    ).strip("_")
