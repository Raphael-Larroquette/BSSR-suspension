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
def aurora_dir(test_data_dir: Path) -> Path:
    # A frozen copy of the original Aurora model, with its own forces.yaml and
    # cases.csv. The golden values in the tests were generated from it, so it
    # lives with the tests: editing a model in Working/ never breaks a test.
    return test_data_dir / "aurora"


@pytest.fixture
def aurora_forces_dir(aurora_dir: Path) -> Path:
    return aurora_dir
