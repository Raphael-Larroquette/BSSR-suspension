# `run.yaml` reference

A **sweep set** is one `run.yaml`. It names itself (`name:`), a default geometry
(`geometry:`), a reporter (`reporter:`), and every sweep it runs. Results land beside
whatever geometry it is pointed at:

```
<geometry folder>/outputs/<name>/     <geometry folder>/report/<name>/
```

How to run it and every CLI flag: root `README.md` §5. This page is the key reference.

---

## Sweep files are generated

There are no sweep files to author. Each sweep's targets are built from its `travel`,
`damper` and `rack` keys, written to `outputs/<name>/_resolved_sweeps/<sweep>.yaml`, and
that file is what is solved — so its hash lands in the CSV provenance header and you can
read exactly what ran. Those files are regenerated every run: **never edit them**, and
nothing reads them back.

So a range exists in exactly one place. Precedence is only two deep:

| | source | scope |
| --- | --- | --- |
| 1 | command-line flags | this invocation only |
| 2 | `run.yaml` | everything else |

The one exception is a sweep the vocabulary cannot express — `mode: absolute`, an explicit
`values:` list, a point driven along a non-principal direction. Write that as an ordinary
sweep YAML and name it with **`file:`** (see below). It is then used **verbatim**: no key
in `run.yaml` overrides it, so that sweep's ranges live in one place too.

## There are no built-in defaults

Every key below is required. A missing or misspelt one is an error naming it:

```
run.yaml: missing required setting(s): decimals.deg, report.gifs, sweeps.02_roll.plots.
There are no built-in defaults - every setting must be present.
```

Two exceptions: `geometry` may be `null` (use `model`), and a sweep's `gif` may be omitted
(no animation).

A sweep with `run: false` is not checked for completeness, so it can be parked as a bare
`run: false`. Keeping its ranges instead means flipping it back on just works — which is
why `03_single_wheel_bump` and `07_bump_at_steer` keep theirs.

---

## Top level

| key | type | front value | meaning |
| --- | --- | --- | --- |
| `version` | int | `1` | configuration format version |
| `name` | str | `front` | names the `outputs/<name>/` and `report/<name>/` folders |
| `geometry` | path | `../../models/aurora/front.yaml` | default geometry, **relative to this file**; `--geometry` overrides |
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

The key is the sweep's name: it becomes the CSV filename, the report heading, and what
`--only` / `--skip` match. Sweeps run in the order written here.

### What it reports

| key | values | meaning |
| --- | --- | --- |
| `run` | `true` \| `false` | solve it at all. `false` writes no CSV and makes the sweep **invisible to the bearing table** |
| `report` | `true` \| `false` \| list | `true` = the channel preset for that sweep kind (`DEFAULT_CHANNELS` in `susreport.py`); `false` = solved and written to CSV but no section in `report.md`; a list names channels explicitly, in order |
| `plots` | `all` \| `none` \| list | must be a subset of `report` |
| `gif` | `true` \| `false` \| mapping | a mapping merges over the top-level `gif:`, e.g. `{enabled: true, fps: 30}` |

`report: false` is the useful middle setting: the sweep still solves, still writes its CSV
and still feeds the bearing table, but adds nothing to `report.md`.

### What it drives

This is the sweep. The solver needs **exactly one target per degree of freedom at every
step**, so every corner must be driven exactly once and every actuator must be given a
range.

| key | values | meaning |
| --- | --- | --- |
| `steps` | int | points in the sweep |
| `travel` | `{left: [a, b], right: [a, b]}` on an axle, `[a, b]` on a one-corner model | wheel-centre z, mm from design |
| `damper` | same two forms | element length, mm from design. **Mutually exclusive with `travel`, per corner** |
| `rack` | `[a, b]` | rack y, mm from centre. `[0, 0]` holds it centred — still required |

Each key generates one target per side:

| key | generated target |
| --- | --- |
| `travel` | `{type: point, point: wheel_center, side: <side>, direction: {axis: z}, mode: relative}` |
| `damper` | `{type: element_length, element: damper, side: <side>, mode: relative}` |
| `rack` | `{type: actuator_position, actuator: rack, direction: {axis: y}, mode: relative}` |

Sides come from the geometry's `scope:` / `side:` — `left` and `right` for an axle, the
declared side for a corner, which is why the rear's targets come out `side: center`.
Actuators come from the solver, so a geometry with no rack rejects a `rack:` key and one
with a rack rejects a sweep that omits it. Everything is `mode: relative`, measured from
the authored design condition.

Errors you can provoke, all before anything is solved:

```
sweep '04_steer_design' does not drive 'rack', which this geometry declares.
sweep '01_bump_parallel': corner 'right' is not driven. Add 'travel' or 'damper' for it.
sweep '08_damper_stroke': corner 'left' is driven by both travel and damper.
sweep '01_bump': 'travel' is a bare [start, stop], which is the single-corner form.
```

### `file:` — the escape hatch

| key | values | meaning |
| --- | --- | --- |
| `file` | path, relative to `run.yaml` | use a hand-written sweep YAML instead of generating one |

For anything the vocabulary above cannot say. The file is used **verbatim** — `steps` and
the range keys are not applied to it, and declaring both is an error — then copied into
`_resolved_sweeps/` so that directory stays the complete record of what was solved. The
grammar is in `SWEEPS.md`; copying a generated file out of `_resolved_sweeps/` is the
quickest starting point.

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

`runner` checks `name`, `geometry`, `reporter`, `side`, `jobs`, `report.plots`,
`report.gifs`, `gif.*`, every sweep's `run`, and — against the geometry — every enabled
sweep's drive keys. The reporter checks the
rest (`decimals`, `solver`, each sweep's `report` and `plots`) when the resolved
configuration reaches it — **before** any solving, so a typo fails in a second rather than
after eight solves. `--dry-run` runs both.
