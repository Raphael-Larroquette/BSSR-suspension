#!/usr/bin/env python3
"""
Run the full sweep set and build the report. Cross-platform (works in
PowerShell, cmd, bash) and independent of your current working directory.

Layout it assumes:
    models/
      aurora/            <- geometry, outputs, report
        front.yaml
        outputs/
        report/
      Sweep_Set/         <- this file
        sweeps/
        susreport.py

Usage:
    uv run python models/Sweep_Set/run_all.py
    uv run python models/Sweep_Set/run_all.py --geometry models/aurora/rear.yaml
    uv run python models/Sweep_Set/run_all.py --model rear     # -> models/rear/
    uv run python models/Sweep_Set/run_all.py --no-animation
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # models/Sweep_Set
MODELS = HERE.parent                            # models
SWEEPS = HERE / "sweeps"
SUSREPORT = HERE / "susreport.py"


def run(cmd: list[str]) -> None:
    print("   $", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="aurora",
                    help="folder under models/ holding the geometry (default: aurora)")
    ap.add_argument("--geometry", type=Path, default=None,
                    help="explicit path to the geometry yaml, overrides --model")
    ap.add_argument("--side", default="left", choices=("left", "right"))
    ap.add_argument("--no-animation", action="store_true")
    args = ap.parse_args()

    model_dir = MODELS / args.model
    geometry = args.geometry.resolve() if args.geometry else model_dir / "front.yaml"
    outputs = model_dir / "outputs"
    report = model_dir / "report"

    if not geometry.is_file():
        sys.exit(f"geometry not found: {geometry}")
    outputs.mkdir(parents=True, exist_ok=True)

    sweeps = sorted(SWEEPS.glob("*.yaml"))
    if not sweeps:
        sys.exit(f"no sweeps in {SWEEPS}")

    print(f"geometry : {geometry}")
    print(f"sweeps   : {SWEEPS}  ({len(sweeps)} files)")
    print(f"outputs  : {outputs}\n")

    for sweep in sweeps:
        print(f"-> {sweep.stem}")
        run(["uv", "run", "kinematics", "sweep",
             "--geometry", str(geometry),
             "--sweep", str(sweep),
             "--out", str(outputs / f"{sweep.stem}.csv")])

    if not args.no_animation:
        first = SWEEPS / "01_bump_parallel.yaml"
        if first.is_file():
            print("\n-> animation (01_bump_parallel)")
            run(["uv", "run", "kinematics", "sweep",
                 "--geometry", str(geometry),
                 "--sweep", str(first),
                 "--out", str(outputs / "01_bump_parallel.csv"),
                 "--animation-out", str(outputs / "motion.gif")])

    print("\n-> report")
    run(["uv", "run", "python", str(SUSREPORT),
         str(outputs), "--out", str(report), "--side", args.side])

    print(f"\ndone. report at {report}")


if __name__ == "__main__":
    main()
