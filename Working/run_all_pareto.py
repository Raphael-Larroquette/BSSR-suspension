#!/usr/bin/env python3
"""
Moved. Running every Pareto candidate is now a flag on the one entry point.

This file is a signpost for stale commands and muscle memory; delete it once
nobody is reaching for it.
"""

import sys

MESSAGE = """\
Working/run_all_pareto.py no longer exists as a command.

An optimizer run now lives in its own folder, Working/models/opt_<timestamp>/,
and every candidate in it runs with one command:

    uv run python Working/optimizer.py        -> opt_<timestamp>/opt_<timestamp>.csv
    uv run python Working/export_pareto.py    -> pareto1, pareto2, ... in that folder
    uv run python Working/run_all.py --batch opt_<timestamp> --sets front
                                     --only 01,02 --no-forces

--batch runs several candidates at once, renders each animation on several
processes, and writes each candidate's console output to <candidate>/run.log.
See README.md.\
"""

if __name__ == "__main__":
    sys.exit(MESSAGE)
