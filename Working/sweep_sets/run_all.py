#!/usr/bin/env python3
"""
Moved. There is now one entry point for everything under Working/.

This file is a signpost for stale commands, notes and muscle memory. The
solving logic is unchanged and lives in `runner.py` beside it, which
`Working/run_all.py` imports. Delete this stub once nobody is reaching for the
old path.
"""

import sys

MESSAGE = """\
Working/sweep_sets/run_all.py no longer exists as a command.

Everything under Working/ runs from ONE entry point:

    uv run python Working/run_all.py                  every sweep set, then forces

Translating the old commands:

    OLD  ... sweep_sets/run_all.py
    NEW  uv run python Working/run_all.py --sets front

    OLD  ... sweep_sets/run_all.py --config <path>/rear/run.yaml
    NEW  uv run python Working/run_all.py --sets rear
     or  uv run python Working/run_all.py --config <path>/rear/run.yaml

    OLD  ... sweep_sets/run_all.py --report-only --only 01
    NEW  uv run python Working/run_all.py --report-only --only 01 --no-forces

Every flag the old script took still works, spelt the same way. The force
solve now runs too unless you pass --no-forces.

The solving code moved to runner.py in this folder; it is a library, not a
command. See ../README.md.\
"""

if __name__ == "__main__":
    sys.exit(MESSAGE)
