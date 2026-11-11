"""
Build an interactive page from out/cv2_spread_sweep/forces.csv.

    uv run python Working/studies/cv2_spread_explorer.py

Writes out/cv2_spread_sweep/explorer.html; open it in a browser (it loads
plotly.js from the internet). Two tabs:

  Explorer  Sliders pick one design; a bar chart shows its 7 joint forces
            (worse side) per case. A heatmap shows any two parameters against
            each other with the other three held at the sliders. Click a cell
            to jump there.

  3D        Pick a UCA spread and LCA spread (or click the overview grid, which
            shows the best design for every spread pair). The 3D scatter is
            UCA front x vs LCA front x vs shock x, coloured by the force metric.

Force metric, per arm: mean |F| + max |F| over that arm's joints and both
sides (and both cases when "both" is chosen).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out" / "cv2_spread_sweep"
DESIGN = ["shock_x", "uca_front", "uca_rear", "lca_front", "lca_rear"]
JOINTS = ["lower_wishbone_inboard_front", "lower_wishbone_inboard_rear",
          "lower_wishbone_outboard", "strut_bottom",
          "upper_wishbone_inboard_front", "upper_wishbone_inboard_rear",
          "upper_wishbone_outboard"]

f = pd.read_csv(OUT / "forces.csv")
f["arm"] = np.where(f["joint"].str.startswith("upper"), "UCA", "LCA")
designs = f[DESIGN].drop_duplicates().sort_values(DESIGN).reset_index(drop=True)
designs["id"] = designs.index
f = f.merge(designs, on=DESIGN)
cases = sorted(f["case"].unique())


def column(series):
    """Align to design ids, round to 1 N, NaN -> None for JSON."""
    s = series.reindex(designs["id"]).round(1)
    return [None if np.isnan(v) else float(v) for v in s]


# Joint force, worse side, per case.
worst = f.groupby(["case", "joint", "id"])["F"].max()
bars = {c: {j: column(worst.loc[c, j]) for j in JOINTS} for c in cases}

# Metric = mean + max over the arm's joints and both sides (and cases for "both").
metric = {}
for arm in ("LCA", "UCA"):
    a = f[f["arm"] == arm]
    for case in cases + ["both"]:
        g = (a if case == "both" else a[a["case"] == case]).groupby("id")["F"]
        metric[f"{arm}|{case}"] = column(g.mean() + g.max())

data = {"cases": cases, "joints": JOINTS,
        "p": [designs[c].round(1).tolist() for c in DESIGN],
        "bars": bars, "metric": metric}

html = Path(__file__).with_name("cv2_spread_explorer.html").read_text(encoding="utf-8")
page = OUT / "explorer.html"
page.write_text(html.replace("/*DATA*/null", json.dumps(data, separators=(",", ":"))),
                encoding="utf-8")
print(f"{len(designs)} designs -> {page}")
