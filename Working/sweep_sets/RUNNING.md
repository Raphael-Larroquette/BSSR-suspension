# Running a sweep set

```
uv run python Working/run_all.py                     every sweep set, then forces
uv run python Working/run_all.py --sets front        just the front set, then forces
uv run python Working/run_all.py --sets rear --no-forces
```

That solves every enabled sweep, writes a CSV per sweep, renders the requested
figures and animations, and builds `report.md`.

**There is one command.** `Working/run_all.py` is the only entry point under
`Working/`; it defines every flag below and calls `runner.py` for each sweep
set it was asked to run. `--sets` names a set by its folder, `--config` names
one by path. See [`../README.md`](../README.md) for the whole workflow,
including the force solve that runs after the sweeps unless you pass
`--no-forces`.

## Sweep sets, cars, and reporters

```
Working/
  run_all.py                   the one entry point
  sweep_sets/
    runner.py                  the sweep-set solver - a library, not a command
    susreport.py               reporter: two-wheel axle
    susreport_rear.py          reporter: single corner
    susreport_common.py        what the two reporters share
    bearings.py                bearing misalignment, shared
    front/  run.yaml  sweeps/  a sweep set
    rear/   run.yaml  sweeps/  another one
  models/
    aurora/
      front.yaml  rear.yaml    the car
      outputs/front/  outputs/rear/
      report/front/   report/rear/
```

A **sweep set** is a `run.yaml` plus a `sweeps/` directory. It names itself
(`name:`), names a default geometry (`geometry:`), and names the report module
that suits it (`reporter:`). Results land **beside whatever geometry it is
pointed at**, in a folder called after the set:

```
<geometry folder>/outputs/<name>/     <geometry folder>/report/<name>/
```

So the same sweep set runs against a different car with no reconfiguration and
no collisions:

```
uv run python Working/run_all.py --sets front --geometry Working/models/gen14/front.yaml
                                # -> Working/models/gen14/outputs/front/
```

`--geometry` describes one set, so it needs `--sets` or `--config` to say
which. Running several sets against one geometry would put every result in the
same output folder, and the script refuses rather than doing it.

## Two reporters

| `reporter:` | for | CSV columns | has |
| --- | --- | --- | --- |
| `susreport` | a two-wheel axle | side-suffixed (`camber_left`) | track, body roll, roll centre, rack, Ackermann |
| `susreport_rear` | a single corner | unsuffixed (`camber`) | the side-view family (SVIC, SVSA, anti-squat), which parallel wishbones cannot produce |

They are separate files because the two describe different objects, not the
same object at different detail. What they share — CSV parsing, solver health,
tables, plots, report assembly — is in `susreport_common.py`, and the bearing
misalignment analysis is in `bearings.py`, so a fix there reaches both.

---

## There are no built-in defaults

`run.yaml` is the single source of truth. Neither script carries fallback
values, so a missing or misspelt setting is an **error naming the key**, not a
silent fallback that makes the run disagree with the file you edited:

```
run.yaml: missing required setting(s): decimals.deg, report.gifs,
sweeps.02_roll.plots.
There are no built-in defaults - every setting must be present.
```

Every key in the tables below is required. Two exceptions, both because their
absence is unambiguous: `geometry` may be `null` (meaning "use `model`"), and a
sweep's `gif` may be omitted (meaning "no animation").

Every file in `sweeps/` must also have an entry under `sweeps:`, even if it is
only `run: false`. A sweep file with no entry is an error rather than an
implicit "run it" — a sweep quietly joining the set would also quietly raise a
bearing requirement.

## Precedence

Highest wins:

| | source | scope |
| --- | --- | --- |
| 1 | command-line flags | this invocation only |
| 2 | `run.yaml` | the project |
| 3 | the sweep YAML (`sweeps/NN_*.yaml`) | that sweep |

A range or step count set in `run.yaml` **replaces** the one written in the
sweep file. Anything `run.yaml` does not mention passes through from the sweep
file untouched. The merged result is written to
`outputs/_resolved_sweeps/NN_*.yaml` and *that* is what gets solved, so its
hash lands in the CSV provenance header and you can read exactly what ran.
Those files are regenerated every run — never edit them.

A range key in `run.yaml` must match a target that already exists in the sweep
file. If it does not, the run stops with an error naming the sweep and the
key rather than silently inventing a target.

So in practice: **hardpoint ranges live in `run.yaml`; the sweep files define
the target *structure*** (which points are driven, in which direction, in which
mode). You only touch a sweep file when you want a different kind of sweep, not
a different amount of one.

---

## `run.yaml` reference

### Top level

