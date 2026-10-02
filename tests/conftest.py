from pathlib import Path

import pytest


@pytest.fixture
def test_data_dir() -> Path:
    return Path(__file__).parent / "data"


@pytest.fixture
def double_wishbone_geometry_file(test_data_dir: Path) -> Path:
    return test_data_dir / "geometry.yaml"


@pytest.fixture
def working_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "Working"


@pytest.fixture
def aurora_dir(working_dir: Path) -> Path:
    # The golden values in these tests were generated from this geometry (the
    # original Aurora model, renamed aurora_evo when the recreated Aurora took
    # models/aurora). Pinned, so editing a working model never breaks a test.
    return working_dir / "models" / "aurora_evo"


@pytest.fixture
def aurora_forces_dir(working_dir: Path) -> Path:
    return working_dir / "models" / "aurora_evo"
