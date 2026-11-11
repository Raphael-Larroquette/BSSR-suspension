# Sweep sets, `run.yaml` and CLI flags

A sweep set is one `Working/sweep_sets/<set>/run.yaml`. Sweep files are **generated**
from it into `<model>/sweep_outputs/<set>/_resolved_sweeps/` (read-only; regenerated every
run). Precedence: CLI flags > `run.yaml`. No built-in defaults: every key below is
required, except `geometry` (may be `null`) and a sweep's `gif`. A `run: false` sweep is
not checked.

## Top level

| key | values | |
| --- | --- | --- |
| `version` | `1` | |
| `name` | str | names `sweep_outputs/<name>/`, `report/<name>/` |
| `geometry` | path, relative to `run.yaml` | default geometry; `--model` / `--geometry` override |
| `reporter` | `susreport` \| `susreport_rear` | two-wheel axle \| single corner |
| `side` | `left` \| `right` \| `null` | per-corner rows; `null` for a corner model |
| `decimals.mm` / `.deg` / `.ratio` / `.percent` | int | digits in `report.md` |
| `report.joints` / `.notes` | bool | misalignment / notes sections |
| `report.plots` / `.gifs` | `auto` \| `true` \| `false` | master override; `auto` = per sweep |
| `solver.on_bad_solve` | `off` \| `warn` \| `fail` | `warn`: flag steps over the limit and drop them from min/max/range |
| `solver.residual_limit` | float | vs the CSV's `solver_max_residual` (mm or deg) |
| `gif.fps` / `.dpi` / `.format` | int, int, `gif` \| `mp4` | frames are 16 x 10 in; render time ∝ dpi² |

## `sweeps.<name>`

Name = CSV stem, report heading, what `--only` / `--skip` match. Runs in file order.

| key | values | |
| --- | --- | --- |
| `run` | bool | `false`: no CSV, invisible to the bearing table |
| `report` | `true` \| `false` \| list | `true` = preset (`DEFAULT_CHANNELS` in the reporter); `false` = CSV only |
| `plots` | `all` \| `none` \| list | subset of `report` |
| `gif` | bool \| mapping | mapping merges over top-level `gif` |
| `steps` | int | |
| `travel` | axle `{left: [a, b], right: [a, b]}`; corner `[a, b]` | wheel-centre z, mm from design |
| `damper` | same forms | damper length, mm from design; not with `travel` on the same corner |
| `rack` | `[a, b]` | rack y, mm from centre; required whenever the geometry has a rack |
| `file` | path | hand-written sweep, used verbatim; excludes `steps` and the drive keys |
| `forces` | list of `[bump, brake, corner]` (g) | optional: solve these cases at every step → `<sweep>_forces.csv` ([`forces.md`](forces.md)). Needs the model's `forces.yaml`; `--no-forces` skips it |

Every corner must be driven exactly once and every actuator given a range; violations are
named before solving. Generated targets are `mode: relative`. Channel names:
[`characteristics.md`](characteristics.md). Never plotted even under `all`: FVIC, FVSA,
SVIC, SVSA, track, rack, wheel travel (`NEVER_PLOT`).

## Hand-written sweep files (`file:`)

Needed only for what the drive keys can't say: `mode: absolute`, `values:` lists, a
non-principal direction. Start from a file in `_resolved_sweeps/`.

```yaml
version: 1
steps: 65                 # needed if any target uses start/stop
targets:
  - type: point           # point | actuator_position | element_length
    point: wheel_center   # point: any PointID except wheel_contact_centre
    side: left            # left | right | center; omit for shared (rack)
    direction: {axis: z}  # or {vector: [x, y, z]}; not on element_length
    mode: relative        # relative | absolute
    start: -55            # or values: [...]
    stop: 50
```

| type | identifier key | values |
| --- | --- | --- |
| `point` | `point` | PointID |
| `actuator_position` | `actuator` | `rack` (shared, no side) |
| `element_length` | `element` | `damper` \| `heave_link` |

- One target per DOF per step. Targets **pair by index** (no grid): equal-length
  sequences, step *i* of each together.
- DOF count: DW axle with rack = 3 (wheel z L, R, rack); corner with rack = 2; centreline
  trailing arm = 1.
- Analytic `deriv_*_wrt_hub_z` columns need a wheel-centre target; damper-driven sweeps
  leave them NaN.

## CLI (`Working/run_all.py`)

| flag | |
| --- | --- |
| *(none)* | Aurora: every set, then forces |
| `--model NAME\|PATH` / `--batch FOLDER` | another model / every model in a folder (`batch_summary.md`) |
| `--sets a,b` / `--config PATH` | sets by folder name / one set by path |
| `--no-sweeps` / `--no-forces` | skip a stage |
| `--only` / `--skip A,B` | sweeps by number or stem, in every selected set |
| `--plots` / `--gifs A,B` | only these get figures / animations |
| `--no-plots` / `--no-gifs` / `--no-joints` | drop them |
| `--report-only` / `--solve-only` | reports from existing CSVs / no reports |
| `--on-bad-solve off\|warn\|fail` | overrides `solver.on_bad_solve` |
| `--geometry PATH` / `--side left\|right` | one set only (needs `--sets` or `--config`) |
| `--workers N` | cap on worker processes |
| `--list` / `--dry-run` | list sets and models / validate and check models, exit 1 on any problem |

A run: plan (validate, generate sweeps) → solve (one pool: every sweep and force solve) →
report + animate (only solved sweeps) → summary. A failed sweep stops nothing; the report
lists it in **Solve status**. Pool size = min(physical cores, memory allows, tasks,
`--workers`, 61 on Windows); out-of-memory tasks retry with fewer workers. Logic:
`scheduler.py`, `tasks.py`.

Standalone report from existing CSVs:

```bash
uv run python Working/sweep_sets/susreport.py <sweep_outputs/set> --out <report/set> --config <run.yaml>
```

## Aurora sweeps

| front | drives | answers |
| --- | --- | --- |
| 01 `bump_parallel` | both wheels | camber, bump steer, MR/IR, RC height |
| 02 `roll` | equal and opposite | camber recovery, RC migration, roll steer, track change |
| 03 `single_wheel_bump` (off) | left only | nothing 01 doesn't, until a cross-axle element exists |
| 04 / 05 / 06 `steer_design` / `_bump` / `_droop` | rack at design / bump / droop | Ackermann, steering ratio, geometry vs steer, loaded vs unloaded |
| 07 `bump_at_steer` (off) | bump, rack held | bump-steer curve shape while steered |
| 08 `damper_stroke` | damper length | usable wheel travel; MR/IR in hardware coordinates |
| 09 `steer_in_roll` | rack 0 → lock at held roll | mid-corner steering, Ackermann in roll |
| 10 `corner_ramp` | roll and steer ramp together | constant-speed corner; outer/inner road camber (`road_camber` objective) |

Rack +y steers **right**, so in 09/10 the **left** wheel is outer and in bump.

| rear | drives | answers |
| --- | --- | --- |
| 01 `bump` | wheel centre | MR/IR, recession, side-view IC/SVSA, anti-squat; joint forces over travel (6 g) |
| 02 `damper_stroke` | damper length | usable wheel travel |
