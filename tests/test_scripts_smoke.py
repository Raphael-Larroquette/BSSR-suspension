"""Smoke tests for repository-level helper scripts."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

matplotlib = pytest.importorskip(
    "matplotlib",
    reason="visualization smoke tests require the optional viz extra",
)
matplotlib.use("Agg")

REPO_ROOT = Path(__file__).resolve().parents[1]
PLOT_BUMP_SWEEP = REPO_ROOT / "scripts" / "plot_bump_sweep.py"


def _load_script(path: Path) -> Any:
    """Import a standalone script by file path."""
    name = f"_script_smoke_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_plot_bump_sweep_imports() -> None:
    module = _load_script(PLOT_BUMP_SWEEP)
    assert callable(module.main)


@pytest.mark.manual
def test_plot_bump_sweep_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run the full bump-sweep script, including its MP4 animation."""
    if shutil.which("ffmpeg") is None:
        # pytest wraps skip() so its stub drops the reason parameter from view.
        pytest.skip("ffmpeg not available")  # ty: ignore[too-many-positional-arguments]

    module = _load_script(PLOT_BUMP_SWEEP)
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path)
    module.main()

    assert (tmp_path / "dashboard.png").exists()
    assert (tmp_path / "bump_sweep.mp4").exists()
