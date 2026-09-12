"""File hashing for result provenance, with no output-format dependencies."""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_file_hash(path: str | Path) -> str:
    """
    Compute the SHA-256 of a file, for provenance tracking.

    Args:
        path: Path to the file to hash.

    Returns:
        Hexadecimal hash string, or an empty string if the file cannot be read.
    """
    try:
        with open(path, "rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except Exception:
        return ""
