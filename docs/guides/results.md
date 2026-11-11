# Results

Everything is written inside the model folder and git-ignored.

| path | |
| --- | --- |
| `report/<set>/report.md` | start here: solve status, every channel at design / min / max / range, misalignment |
| `report/<set>/` | plots, `summary.csv`, `joints.csv`, `solve_status.csv`, `_resolved_run.json` |
| `sweep_outputs/<set>/` | one CSV per sweep, animations, `_resolved_sweeps/` (exactly what was solved) |
| `sweep_outputs/<set>/<sweep>_forces.csv` | joint forces at every step, for sweeps with `forces:` |
| `forces/forces.csv`, `load_transfer.csv` | [`forces.md`](../reference/forces.md) |
| `run.log` | one line per task of the last run |
| `logs/<set>/<sweep>.log` | per-task output; tracebacks |
| `<batch>/batch_summary.md` / `.csv` | `--batch`: candidates × sweeps, pass counts, failures |

| status | meaning |
| --- | --- |
| `ok` | solved |
| `warn` | solved; steps flagged over `residual_limit` |
| `lockout` | no pose exists at some step (geometry, not software) |
| `geometry` | geometry file does not build |
| `resource` | out of memory after retries |
| `error` | anything else; see the task log |

Channel meanings and SUSProg traps: [`characteristics.md`](../reference/characteristics.md).
Rebuild reports without solving: `run_all.py --report-only --no-forces`.