| key | type | front value | meaning |
| --- | --- | --- | --- |
| `version` | int | `1` | configuration format version |
| `name` | str | `front` | names the `outputs/<name>/` and `report/<name>/` folders |
| `geometry` | path | `../../models/aurora/front.yaml` | default geometry, **relative to this file**; `--geometry` overrides |
| `sweeps_dir` | path | `sweeps` | the sweep YAMLs, relative to this file |
| `reporter` | `susreport` \| `susreport_rear` | `susreport` | which report module builds `report.md` |
| `side` | `left` \| `right` \| `null` | `left` | which corner the per-corner rows report. **`null` for a corner model**, which has only one |

**A standalone corner geometry is `side: left` or, for a wheel on the vehicle
centreline, `side: center`.** The loader rejects `right` — *"side 'right' is
available only through an axle geometry"* — because a right corner is the mirror
of a left one and adds nothing on its own. If a sided wheel faces the other way,
negate every `y` in the geometry file: the suspension is identical by mirror
symmetry.

`center` is accepted only by architectures that support a centreline wheel
(today, the trailing arm), and it changes what the model reports: a wheel on the
centreline has no inboard or outboard, so camber, toe, caster, KPI, scrub
radius, mechanical trail, half track and the front-view swing arm are not
produced at all. See CHARACTERISTICS.md. Sweep targets in that set take the same
`side:` the geometry declares.
| `jobs` | int \| `auto` | `auto` | parallel solver processes; `auto` = min(8, CPU cores) |

### `decimals`

Digits after the point in `report.md`, chosen per unit.

| key | shipped value | applies to |
| --- | --- | --- |
| `mm` | `3` | every length channel |
| `deg` | `4` | every angle channel |
| `ratio` | `4` | `mm/mm`, `deg/deg`, `deg/mm` and unitless |
| `percent` | `2` | `%` channels (Ackermann, anti-geometry) |

### `report`

| key | values | shipped value | meaning |
| --- | --- | --- | --- |
| `joints` | bool | `true` | include the bearing misalignment section |
| `notes` | bool | `true` | include the conventions / degenerate-geometry notes |
| `plots` | `auto` \| `true` \| `false` | `auto` | **master override.** `auto` lets each sweep's own `plots:` decide; `true` forces figures on everywhere; `false` forces them off everywhere |
| `gifs` | `auto` \| `true` \| `false` | `auto` | same, for animations |

The master overrides exist so you can kill every figure or every animation
with one edit while leaving the per-sweep settings intact for next time.

### `solver`

| key | values | shipped value |
| --- | --- | --- |
| `on_bad_solve` | `off` \| `warn` \| `fail` | `warn` |
| `residual_limit` | float | `1.0e-5` |

`residual_limit` is compared against the CSV's `solver_max_residual` column:
the largest constraint violation left in that row after the solve, in the
constraint's own units (mm for lengths, deg for angles). A healthy Aurora step
sits at 1e-6 to 5e-6 mm — four orders of magnitude below anything
geometrically meaningful — so 1e-5 catches a solver that limped without firing
on good rows.

- `off` — no checking; every row is reported as if it solved.
- `warn` — a banner at the top of `report.md` names the sweep and the offending
  step indices, and those rows are **excluded from the min/max/range columns**
  so one bad step cannot set your design envelope. They stay in the CSV.
- `fail` — non-zero exit, no report written.

Without this, a hardpoint move that makes one end of the travel range
unsolvable produces a report that looks completely normal.

### `gif`

Applies to every animation; a per-sweep `gif:` mapping merges over this.

| key | shipped value | meaning |
| --- | --- | --- |
| `fps` | `20` | frames per second |

### `sweeps.<name>`

| key | values | meaning |
| --- | --- | --- |
| `run` | `true` \| `false` | solve it at all. `false` means no CSV is written and the sweep is **invisible to the bearing table** — check the "at" column there before turning one off |
| `report` | `true` \| `false` \| list | `true` = the named channel preset for that sweep kind (`DEFAULT_CHANNELS` in `susreport.py` — a curated list, not a fallback); `false` = solved and written to CSV but no section in `report.md`; a list names channels explicitly, and the table follows that order |
| `plots` | `all` \| `none` \| list | must be a subset of `report` |
| `gif` | `true` \| `false` \| mapping | a mapping merges over the top-level `gif:` block, e.g. `{enabled: true, fps: 30}` |
| `steps` | int | points in the sweep |
| `travel` | `{left: [a, b], right: [a, b]}` on an axle, `[a, b]` on a corner | wheel-centre z, mm relative to design |
| `damper` | same two forms | element length, mm relative to design. Mutually exclusive with `travel` |
| `rack` | `[a, b]` | rack y, mm relative to centre |

