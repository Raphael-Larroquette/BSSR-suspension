"""Module-level task functions for the scheduler tests (spawned workers import them)."""

import os


def flaky(payload: dict) -> dict:
    """Fail once per task (out of memory, or by killing the worker), then succeed."""
    marker = payload["marker"]
    if not os.path.exists(marker):
        open(marker, "w").close()
        if payload["mode"] == "die":
            os._exit(3)
        return {"status": "resource", "message": "MemoryError: test"}
    return {"status": "ok"}


def always_out_of_memory(payload: dict) -> dict:
    """Never succeeds."""
    return {"status": "resource", "message": "MemoryError: test"}
