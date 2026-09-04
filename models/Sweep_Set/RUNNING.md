# Running the sweep set

```
uv run python models/Sweep_Set/run_all.py
```

That solves every enabled sweep, writes a CSV per sweep into
`models/<model>/outputs/`, renders the requested figures and animations, and
builds `models/<model>/report/report.md`.

Everything that is not a hardpoint is configured in **`run.yaml`** next to
`run_all.py`. This file documents its keys, the command-line overrides, and
how the two interact.

---

## Precedence

Highest wins:

| | source | scope |
| --- | --- | --- |
| 1 | command-line flags | this invocation only |
| 2 | `run.yaml` | the project |
| 3 | the sweep YAML (`sweeps/NN_*.yaml`) | that sweep |
| 4 | built-in defaults (`DEFAULTS` in `run_all.py`) | fallback |

A range or step count set in `run.yaml` **replaces** the one written in the
sweep file. Anything `run.yaml` does not mention passes through from the sweep
file untouched. The merged result is written to
`outputs/_resolved_sweeps/NN_*.yaml` and *that* is what gets solved, so its
hash lands in the CSV provenance header and you can read exactly what ran.
Those files are regenerated every run — never edit them.

A range key in `run.yaml` must match a target that already exists in the sweep
file. If it does not, `run_all` stops with an error naming the sweep and the
key rather than silently inventing a target.

So in practice: **hardpoint ranges live in `run.yaml`; the sweep files define
the target *structure*** (which points are driven, in which direction, in which
mode). You only touch a sweep file when you want a different kind of sweep, not
a different amount of one.

---

## `run.yaml` reference

### Top level

| key | type | default | meaning |
| --- | --- | --- | --- |
| `version` | int | `1` | configuration format version |
| `model` | str | `aurora` | folder under `models/` holding the geometry |
| `geometry` | path \| null | `null` | explicit geometry YAML; overrides `model` |
| `side` | `left` \| `right` | `left` | which corner the per-corner rows report |
| `jobs` | int \| `auto` | `auto` | parallel solver processes; `auto` = min(8, CPU cores) |

### `decimals`

Digits after the point in `report.md`, chosen per unit.

| key | default | applies to |
| --- | --- | --- |
| `mm` | `3` | every length channel |
| `deg` | `4` | every angle channel |
| `ratio` | `4` | `mm/mm`, `deg/deg`, `deg/mm` and unitless |
| `percent` | `2` | `%` channels (Ackermann, anti-geometry) |

### `report`

| key | values | default | meaning |
| --- | --- | --- | --- |
| `joints` | bool | `true` | include the bearing misalignment section |
| `notes` | bool | `true` | include the conventions / degenerate-geometry notes |
| `plots` | `auto` \| `true` \| `false` | `auto` | **master override.** `auto` lets each sweep's own `plots:` decide; `true` forces figures on everywhere; `false` forces them off everywhere |
| `gifs` | `auto` \| `true` \| `false` | `auto` | same, for animations |

The master overrides exist so you can kill every figure or every animation
with one edit while leaving the per-sweep settings intact for next time.

### `solver`

| key | values | default |
| --- | --- | --- |
| `on_bad_solve` | `off` \| `warn` \| `fail` | `warn` |
| `residual_limit` | float | `1.0e-5` |

`residual_limit` is compared against the CSV's `solver_max_residual` column:
the largest constraint violation left in that row after the solve, in the
constraint's own units (mm for lengths, deg for angles). A healthy Aurora step
sits at 1e-6 to 5e-6 mm — four orders of magnitude below anything
geometrically meaningful — so the default catches a solver that limped without
firing on good rows.

- `off` — no checking; every row is reported as if it solved.
- `warn` — a banner at the top of `report.md` names the sweep and the offending
  step indices, and those rows are **excluded from the min/max/range columns**
  so one bad step cannot set your design envelope. They stay in the CSV.
- `fail` — non-zero exit, no report written.

Without this, a hardpoint move that makes one end of the travel range
unsolvable produces a report that looks completely normal.

### `gif`

Defaults for every animation; a per-sweep `gif:` mapping merges over this.

| key | default | meaning |
| --- | --- | --- |
| `fps` | `20` | frames per second |
| `overlays` | `[fvic, fvsa, roll_center]` | construction geometry drawn on top of the members. Any of `fvic`, `fvsa`, `svic`, `svsa`, `roll_center`. An empty list renders the members alone |
| `overlay_frame` | `3.0` | how many times the geometry half-range an overlay marker may stray before it is clipped |

Instant centres routinely sit tens of metres from a car two metres wide, and
the front-view IC runs to infinity every time the wishbones pass through
parallel. Autoscaling to include one would shrink the suspension to a dot, so a
marker outside the frame is pulled back onto the boundary along the same
direction and drawn **hollow** — filled means "this is where the point actually
is". The true value is printed in the animation title.

Asking for `fvsa` implies `fvic` (and `svsa` implies `svic`): a swing arm drawn
without its instant centre is a line to nowhere.

