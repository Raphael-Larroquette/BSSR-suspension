# `run.yaml` reference

A **sweep set** is a `run.yaml` plus a `sweeps/` directory. It names itself (`name:`), a
default geometry (`geometry:`) and a reporter (`reporter:`). Results land beside whatever
geometry it is pointed at:

```
<geometry folder>/outputs/<name>/     <geometry folder>/report/<name>/
```

How to run it and every CLI flag: root `README.md` §5. This page is the key reference.

---

## Precedence

Highest wins:

| | source | scope |
| --- | --- | --- |
| 1 | command-line flags | this invocation only |
| 2 | `run.yaml` | the project |
| 3 | the sweep YAML (`sweeps/NN_*.yaml`) | that sweep |

A range or step count set in `run.yaml` **replaces** the one in the sweep file; anything
`run.yaml` does not mention passes through untouched. The merged result is written to
`outputs/<name>/_resolved_sweeps/` and *that* is what is solved, so its hash lands in the
CSV provenance header. Those files are regenerated every run — never edit them.

A range key in `run.yaml` must match a target that already exists in the sweep file;
otherwise the run stops naming the sweep and the key.

**So: ranges live in `run.yaml`; sweep files define the target structure.** You only open
a sweep file to change the *kind* of sweep, not the amount of one.

## There are no built-in defaults

Every key below is required. A missing or misspelt one is an error naming it:

```
run.yaml: missing required setting(s): decimals.deg, report.gifs, sweeps.02_roll.plots.
There are no built-in defaults - every setting must be present.
```

Two exceptions: `geometry` may be `null` (use `model`), and a sweep's `gif` may be omitted
(no animation). Every file in `sweeps/` must also have an entry under `sweeps:`, even if
only `run: false`.

---

## Top level

| key | type | front value | meaning |
| --- | --- | --- | --- |
| `version` | int | `1` | configuration format version |
| `name` | str | `front` | names the `outputs/<name>/` and `report/<name>/` folders |
| `geometry` | path | `../../models/aurora/front.yaml` | default geometry, **relative to this file**; `--geometry` overrides |
| `sweeps_dir` | path | `sweeps` | the sweep YAMLs, relative to this file |
| `reporter` | `susreport` \| `susreport_rear` | `susreport` | which module builds `report.md` |
| `side` | `left` \| `right` \| `null` | `left` | which corner the per-corner rows report. **`null` for a corner model** |
| `jobs` | int \| `auto` | `auto` | parallel solver processes; `auto` = min(8, CPU cores) |

## `decimals`

Digits after the point in `report.md`.

| key | value | applies to |
| --- | --- | --- |
| `mm` | `3` | every length channel |
| `deg` | `4` | every angle channel |
| `ratio` | `4` | `mm/mm`, `deg/deg`, `deg/mm`, unitless |
| `percent` | `2` | `%` channels (Ackermann, anti-geometry) |

## `report`

| key | values | value | meaning |
| --- | --- | --- | --- |
| `joints` | bool | `true` | include the bearing misalignment section |
| `notes` | bool | `true` | include the conventions / degenerate-geometry notes |
| `plots` | `auto` \| `true` \| `false` | `auto` | **master override.** `auto` lets each sweep's own `plots:` decide |
| `gifs` | `auto` \| `true` \| `false` | `auto` | same, for animations |

## `solver`

| key | values | value |
| --- | --- | --- |
| `on_bad_solve` | `off` \| `warn` \| `fail` | `warn` |
| `residual_limit` | float | `1.0e-5` |

`residual_limit` is compared against the CSV's `solver_max_residual` column — the largest
constraint violation left in that row, in the constraint's own units (mm or deg). A
healthy Aurora step sits at 1e-6 to 5e-6 mm, so 1e-5 catches a limping solver without
firing on good rows.

- `off` — no checking.
- `warn` — a banner in `report.md` names the bad steps, and those rows are **excluded from
  the min/max/range columns** so one bad step cannot set your design envelope. They stay
  in the CSV.
