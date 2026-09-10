from importlib import import_module
from pathlib import Path
from types import ModuleType

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


def require_visualization() -> ModuleType:
    """
    Load the optional visualization API or exit with installation guidance.
    """
    try:
        import_module("matplotlib")
        return import_module("kinematics.cli.visualization.api")
    except ImportError as error:
        typer.echo(
            "Error: Visualization dependencies not installed.\n"
            'Install with: pip install "kinematics[cli,viz]"\n'
            f"Details: {error}",
            err=True,
        )
        raise typer.Exit(1) from error


@app.command()
def sweep(
    geometry: Path = typer.Option(..., exists=True, help="Path to geometry YAML"),
    sweep: Path = typer.Option(..., exists=True, help="Path to sweep YAML"),
    out: Path = typer.Option(..., help="Output path (.parquet or .csv)"),
    animation_out: Path | None = typer.Option(
        None, help="Optional animation output path (.mp4, .gif, etc.)"
    ),
):
    """
    Run a sweep from file and write results to Parquet or CSV format.

    Example:
        kinematics sweep --geometry=geo.yaml --sweep=sweep.yaml --out=out.parquet
        kinematics sweep --geometry=geo.yaml --sweep=sweep.yaml --out=out.csv
    """
    from kinematics.cli.commands.sweep import run_sweep_files

    run = run_sweep_files(geometry, sweep, out)
    if run.evaluated.diagnostics:
        typer.echo("Diagnostics:", err=True)
        for issue in run.evaluated.diagnostics:
            typer.echo(f"{issue.severity.upper()}: {issue.message}", err=True)

    typer.echo(f"wrote {out}")

    # Generate animation if requested.
    if animation_out:
        visualization = require_visualization()

        # Create animation.
        visualization.visualize_suspension_sweep(
            suspension=run.suspension,
            solution_states=run.evaluated.states,
            output_path=animation_out,
            fps=20,
            show_live=False,
        )

        typer.echo(f"Wrote animation: {animation_out}")


@app.command()
def forces(
    config: Path = typer.Option(
        Path("forces.yaml"), exists=True, help="Path to the force configuration YAML"
    ),
    front: Path | None = typer.Option(
        None, exists=True, help="Override the front geometry YAML"
    ),
    rear: Path | None = typer.Option(
        None, exists=True, help="Override the rear geometry YAML"
    ),
    cases: Path | None = typer.Option(
        None, exists=True, help="Override the load-case CSV"
    ),
    out: Path | None = typer.Option(None, help="Output path (.csv or .xlsx)"),
    mass: float | None = typer.Option(None, help="Override the vehicle mass in kg"),
    per_part_files: Path | None = typer.Option(
        None, help="Also write one CSV per part into this directory"
    ),
    describe_only: bool = typer.Option(
        False, "--describe", help="Print the structural model and stop"
    ),
    check_only: bool = typer.Option(
        False, "--check", help="Print per-part equilibrium residuals and stop"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate every input and stop"
    ),
):
    """
    Solve static suspension forces for every load case and write them per part.

    Front and rear are solved together because the load distribution is a
    whole-vehicle statement; the individual corner solves are independent.

    Example:
        kinematics forces --config=forces.yaml --out=forces.csv
        kinematics forces --config=forces.yaml --describe
    """
    from kinematics.cli.commands.forces import (
        check,
        describe,
        load_inputs,
        run_force_files,
    )

    if describe_only or check_only or dry_run:
        loaded = load_inputs(config, front, rear, cases, mass)
        _report_diagnostics(loaded.run.solution.diagnostics)
        if describe_only:
            typer.echo(describe(loaded))
        elif check_only:
            report, passed = check(loaded)
            typer.echo(report)
            if not passed:
                raise typer.Exit(1)
        else:
            typer.echo(
                f"configuration valid: {len(loaded.cases)} case(s), "
                f"{len(loaded.run.corners)} corner(s)"
            )
        return

    if out is None:
        typer.echo(
            "Error: --out is required unless --describe, --check, or "
            "--dry-run is given.",
            err=True,
        )
        raise typer.Exit(1)

    run = run_force_files(config, front, rear, cases, out, mass, per_part_files)
    _report_diagnostics(run.run.solution.diagnostics)
    typer.echo(f"wrote {out}")
    for path in run.per_part_paths:
        typer.echo(f"wrote {path}")


def _report_diagnostics(diagnostics: tuple[str, ...]) -> None:
    """Print solve warnings to stderr, so piped output stays clean."""
    if not diagnostics:
        return
    typer.echo("Diagnostics:", err=True)
    for issue in diagnostics:
        typer.secho(f"WARNING: {issue}", err=True, fg=typer.colors.YELLOW)


@app.command()
def visualize(
    geometry: Path = typer.Option(..., exists=True, help="Path to geometry YAML."),
    output: Path = typer.Option(
        ..., help="Output path for the plot image (.png, .jpg)."
    ),
):
    """
    Visualize a suspension geometry at its design condition.

    This command loads a single geometry file, calculates its initial state, and
    generates a debug plot. It also reports whether the wheel contact centres
    points lie on the reconstructed design road plane.

    Example:
    uv run kinematics visualize --geometry=tests/data/geometry.yaml --output=plot.png
    """
    from kinematics.cli.io.loaders import load_geometry

    visualization = require_visualization()
    suspension = load_geometry(geometry)

    typer.echo("Checking and visualizing suspension geometry...")
    result = visualization.visualize_geometry(
        suspension=suspension,
        output_path=output,
    )
    road_distances = ", ".join(
        f"{value:.3f}" for value in result.wheel_contact_centre_road_distance_mm
    )
    if result.wheel_contact_centres_on_road:
        typer.secho(
            "Geometry Check: OK. Wheel contact centres lie on the reconstructed "
            f"design road plane (distances = {road_distances} mm).",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            "Geometry Check: WARNING. Wheel contact centres do not lie on the "
            "reconstructed design road plane.",
            fg=typer.colors.RED,
        )
        typer.echo(f"Their signed distances from that plane are {road_distances} mm.")
    typer.secho(
        f"Visualization saved to: {result.output_path}",
        fg=typer.colors.GREEN,
    )


if __name__ == "__main__":
    app()
