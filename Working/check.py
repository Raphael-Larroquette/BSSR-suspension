#!/usr/bin/env python3
"""
Check that a model folder is complete and builds, without solving any sweep.

    uv run python Working/check.py                  every model in Working/models/
    uv run python Working/check.py aurora CV1       these models (name or path)

A model must hold every file listed in MODEL_FILES, each geometry must build, and
its forces.yaml must load and solve against Working/cases.csv. Exits 1 on any
problem. `run_all.py --dry-run` runs the same check on every model it plans.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # Working/
MODELS_DIR = HERE / "models"
CASES_FILE = HERE / "cases.csv"

# What a model folder must hold to run its sweeps, its forces, and to serve
# as an optimizer template.
MODEL_FILES = ("front.yaml", "rear.yaml", "forces.yaml")
GEOMETRY_FILES = ("front.yaml", "rear.yaml")


def check_model(folder: Path) -> list[str]:
    """Return every problem with one model folder; empty means it is good."""
    missing = [name for name in MODEL_FILES if not (folder / name).is_file()]
    problems = [f"missing {name}" for name in missing]

    import yaml
    from kinematics.core.input import build_suspension

    for name in GEOMETRY_FILES:
        if name in missing:
            continue
        try:
            build_suspension(yaml.safe_load((folder / name).read_text()))
        except Exception as error:  # noqa: BLE001 - report, never raise
            problems.append(f"{name} does not build: {error}")

    if "forces.yaml" not in missing and not any(
        p.startswith(GEOMETRY_FILES) for p in problems
    ):
        from kinematics.cli.commands.forces import load_inputs
        from kinematics.cli.io.forces_loader import load_forces_config

        config = folder / "forces.yaml"
        try:
            own_cases = load_forces_config(config).cases is not None
            load_inputs(config, cases=None if own_cases else CASES_FILE)
        except Exception as error:  # noqa: BLE001
            problems.append(f"forces.yaml does not solve: {error}")
    return problems


def resolve(value: str) -> Path:
    """A model given as a path, or as a folder name under Working/models/."""
    for candidate in (Path(value).expanduser(), MODELS_DIR / value):
        if candidate.is_dir():
            return candidate.resolve()
    sys.exit(f"model not found: {value}")


def is_model(folder: Path) -> bool:
    """A folder holding any geometry file (a batch folder holds none)."""
    return any((folder / name).is_file() for name in GEOMETRY_FILES)


def main() -> None:
    folders = (
        [resolve(v) for v in sys.argv[1:]]
        if len(sys.argv) > 1
        else sorted(p for p in MODELS_DIR.iterdir() if p.is_dir() and is_model(p))
    )
    failed = 0
    for folder in folders:
        problems = check_model(folder)
        failed += bool(problems)
        print(f"{'ok    ' if not problems else 'FAILED'}  {folder.name}")
        for problem in problems:
            print(f"        {problem}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