- `fail` — non-zero exit, no report written.

## `gif`

| key | value | meaning |
| --- | --- | --- |
| `fps` | `20` | frames per second |

A per-sweep `gif:` mapping merges over this block.

## `sweeps.<name>`

| key | values | meaning |
| --- | --- | --- |
| `run` | `true` \| `false` | solve it at all. `false` writes no CSV and makes the sweep **invisible to the bearing table** |
| `report` | `true` \| `false` \| list | `true` = the channel preset for that sweep kind (`DEFAULT_CHANNELS` in `susreport.py`); `false` = solved and written to CSV but no section in `report.md`; a list names channels explicitly, in order |
| `plots` | `all` \| `none` \| list | must be a subset of `report` |
| `gif` | `true` \| `false` \| mapping | a mapping merges over the top-level `gif:`, e.g. `{enabled: true, fps: 30}` |
| `steps` | int | points in the sweep |
| `travel` | `{left: [a, b], right: [a, b]}` on an axle, `[a, b]` on a corner | wheel-centre z, mm from design |
| `damper` | same two forms | element length, mm from design. **Mutually exclusive with `travel`** |
| `rack` | `[a, b]` | rack y, mm from centre |

`report: false` is the useful middle setting: the sweep still solves, still writes its CSV
and still feeds the bearing table, but adds nothing to `report.md`.

Channel names come from the `CHANNELS` table in `susreport.py` and are defined in
`CHARACTERISTICS.md`. A few are never plotted even under `plots: all` — FVIC, FVSA, SVIC,
SVSA, track, rack and wheel travel — because they are constant or pass through a
singularity that flattens every other curve. See `NEVER_PLOT` in `susreport.py`.

---

## Two reporters

| `reporter:` | for | CSV columns | has |
| --- | --- | --- | --- |
| `susreport` | a two-wheel axle | side-suffixed (`camber_left`) | track, body roll, roll centre, rack, Ackermann |
| `susreport_rear` | a single corner | unsuffixed (`camber`) | the side-view family (SVIC, SVSA, anti-squat) |

Shared code — CSV parsing, solver health, tables, plots, report assembly — is in
`susreport_common.py`; bearing misalignment is in `bearings.py`.

## Parallelism

Each sweep is an independent `uv run kinematics sweep` subprocess submitted to a pool of
`jobs` workers. Two stages stay serial: the **report** (it needs every CSV) and
**animations** (the writer holds every frame in memory). So expect roughly `jobs`× on the
solve phase and no change elsewhere.

## Calling the report builder directly

`runner` imports the reporter its `run.yaml` names and calls `run_report()` in-process, so
a traceback or breakpoint lands in the run you started. The import is lazy, so
`--solve-only` never pays for matplotlib.

A reporter never solves — it only reads CSVs — so it also runs standalone on any folder of
CSVs:

```bash
uv run python Working/sweep_sets/susreport.py Working/models/aurora/outputs/front \
    --out Working/models/aurora/report/front --config Working/sweep_sets/front/run.yaml
```

With no `--config` it uses `front/run.yaml`; with no configuration at all it stops.

In a normal run, `runner` hands it `<geometry folder>/report/<name>/_resolved_run.json`
instead — the configuration after CLI overrides, written before solving. That file is the
authoritative record of what ran, including the sweep list, which is how a sweep you
switched off cannot sneak back in from a stale CSV.

## Where each setting is validated

`runner` checks `name`, `geometry`, `sweeps_dir`, `reporter`, `side`, `jobs`,
`report.plots`, `report.gifs`, `gif.*` and every sweep's `run`. The reporter checks the
rest (`decimals`, `solver`, each sweep's `report` and `plots`) when the resolved
configuration reaches it — **before** any solving, so a typo fails in a second rather than
after eight solves. `--dry-run` runs both.
