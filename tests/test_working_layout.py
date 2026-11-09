"""Model-folder layout, the batch scheduler, Pareto export, and animations."""

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
    for name in ("front.yaml", "rear.yaml", "forces.yaml"):
        assert (folder / name).is_file(), name
    assert (WORKING / "cases.csv").is_file()


@pytest.mark.parametrize("car", ["aurora", "aurora_evo"])
def test_model_check_passes_a_complete_model(car: str) -> None:
    check = _load(WORKING / "check.py")
    assert check.check_model(WORKING / "models" / car) == []


def test_model_check_names_every_missing_file(tmp_path: Path) -> None:
    check = _load(WORKING / "check.py")
    source = WORKING / "models" / "aurora"
    (tmp_path / "front.yaml").write_text((source / "front.yaml").read_text())
    problems = check.check_model(tmp_path)
    assert problems == ["missing rear.yaml", "missing forces.yaml"]


def test_dry_run_fails_on_an_incomplete_model(tmp_path: Path, monkeypatch) -> None:
    run_all = _load(WORKING / "run_all.py")
    source = WORKING / "models" / "aurora"
    for name in ("front.yaml", "rear.yaml"):
        (tmp_path / name).write_text((source / name).read_text())
    monkeypatch.setattr(
        sys, "argv", ["run_all.py", "--model", str(tmp_path), "--dry-run"]
    )
    with pytest.raises(SystemExit) as exited:
        run_all.main()
    assert exited.value.code == 1


def _working_force_configs() -> list[Path]:
    return sorted((WORKING / "models").glob("*/forces.yaml"))


@pytest.mark.parametrize(
    "config", _working_force_configs(), ids=lambda p: p.parent.name
)
def test_every_working_force_config_solves(config: Path) -> None:
    """Validate and solve, asserting nothing about values the team tunes."""
    pytest.importorskip("yaml")
    from kinematics.cli.commands.forces import load_inputs

    loaded = load_inputs(config, cases=WORKING / "cases.csv")
    assert loaded.cases and loaded.run.corners


def test_a_config_without_cases_needs_them_passed(tmp_path: Path) -> None:
    from kinematics.cli.commands.forces import resolve_paths
    from kinematics.cli.io.forces_loader import load_forces_config

    config_path = WORKING / "models" / "aurora" / "forces.yaml"
    config = load_forces_config(config_path)
    assert config.cases is None
    with pytest.raises(ValueError, match="names no load cases"):
        resolve_paths(config, config_path)


def test_sweep_sets_default_to_a_model_that_exists() -> None:
    run_all = _load(WORKING / "run_all.py")
    for config in run_all.discover_sweep_sets():
        assert run_all.default_geometry(config).is_file(), config


def test_removed_flags_name_their_replacement(monkeypatch, capsys) -> None:
    run_all = _load(WORKING / "run_all.py")
    monkeypatch.setattr(sys, "argv", ["run_all.py", "--parallel", "4"])
    with pytest.raises(SystemExit):
        run_all.main()
    assert "--workers" in capsys.readouterr().err


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
        {
            "lower_wishbone_outboard.y": "20.12345",
            "strut_bottom.u_frac": "0.5",
            "fvsa_length": "1000",
            "template_car": "aurora",
        }
    )
    patched, count = export.patch_geometry(text, points, "run pareto1")
    assert count == 1
    assert "lower_wishbone_outboard: {x: 1, y: 20.123, z: 3}   # LBJ" in patched
    assert "upper_wishbone_outboard: {x: 4, y: 5, z: 6}" in patched
    assert patched.startswith('name: "run pareto1"')


def test_generated_results_are_git_ignored() -> None:
    if (
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse"], capture_output=True
        ).returncode
        != 0
    ):
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
            ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", "--no-index", path]
        )
        assert (result.returncode == 0) is ignored, path


# --------------------------------------------------------------------------
# The scheduler: pool sizing, retries, recovery
# --------------------------------------------------------------------------
def _scheduler() -> Any:
    if str(WORKING / "sweep_sets") not in sys.path:
        sys.path.insert(0, str(WORKING / "sweep_sets"))
    import scheduler

    return scheduler


def test_pool_size_is_the_tightest_of_cores_memory_tasks_and_cap() -> None:
    scheduler = _scheduler()
    machine = scheduler.Machine(
        physical_cores=64,
        logical_cores=128,
        usable_cores=64,
        ram_mb=128 * 1024,
        available_mb=40 * 1024,
        memory_kind="commit",
    )
    # 40 GB available, 12.8 GB reserve -> 27.2 GB / 1 GB per worker = 27.
    assert scheduler.plan_workers(500, 1024, machine) == (27, "memory")
    assert scheduler.plan_workers(5, 1024, machine) == (5, "tasks")
    assert scheduler.plan_workers(500, 1024, machine, cap=8) == (8, "--workers")
    roomy = scheduler.Machine(64, 128, 64, 128 * 1024, 120 * 1024, "commit")
    workers, reason = scheduler.plan_workers(500, 512, roomy)
    assert reason in ("cores", "Windows pool limit") and workers <= 64


