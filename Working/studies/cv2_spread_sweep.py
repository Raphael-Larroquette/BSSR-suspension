"""
CV2 front: static joint forces over a grid of shock x and inboard pivot layouts.

Each arm's two inboard pivots keep a fixed spread (front.x - rear.x) and the
pair slides fore-aft in STEP increments, staying inside the arm's limits. The
shock (strut_top and strut_bottom together) slides in x. Designs where the
shock is not between BOTH arms' inboard pivots are rejected.

    uv run python Working/studies/cv2_spread_sweep.py              # all cores
    uv run python Working/studies/cv2_spread_sweep.py --workers 1  # serial

Writes out/cv2_spread_sweep/forces.csv. Plot with cv2_spread_plot.py.
"""

import argparse
import copy
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

WORKING = Path(__file__).resolve().parents[1]
MODEL = WORKING / "models" / "CV2"
OUT = Path(__file__).resolve().parent / "out" / "cv2_spread_sweep"

# ---- 1. Inputs (mm) -------------------------------------------------------
CASES = ["2,1,1", "6,0,0"]                # bump,brake,corner
STEP = 15                                 # fore-aft step, shock and pivot pairs
SHOCK_X = np.arange(-100, 100 + 1, STEP)  # CV2 is at 5
UCA_SPREADS = np.arange(90, 190 + 1, 20)
UCA_LIMITS = (-150, 150)                  # both UCA pivots stay inside
LCA_SPREADS = np.arange(100, 250 + 1, 25)
LCA_LIMITS = (-300, 230)

COLUMNS = ["shock_x", "uca_front", "uca_rear", "lca_front", "lca_rear"]
POINTS = {  # which hardpoint x each column sets
    "shock_x": ["strut_top", "strut_bottom"],
    "uca_front": ["upper_wishbone_inboard_front"],
    "uca_rear": ["upper_wishbone_inboard_rear"],
    "lca_front": ["lower_wishbone_inboard_front"],
    "lca_rear": ["lower_wishbone_inboard_rear"],
}
ARMS = ("Lower Wishbone", "Upper Wishbone")


# ---- 2. Matrix of designs, 3. minus illegal shock positions -------------
def pairs(spreads, limits):
    """Every (front, rear) with front - rear = spread, both inside limits."""
    lo, hi = limits
    return [(rear + s, rear) for s in spreads for rear in np.arange(lo, hi - s + 1e-9, STEP)]


def design_matrix():
    uca, lca = pairs(UCA_SPREADS, UCA_LIMITS), pairs(LCA_SPREADS, LCA_LIMITS)
    rows = [(sx, uf, ur, lf, lr)
            for sx in SHOCK_X for uf, ur in uca for lf, lr in lca
            if ur <= sx <= uf and lr <= sx <= lf]
    print(f"{len(SHOCK_X) * len(uca) * len(lca)} designs, {len(rows)} with the "
          "shock between both arms' pivots")
    return rows


# ---- 4. Solve one design (runs in a worker) ------------------------------
_INPUTS = None


def inputs():
    """Force config, rear axle, cases and CV2 front template; once per process."""
    global _INPUTS
    if _INPUTS is None:
        from kinematics.cli.commands.forces import build_options, resolve_paths
        from kinematics.cli.io.cases_loader import load_cases
        from kinematics.cli.io.forces_loader import load_forces_config
        from kinematics.cli.io.loaders import load_geometry

        config = load_forces_config(MODEL / "forces.yaml")
        paths = resolve_paths(config, MODEL / "forces.yaml", cases=WORKING / "cases.csv")
        cases = {}
        with tempfile.TemporaryDirectory() as tmp:
            for i, label in enumerate(CASES):  # one file per case: rows are unambiguous
                path = Path(tmp) / f"{i}.csv"
                path.write_text(f"bump,brake,corner\n{label}\n")
                cases[label] = load_cases(path)
        template = yaml.safe_load((MODEL / "front.yaml").read_text(encoding="utf-8"))
        _INPUTS = (config, load_geometry(paths.rear), cases, build_options(config), template)
    return _INPUTS


def solve(design):
    """Joint |F| on the LCA and UCA for every case and side. design=None is CV2 as authored."""
    from kinematics.core.input import build_suspension
    from kinematics.core.loads.main import solve_forces

    config, rear, cases, options, template = inputs()
    data = copy.deepcopy(template)
    for column, x in zip(COLUMNS, design or []):
        for point in POINTS[column]:
            data["hardpoints"]["left"][point]["x"] = float(x)
    try:
        front = build_suspension(data)
        rows = []
        for label, case in cases.items():
            run = solve_forces((front, rear), case, mass=config.vehicle.mass,
                               gravity=config.vehicle.g, options=options)
            for block in run.solution.blocks:
                if block.part in ARMS:
                    for row in block.rows:
                        side = str(getattr(row.side, "value", row.side))
                        rows += [(label, side, load.name, float(np.linalg.norm(load.force)))
                                 for load in row.loads if not load.applied]
        return rows, None
    except Exception as exc:
        return [], f"{design}: {type(exc).__name__}: {exc}"


# ---- 5. Run everything and collect --------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=min(61, os.cpu_count() or 1))
    args = parser.parse_args()

    baseline, error = solve(None)
    if error:
        raise SystemExit(f"CV2 as authored did not solve: {error}")
    print("CV2 as authored - check against models/CV2/forces/forces.csv:")
    print(pd.DataFrame(baseline, columns=["case", "side", "joint", "F"])
          .pivot_table(index="joint", columns=["case", "side"], values="F").round(1))

    designs = design_matrix()
    if args.workers > 1:
        with ProcessPoolExecutor(args.workers) as pool:
            results = list(pool.map(solve, designs, chunksize=32))
    else:
        results = [solve(d) for d in designs]

    rows = [(*d, *r) for d, (rs, _) in zip(designs, results) for r in rs]
    errors = [e for _, e in results if e]
    print(f"{len(designs) - len(errors)} solved, {len(errors)} failed")
    for e in errors[:3]:
        print("  e.g.", e)

    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=COLUMNS + ["case", "side", "joint", "F"]).to_csv(
        OUT / "forces.csv", index=False)
    print(f"wrote {OUT / 'forces.csv'}")


if __name__ == "__main__":
    main()
