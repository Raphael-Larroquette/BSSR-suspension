"""
Turn an optimizer run's Pareto front into runnable model folders.

    uv run python Working/export_pareto.py                        the latest run
    uv run python Working/export_pareto.py opt_2026-10-02_1430    a specific run

An optimizer run is a folder Working/models/opt_<timestamp>/ holding
opt_<timestamp>.csv (written by `uv run python Working/optimizer.py`). For each
row of that CSV this writes <run>/pareto1/, pareto2/, ...: a copy of the template
model's YAMLs (front, rear, forces) with the optimised hardpoints patched in.
Existing pareto folders in that run are replaced. Then run them all with:

    uv run python Working/run_all.py --batch <run> --sets front --only 01,02 --no-forces

The pareto folders are git-ignored; only the CSV is tracked, and this script
rebuilds them from it on any machine.
"""

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent  # Working/
MODELS_DIR = HERE / "models"
RUN_PREFIX = "opt_"

# Results and logs in the template model are not copied into a candidate.
NOT_COPIED = ("sweep_outputs", "report", "forces", "outputs", "run.log", "__pycache__")


def find_runs() -> list[Path]:
    """Every optimizer run folder that holds its CSV, oldest first."""
    return sorted(
        p for p in MODELS_DIR.glob(f"{RUN_PREFIX}*")
        if p.is_dir() and (p / f"{p.name}.csv").is_file()
    )


def resolve_run(value: str | None) -> Path:
    """The run named on the command line, or the latest one."""
    runs = find_runs()
    if value is None:
        if not runs:
            sys.exit(f"no optimizer runs in {MODELS_DIR} (folders named "
                     f"{RUN_PREFIX}<timestamp> holding <folder name>.csv). "
                     "Run the optimizer first: uv run python Working/optimizer.py")
        return runs[-1]
    for candidate in (Path(value).expanduser(), MODELS_DIR / value):
        if candidate.is_dir():
            if not (candidate / f"{candidate.name}.csv").is_file():
                sys.exit(f"{candidate} holds no {candidate.name}.csv, so it is not "
                         "an optimizer run.")
            return candidate.resolve()
    sys.exit(f"optimizer run not found: {value}\nRuns available: "
             f"{', '.join(r.name for r in runs) or '(none)'}")


def from_csv(rows: list[dict], column: str, override: str | None,
             flag: str) -> str:
    """One provenance value the optimizer wrote on every row, or the CLI's.

    The CSV says which template folder and axle its hardpoints belong to, so
    exporting never depends on what any optimizer script says today. A CSV
    from before those columns existed needs the value on the command line.
    """
    if override is not None:
        return override
    values = {row.get(column) for row in rows} - {None, ""}
    if len(values) > 1:
        sys.exit(f"the CSV names several values for {column}: "
                 f"{', '.join(sorted(values))}")
    if not values:
        sys.exit(f"the CSV has no `{column}` column (it predates it). "
                 f"Say which with {flag}, e.g. {flag} "
                 + ("models/aurora" if column == "template" else "front"))
    return values.pop()


def resolve_template(value: str) -> Path:
    """A template folder: absolute, or relative to Working/."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else (HERE / path).resolve()


def hardpoints_from_row(row: dict) -> dict[str, dict[str, float]]:
    """`lower_wishbone_outboard.y` style columns -> {point: {axis: value}}."""
    points: dict[str, dict[str, float]] = {}
    for column, text in row.items():
        if "." not in column or column.endswith("_frac"):
            continue
        try:
            value = round(float(text), 3)
        except (TypeError, ValueError):
            continue
        point, axis = column.split(".", 1)
        points.setdefault(point, {})[axis] = value
    return points


# `  name: {x: 1, y: 2, z: 3}  # comment` - one hardpoint per line.
POINT_LINE = re.compile(r"^(\s*)([a-zA-Z0-9_]+):\s*\{(.*)\}(.*)$")


def patch_geometry(text: str, points: dict, title: str) -> tuple[str, int]:
    """Rewrite the matching hardpoint lines in place, keeping comments and layout."""
    lines = text.split("\n")
    patched = 0
    for index, line in enumerate(lines):
        match = POINT_LINE.match(line)
        if match and match.group(2) in points:
            indent, name, inner, trailer = match.groups()
            try:
                coords = yaml.safe_load("{" + inner + "}")
            except yaml.YAMLError:
                continue
            coords.update(points[name])
            body = ", ".join(f"{k}: {v}" for k, v in coords.items())
            lines[index] = f"{indent}{name}: {{{body}}}{trailer}"
            patched += 1
        elif line.startswith("name: "):
            lines[index] = f'name: "{title}"'
    return "\n".join(lines), patched


def main() -> None:
    """Export one pareto<N>/ model folder per row of the run's CSV."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", nargs="?", default=None,
                        help="optimizer run folder: a name under Working/models/ "
                        "or a path (default: the latest run)")
    parser.add_argument("--template", default=None,
                        help="template model folder, relative to Working/; only "
                        "for a CSV without a `template` column")
    parser.add_argument("--axle", default=None,
                        help="front or rear; only for a CSV without an `axle` column")
    args = parser.parse_args()

    run = resolve_run(args.run)
    csv_path = run / f"{run.name}.csv"
    with open(csv_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        sys.exit(f"{csv_path} has no rows.")

    # A pre-October CSV recorded the template by car name only.
    legacy_car = {row.get("template_car") for row in rows} - {None, ""}
    if args.template is None and len(legacy_car) == 1:
        args.template = f"models/{legacy_car.pop()}"
    template = resolve_template(
        from_csv(rows, "template", args.template, "--template"))
    if not template.is_dir():
        sys.exit(f"template model not found: {template}")
    geometry_name = f"{from_csv(rows, 'axle', args.axle, '--axle')}.yaml"

    print(f"run      : {run}")
    print(f"template : {template}")
    print(f"points   : {len(rows)}\n")

    for stale in run.glob("pareto*"):
        if stale.is_dir():
            shutil.rmtree(stale)

    for number, row in enumerate(rows, start=1):
        target = run / f"pareto{number}"
        shutil.copytree(template, target, ignore=shutil.ignore_patterns(*NOT_COPIED))
        geometry = target / geometry_name
        text, patched = patch_geometry(
            geometry.read_text(encoding="utf-8"),
            hardpoints_from_row(row),
            f"{run.name} pareto{number}",
        )
        geometry.write_text(text, encoding="utf-8")
        print(f"   pareto{number:<4} {patched} hardpoints patched")

    print(f"\nDone. Run every candidate with:\n"
          f"   uv run python Working/run_all.py --batch {run.name} "
          "--sets front --only 01,02 --no-forces")


if __name__ == "__main__":
    main()
