"""
Plot out/cv2_spread_sweep/forces.csv: one figure per load case, one panel per
LCA/UCA joint.

Each dot is one design, using the worse side. x is that arm's pivot spread and
colour is the shock's offset from the midpoint of that arm's pivots. The black
line is the lowest force reached at each spread. A tall column of dots at one
spread means the remaining parameters (pair position, the other arm) matter.

    uv run python Working/studies/cv2_spread_plot.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

OUT = Path(__file__).resolve().parent / "out" / "cv2_spread_sweep"
DESIGN = ["shock_x", "uca_front", "uca_rear", "lca_front", "lca_rear"]

f = pd.read_csv(OUT / "forces.csv")
f = f.groupby(DESIGN + ["case", "joint"], as_index=False)["F"].max()  # worse side
upper = f["joint"].str.startswith("upper")
front = f["uca_front"].where(upper, f["lca_front"])  # this joint's own arm
rear = f["uca_rear"].where(upper, f["lca_rear"])
f["spread"] = front - rear
f["offset"] = f["shock_x"] - (front + rear) / 2

joints = sorted(f["joint"].unique(), key=lambda j: (not j.startswith("lower"), j))
for case, data in f.groupby("case"):
    fig, axes = plt.subplots(2, 4, figsize=(16, 7.5), constrained_layout=True)
    for ax, joint in zip(axes.flat, joints):
        d = data[data["joint"] == joint]
        dots = ax.scatter(d["spread"], d["F"], c=d["offset"], cmap="coolwarm",
                          s=6, alpha=0.5, vmin=-125, vmax=125)
        best = d.groupby("spread")["F"].min()
        ax.plot(best.index, best.values, "k-o", ms=3, label="lowest")
        ax.set_title(joint.replace("_wishbone", ""), fontsize=10)
        ax.set_xlabel(f"{'UCA' if joint.startswith('upper') else 'LCA'} spread [mm]")
        ax.set_ylabel("|F| [N]")
        ax.grid(alpha=0.3)
    axes.flat[-1].axis("off")
    fig.colorbar(dots, ax=axes, label="shock x - arm pivot midpoint [mm]")
    fig.suptitle(f"Joint force vs arm spread, case {case} (worse side)")
    fig.savefig(OUT / f"forces_{case.replace(',', '')}.png", dpi=130)
    plt.close(fig)
print(f"wrote plots to {OUT}")