### `sweeps.<name>`

| key | values | meaning |
| --- | --- | --- |
| `run` | `true` \| `false` | solve it at all. `false` means no CSV is written and the sweep is **invisible to the bearing table** — check the "at" column there before turning one off |
| `report` | `true` \| `false` \| list | `true` = the default channel set for that sweep kind; `false` = solved and written to CSV but no section in `report.md`; a list names channels explicitly, and the table follows that order |
| `plots` | `all` \| `none` \| list | must be a subset of `report` |
| `gif` | `true` \| `false` \| mapping | a mapping merges over the top-level `gif:` block, e.g. `{enabled: true, fps: 30}` |
| `steps` | int | points in the sweep |
| `travel` | `{left: [a, b], right: [a, b]}` | wheel-centre z, mm relative to design |
| `damper` | `{left: [a, b], right: [a, b]}` | element length, mm relative to design. Mutually exclusive with `travel` |
| `rack` | `[a, b]` | rack y, mm relative to centre |

`report: false` is the useful middle setting: the sweep still solves, still
writes its CSV, and still feeds the bearing misalignment table, but adds
nothing to `report.md`.

Channel names are defined by the `CHANNELS` table in `susreport.py` and
explained in `CHARACTERISTICS.md`. A few channels are never plotted even under
`plots: all` — FVIC, FVSA, SVIC, SVSA, track, rack and wheel travel — because
they are either constant or pass through a singularity that flattens every
other curve in the figure. See `NEVER_PLOT` in `susreport.py`.

---

## Command-line overrides

Every flag overrides `run.yaml` for that invocation only.

| flag | effect |
| --- | --- |
| `--config PATH` | use a different run configuration (default: `run.yaml` beside the script) |
| `--model NAME` | folder under `models/` |
| `--geometry PATH` | explicit geometry file |
| `--sweeps-dir PATH` | an alternative directory of sweep YAMLs |
| `--side left\|right` | reported corner |
| `--only A,B` | run only these sweeps; everything else is off |
| `--skip A,B` | run everything except these |
| `--plots A,B` | only these sweeps get a figure |
| `--gifs A,B` | only these sweeps get an animation |
| `--no-plots` | no figures at all |
| `--no-gifs` | no animations at all |
| `--no-joints` | drop the bearing misalignment section |
| `--gif-overlays a,b` | overlays for every animation; `none` for a clean render |
| `--jobs N` | parallel solver processes |
| `--report-only` | rebuild the report from the CSVs already in `outputs/`, solving nothing |
| `--solve-only` | solve and stop, no report |
| `--on-bad-solve MODE` | `off`, `warn` or `fail` |
| `--dry-run` | resolve the configuration, write the merged sweep files, print the commands, solve nothing |

Sweep selectors accept the numeric prefix or the full stem, so `--only 01,09`
and `--only 01_bump_parallel,09_steer_in_roll` are the same thing.

### Worked examples

```bash
# everything, exactly as run.yaml says
uv run python models/Sweep_Set/run_all.py

# iterate on the report without re-solving - the fastest loop by far
uv run python models/Sweep_Set/run_all.py --report-only

# just the two corner sweeps, with animations, nothing else
uv run python models/Sweep_Set/run_all.py --only 09,10 --gifs 09,10

# a fast numbers-only pass
uv run python models/Sweep_Set/run_all.py --no-plots --no-gifs --no-joints

# check what a config change would actually do before spending the CPU
uv run python models/Sweep_Set/run_all.py --dry-run

# clean animation with no construction geometry
uv run python models/Sweep_Set/run_all.py --gifs 01 --gif-overlays none

# the rear axle, when it exists
uv run python models/Sweep_Set/run_all.py --model aurora --geometry models/aurora/rear.yaml
```

---

## How the parallelism works

Each sweep is an independent `uv run kinematics sweep` subprocess: one geometry
file in, one CSV out, nothing shared. `run_all` submits them to a pool of
`jobs` workers, so they cannot race and there is nothing to synchronise. Since
the work happens in subprocesses rather than in Python, the GIL is not
involved; the limit is CPU cores and the solver's own memory.

Two stages stay serial on purpose:

- **The report**, because it needs every CSV before it can start.
- **Animations**, because the writer holds every frame in memory and several at
  once thrash rather than go faster. `--jobs` does not affect them.

So expect roughly `jobs`× on the solve phase and no change to the rest. On the
current eight-sweep Aurora set the solve is the dominant cost, so it is worth
setting.

---

## Calling the report builder directly

`susreport.py` never solves anything — it only reads CSVs — so you can point it
at an output directory by hand:

```bash
uv run python models/Sweep_Set/susreport.py models/aurora/outputs \
    --out models/aurora/report --config models/Sweep_Set/run.yaml
```

`run_all` instead passes `--resolved models/<model>/report/_resolved_run.json`,
which is the configuration after the command-line overrides have been applied.
That file is the authoritative record of what actually ran, including the list
of sweeps — which is how a sweep you switched off does not sneak back into the
report from a stale CSV left on disk.
