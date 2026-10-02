"""Model-folder layout, batch runs, Pareto export, and GIF frame rendering."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKING = REPO_ROOT / "Working"


def _load(path: Path) -> Any:
    name = f"_working_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("car", ["aurora", "aurora_evo"])
def test_each_aurora_model_is_self_contained(car: str) -> None:
    folder = WORKING / "models" / car
    for name in ("front.yaml", "rear.yaml", "forces.yaml", "cases.csv"):
        assert (folder / name).is_file(), name


def test_sweep_sets_default_to_a_model_that_exists() -> None:
    run_all = _load(WORKING / "run_all.py")
    for config in run_all.discover_sweep_sets():
        assert run_all.default_geometry(config).is_file(), config


def test_batch_strips_only_its_own_flags() -> None:
    run_all = _load(WORKING / "run_all.py")
    argv = ["--batch", "opt_x", "--sets", "front", "--parallel=3",
            "--gif-workers", "4", "--only", "01,02", "--no-forces"]
    assert run_all.forwarded_args(argv) == [
        "--sets", "front", "--only", "01,02", "--no-forces"]


def test_batch_never_starts_more_models_than_it_has() -> None:
    run_all = _load(WORKING / "run_all.py")
    parallel, workers = run_all.batch_sizes(2, 16, None)
    assert parallel == 2 and workers >= 1


def test_batch_discovers_models_in_natural_order(tmp_path: Path) -> None:
    run_all = _load(WORKING / "run_all.py")
    for n in (10, 2, 1):
        (tmp_path / f"pareto{n}").mkdir()
        (tmp_path / f"pareto{n}" / "front.yaml").write_text("x")
    (tmp_path / "not_a_model").mkdir()
    names = [p.name for p in run_all.discover_batch(tmp_path)]
    assert names == ["pareto1", "pareto2", "pareto10"]


def test_export_patches_hardpoints_and_keeps_comments() -> None:
    export = _load(WORKING / "export_pareto.py")
    text = (
        'name: "Aurora"\n'
        "    lower_wishbone_outboard: {x: 1, y: 2, z: 3}   # LBJ\n"
        "    upper_wishbone_outboard: {x: 4, y: 5, z: 6}\n"
    )
    points = export.hardpoints_from_row(
        {"lower_wishbone_outboard.y": "20.12345", "strut_bottom.u_frac": "0.5",
         "fvsa_length": "1000", "template_car": "aurora"}
    )
    patched, count = export.patch_geometry(text, points, "run pareto1")
    assert count == 1
    assert "lower_wishbone_outboard: {x: 1, y: 20.123, z: 3}   # LBJ" in patched
    assert "upper_wishbone_outboard: {x: 4, y: 5, z: 6}" in patched
    assert patched.startswith('name: "run pareto1"')


def test_generated_results_are_git_ignored() -> None:
    if subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse"],
                      capture_output=True).returncode != 0:
        pytest.skip("not a git checkout")
    cases = {
        "Working/models/aurora/sweep_outputs/front/02_roll.gif": True,
        "Working/models/aurora/report/front/report.md": True,
        "Working/models/aurora/forces/forces.csv": True,
        "Working/models/aurora/forces.yaml": False,
        "Working/models/opt_2026-10-02_1430/opt_2026-10-02_1430.csv": False,
        "Working/models/opt_2026-10-02_1430/pareto1/front.yaml": True,
        "Working/models/opt_2026-10-02_1430/pareto1/run.log": True,
    }
    for path, ignored in cases.items():
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", "--no-index", path])
        assert (result.returncode == 0) is ignored, path


def test_parallel_gif_frames_match_serial(
    double_wishbone_geometry_file: Path, test_data_dir: Path
) -> None:
    pytest.importorskip("matplotlib")
    from PIL import ImageChops

    from kinematics.cli.io.loaders import load_geometry
    from kinematics.cli.io.sweep_loader import load_sweep
    from kinematics.cli.visualization.animation import render_gif_frames
    from kinematics.cli.visualization.main import build_render_model
    from kinematics.core.sweep import solve_evaluated_sweep

    suspension = load_geometry(double_wishbone_geometry_file)
    sweep = load_sweep(test_data_dir / "sweep.yaml", suspension)
    states = solve_evaluated_sweep(suspension, sweep).states[:3]
    model = build_render_model(suspension)
    positions = [model.positions(state) for state in states]
    initial = model.positions(suspension.initial_state())

    def render(workers: int) -> list:
        return render_gif_frames(
            positions, initial, model.visualizer, dpi=20, workers=workers)

    serial, parallel = render(1), render(2)
    assert len(serial) == len(parallel) == 3
    for a, b in zip(serial, parallel):
        assert a.mode == "P"
        difference = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
        assert difference.getbbox() is None