A single corner has one wheel and one damper, so its ranges take the bare
`[start, stop]` form; the `{left:, right:}` form is for an axle.

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

All of these are flags of `Working/run_all.py`, and each overrides `run.yaml`
for that invocation only.

**Choosing which sets run:**

| flag | effect |
| --- | --- |
| *(none)* | every sweep set under `sweep_sets/` |
| `--sets A,B` | only these sets, by folder name |
| `--config PATH` | one set by path to its `run.yaml`, for a set outside `sweep_sets/<name>/`. Not with `--sets` |
| `--no-forces` | skip the force solve that otherwise follows the sweeps |
| `--no-sweeps` | skip the sweeps entirely |

**Inside each set that runs:**

| flag | effect |
| --- | --- |
| `--only A,B` | run only these sweeps; everything else is off |
| `--skip A,B` | run everything except these |
| `--plots A,B` | only these sweeps get a figure |
| `--gifs A,B` | only these sweeps get an animation |
| `--no-plots` | no figures at all |
| `--no-gifs` | no animations at all |
| `--no-joints` | drop the bearing misalignment section |
| `--jobs N` | parallel solver processes |
| `--report-only` | rebuild the report from the CSVs already in `outputs/`, solving nothing |
| `--solve-only` | solve and stop, no report |
| `--on-bad-solve MODE` | `off`, `warn` or `fail` |
| `--dry-run` | resolve the configuration, write the merged sweep files, print the commands, solve nothing |
| `--geometry PATH` † | run the set against a different car |
| `--sweeps-dir PATH` † | an alternative directory of sweep YAMLs |
| `--side left\|right` † | reported corner |

† describes a single set, so it requires `--sets` or `--config`.

Sweep selectors accept the numeric prefix or the full stem, so `--only 01,09`
and `--only 01_bump_parallel,09_steer_in_roll` are the same thing. A selector
applies to **every set being run**, so pair it with `--sets` when it only
makes sense for one of them — `--only 04` with both sets selected fails on the
rear, which has no `04`.

### Worked examples

```bash
# everything, exactly as the run.yamls say, plus the force solve
uv run python Working/run_all.py

# iterate on the report without re-solving - the fastest loop by far
uv run python Working/run_all.py --report-only --no-forces

# just the two corner sweeps of the front set, with animations, nothing else
uv run python Working/run_all.py --sets front --only 09,10 --gifs 09,10 --no-forces

# a fast numbers-only pass
uv run python Working/run_all.py --no-plots --no-gifs --no-joints

# check what a config change would actually do before spending the CPU
uv run python Working/run_all.py --dry-run

# the rear only
uv run python Working/run_all.py --sets rear
```

---

## How the parallelism works

Each sweep is an independent `uv run kinematics sweep` subprocess: one geometry
file in, one CSV out, nothing shared. `runner` submits them to a pool of
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

`runner` **imports** the reporter its `run.yaml` names and calls `run_report()` directly — one
process, so a traceback or a breakpoint in `susreport.py` lands in the run you
started. The import is lazy, so a `--solve-only` run never pays for matplotlib.

A reporter never solves anything — it only reads CSVs — so it also runs on
its own, on any folder of CSVs, needing nothing from the `kinematics` package
except for the bearing-misalignment section:

```bash
uv run python Working/sweep_sets/susreport.py Working/models/aurora/outputs/front \
    --out Working/models/aurora/report/front --config Working/sweep_sets/front/run.yaml

uv run python Working/sweep_sets/susreport_rear.py Working/models/aurora/outputs/rear \
    --out Working/models/aurora/report/rear --config Working/sweep_sets/rear/run.yaml
```

With no `--config` it uses `front/run.yaml`. With no configuration
available at all it stops — there are no defaults to fall back on.

`runner` hands it `<geometry folder>/report/<name>/_resolved_run.json` instead: the
configuration after the command-line overrides, written before solving. That
file is the authoritative record of what actually ran, including the list of
sweeps — which is how a sweep you switched off does not sneak back into the
report from a stale CSV left on disk. It is regenerated every run and
gitignored.

### Where each setting is validated

`runner` checks the keys it reads (`name`, `geometry`, `sweeps_dir`,
`reporter`, `side`, `jobs`, `report.plots`, `report.gifs`, `gif.*`, and every
sweep's `run`). The reporter checks the rest
(`decimals`, `solver`, each sweep's `report` and `plots`) when the resolved
configuration reaches it — which happens **before** any solving, so a typo in a
report setting fails in a second rather than after eight solves. `--dry-run`
runs both checks, so it is a complete configuration check.
