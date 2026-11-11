# Optimizer (front)

NSGA-III (pymoo). **The launched script is the whole configuration**; copy it to make a
variant (`optimizer.py`, `underlegoptimizer.py`, `nonunderleg*.py`). `opt/` names no
file of its own.

```bash
uv run python Working/<script>.py                     # search → models/opt_<timestamp>/opt_<timestamp>.csv
uv run python Working/check_design.py Working/<script>.py   # evaluate KNOWN_DESIGN only
uv run python Working/export_pareto.py [opt_<timestamp>]    # → pareto1/, pareto2/, ... (default: latest)
uv run python Working/run_all.py --batch opt_<timestamp> --sets front
```

| script setting | |
| --- | --- |
| `TEMPLATE` | model folder (any, incl. a previous pareto); tyre radius and offset read from it |
| `AXLE`, `SWEEP_SET`, `CASES` | axle patched, sweeps the objectives read, load cases |
| `TRACK_WIDTH`, `CASTER_DEG`, `MIN_ARM_SEPARATION` | design rules `derive_parameters()` uses |
| `POPULATION_SIZE`, `GENERATIONS` | population ≥ reference directions (4 obj → 165, 5 → 210) |
| `POOL_WORKERS`, `WORKERS_PER_POOL` | `None` = all logical CPUs; Windows caps a pool at 60 |
| `SWEEP_LIMITS` | per sweep: `{start, stop}` (single-drive sweeps) or `{travel, damper, rack}` merged over `run.yaml` |
| `SWEEP_STEPS` | steps the optimizer solves each sweep at |
| `FREE_PARAMETERS` | searched variables and bounds |
| `KNOWN_DESIGN` | seed design |
| `OBJECTIVES` | `name: (sweep, metric, "minimize")` |
| `CONSTRAINTS` | `name: (sweep, metric, (lo, hi))`, `None` = unbounded |
| `*_WEIGHTING`, `FORCE_WEIGHTS`, `MIN_SHOCK_LENGTH` | objective weights and limits |

Metrics are reduced in `opt/reduce.py`. Only `opt_<timestamp>.csv` is git-tracked; the
pareto folders are rebuilt by `export_pareto.py` on whichever machine reviews them.
`batch_summary.md` lists candidates × sweeps and the candidates passing everything.
