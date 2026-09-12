"""CSV adapter for load-case files."""

from __future__ import annotations

import csv
from pathlib import Path

from kinematics.core.loads.cases import LoadCase

COLUMNS = ("bump", "brake", "corner")


def load_cases(path: Path) -> tuple[LoadCase, ...]:
    """
    Read a load-case CSV into validated cases.

    Lines beginning with ``#`` are comments and are skipped wherever they
    appear. The first non-comment row is the header and must name ``bump``,
    ``brake``, and ``corner`` in any order; any other column is an error rather
    than being silently ignored.

    Args:
        path: Path to the case file.

    Returns:
        The cases, in file order.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the header is wrong, a value is not a number, or a case
            is not physically solvable.
    """
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            rows = [
                row
                for row in csv.reader(handle)
                if row and not row[0].lstrip().startswith("#")
            ]
    except FileNotFoundError:
        raise FileNotFoundError(f"Case file not found: {path}")

    if not rows:
        raise ValueError(f"Case file has no rows: {path}")

    header = [cell.strip().lower() for cell in rows[0]]
    indices = {}
    for column in COLUMNS:
        if column not in header:
            raise ValueError(
                f"Case file {path} is missing the '{column}' column. Its header "
                f"must name {', '.join(COLUMNS)}."
            )
        indices[column] = header.index(column)

    extra = [cell for cell in header if cell and cell not in COLUMNS]
    if extra:
        raise ValueError(
            f"Case file {path} has unexpected column(s): {', '.join(extra)}. "
            f"Only {', '.join(COLUMNS)} are read."
        )

    cases: list[LoadCase] = []
    for number, row in enumerate(rows[1:], start=2):
        values = {}
        for column, index in indices.items():
            cell = row[index].strip() if index < len(row) else ""
            try:
                values[column] = float(cell)
            except ValueError:
                raise ValueError(
                    f"Case file {path}, data row {number}: '{column}' is "
                    f"{cell!r}, which is not a number."
                ) from None
        try:
            cases.append(LoadCase(**values))
        except ValueError as error:
            raise ValueError(f"Case file {path}, data row {number}: {error}") from error

    if not cases:
        raise ValueError(f"Case file {path} has a header but no cases.")
    return tuple(cases)
