"""YAML adapter for validated force-solve configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from kinematics.core.schema.loads import ForcesConfig


def load_forces_config(path: Path) -> ForcesConfig:
    """
    Load and validate a force-solve configuration file.

    Args:
        path: Path to ``forces.yaml``.

    Returns:
        The validated configuration.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a mapping, or any key is missing,
            misspelt, or invalid. The message names every offending key.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data: Any = yaml.safe_load(handle)
    except FileNotFoundError:
        raise FileNotFoundError(f"Force configuration file not found: {path}")
    except yaml.YAMLError as error:
        raise ValueError(f"Error parsing force configuration: {error}") from error

    if data is None:
        raise ValueError(f"Force configuration file is empty: {path}")
    if not isinstance(data, dict):
        raise ValueError(f"Force configuration must be a YAML mapping: {path}")

    try:
        return ForcesConfig.model_validate(data)
    except ValidationError as error:
        raise ValueError(f"Invalid force configuration {path}:\n{_render(error)}")


def _render(error: ValidationError) -> str:
    """Render a validation failure as one named problem per line."""
    lines: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"]) or "<root>"
        message = item["msg"]
        if item["type"] == "missing":
            message = "required key is missing"
        elif item["type"] == "extra_forbidden":
            message = "unknown key"
        lines.append(f"  {location}: {message}")
    return "\n".join(lines)