@pytest.mark.parametrize("mode", ["resource", "die"])
def test_memory_failures_and_dead_workers_are_retried(
    mode: str, tmp_path: Path
) -> None:
    scheduler = _scheduler()
    from tests import _pool_tasks

    tasks = [
        scheduler.Task(
            key=str(i), payload={"marker": str(tmp_path / str(i)), "mode": mode}
        )
        for i in range(3)
    ]
    results, report = scheduler.run_phase(
        "test", tasks, _pool_tasks.flaky, worker_mb=1, cap=2, log=lambda _m: None
    )
    assert [r["status"] for r in results] == ["ok"] * 3
    assert report.retries >= 3
    if mode == "die":
        assert report.rebuilds >= 1


def test_a_task_that_keeps_running_out_of_memory_is_reported(tmp_path: Path) -> None:
    scheduler = _scheduler()
    from tests import _pool_tasks

    tasks = [scheduler.Task(key="x", payload={"identity": {"sweep": "s"}})]
    results, _ = scheduler.run_phase(
        "test",
        tasks,
        _pool_tasks.always_out_of_memory,
        worker_mb=1,
        cap=1,
        log=lambda _m: None,
    )
    assert results[0]["status"] == "resource"
    assert results[0]["attempts"] == scheduler.MAX_RETRIES + 1
    assert results[0]["sweep"] == "s"


# --------------------------------------------------------------------------
# Tasks: what a failed sweep reports
# --------------------------------------------------------------------------
def test_a_lockout_is_reported_with_the_step_and_pose(tmp_path: Path) -> None:
    pytest.importorskip("yaml")
    _scheduler()
    import tasks

    sweep = tmp_path / "lock.yaml"
    sweep.write_text(
        "version: 1\nsteps: 6\ntargets:\n"
        "- {type: point, point: wheel_center, side: left, direction: {axis: z},"
        " mode: relative, start: 0, stop: 0}\n"
        "- {type: point, point: wheel_center, side: right, direction: {axis: z},"
        " mode: relative, start: 0, stop: 0}\n"
        "- {type: actuator_position, actuator: rack, direction: {axis: y},"
        " mode: relative, start: 0, stop: 400}\n"
    )
    result = tasks.execute(
        {
            "kind": "solve",
            "identity": {"sweep": "lock"},
            "geometry": str(WORKING / "models" / "aurora" / "front.yaml"),
            "sweep": str(sweep),
            "csv": str(tmp_path / "lock.csv"),
            "frames": "",
            "log": str(tmp_path / "lock.log"),
        }
    )
    assert result["status"] == "lockout", result
    assert result["n_steps"] == 6
    assert 1 < result["fail_step"] <= 6
    assert result["at"]["rack"] > result["last_good"]["rack"]
    assert not (tmp_path / "lock.csv").exists()


def test_resource_errors_are_told_apart_from_design_failures() -> None:
    _scheduler()
    import tasks

    paging = ImportError(
        "DLL load failed while importing _flapack: The paging "
        "file is too small for this operation to complete."
    )
    assert tasks.is_resource_error(paging)
    assert tasks.is_resource_error(MemoryError())
    assert not tasks.is_resource_error(
        RuntimeError("Solver failed to converge for targets: [...]")
    )


# --------------------------------------------------------------------------
# Animations
# --------------------------------------------------------------------------
@pytest.mark.parametrize("suffix", [".gif", ".mp4"])
def test_animation_streams_to_ffmpeg(
    suffix: str,
    double_wishbone_geometry_file: Path,
    test_data_dir: Path,
    tmp_path: Path,
) -> None:
    pytest.importorskip("matplotlib")
    from kinematics.cli.io.loaders import load_geometry
    from kinematics.cli.io.sweep_loader import load_sweep
    from kinematics.cli.visualization.main import build_render_model
    from kinematics.cli.visualization.render2d import (
        ffmpeg_executable,
        write_animation,
    )
    from kinematics.core.sweep import solve_evaluated_sweep

    try:
        ffmpeg_executable()
    except RuntimeError:
        pytest.skip("no ffmpeg")
    suspension = load_geometry(double_wishbone_geometry_file)
    sweep = load_sweep(test_data_dir / "sweep.yaml", suspension)
    states = solve_evaluated_sweep(suspension, sweep).states[:4]
    model = build_render_model(suspension)
    out = write_animation(
        [model.positions(s) for s in states],
        model.positions(suspension.initial_state()),
        model.visualizer,
        tmp_path / f"anim{suffix}",
        fps=10,
        dpi=30,
    )
    assert out.is_file() and out.stat().st_size > 1000
    assert not list(tmp_path.glob("*.partial*"))
