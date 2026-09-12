# Working — how to run the suspension tool

Everything that describes a **car** rather than the solver, and the entry point
for every workflow run against it. If you are here to *use* the tool rather
than change it, this is the only page you need to start from; each step below
links to the reference that goes deeper.

```bash
uv run python Working/run_all.py
```

That is the whole thing: every kinematic sweep set, then the static force
solve. **There is one command.** Everything else on this page is how to
configure what it does, and how to narrow it to the part you care about.

Run it from the **repository root**, with the environment set up
(`just setup`). Every path in this document is relative to that root.

---

## The four steps, in order

| # | You do this | In | Reference |
| --- | --- | --- | --- |
| 1 | Describe the car — hardpoints, architecture, vehicle data | `models/aurora/front.yaml`, `rear.yaml` | [`models/MODELS.md`](models/MODELS.md) |
| 2 | Declare the bearings you want misalignment for | the `joints:` block of those same files | [`models/MODELS.md` §6](models/MODELS.md#6-the-joints-block) |
| 3 | Choose and run the kinematic sweeps | `sweep_sets/*/run.yaml` | [`sweep_sets/RUNNING.md`](sweep_sets/RUNNING.md), [`SWEEPS.md`](sweep_sets/SWEEPS.md) |
| 4 | Solve the joint forces for FEA | `forces/aurora/forces.yaml`, `cases.csv` | [`forces/force.md`](forces/force.md) |

Steps 3 and 4 read the **same** geometry from step 1. That is why they live
side by side and why one command does both: a hardpoint edit invalidates both
results at once.

---

## 1. Describe the car

Two files, one per end of the vehicle:

```
models/aurora/front.yaml     an AXLE  — two mirrored double-wishbone corners
models/aurora/rear.yaml      a CORNER — one centreline trailing arm
```

A model file holds the hardpoints, the architecture (`type:`, `actuation:`,
`spring:`, `steering:`), the wheel and tyre, and the whole-vehicle data
(`cg_position`, `wheelbase`) that both workflows need. `cg_position` and
`wheelbase` are authored in **both** files and cross-checked.

ISO 8855 throughout: **+X forward, +Y left, +Z up**, mm, origin at the front
axle centreline on the ground plane. Left-side hardpoints have positive Y.

**→ [`models/MODELS.md`](models/MODELS.md) is the syntax reference**: the two
file shapes (`scope: axle` vs `scope: corner`), every configuration key, the
hardpoint name for every architecture and mechanism, and what is derived
rather than authored.

Check it before you spend any CPU:

```bash
uv run python Working/models/aurora/check.py Working/models/aurora/front.yaml
uv run kinematics visualize --geometry Working/models/aurora/front.yaml --output front.png
```

The first says whether it loads and builds. The second draws the design
condition and tells you whether every derived wheel contact centre lands on
the reconstructed road plane — fix that before reading any characteristic,
because every road-plane metric is built on it.

---

## 2. Declare the joints

The `joints:` block **inside the same geometry file** is what produces the
bearing misalignment table in `report.md`. It answers: given how the
suspension actually moves, how much tilt does this bearing, on this axis, have
to absorb? That is the number you take to a catalogue.

It is optional and **opt-in per point** — an undeclared hardpoint produces no
output at all. It changes no kinematics and is not read by the force solve.

```yaml
joints:
  lower_wishbone_outboard:
    label: "LBJ"
    type: spherical            # bushing | spherical | rod_end — vocabulary only, no physics
    bore:                      # bolt/ball axis, fixed to one part
      part: upright
      axis: {from: lower_wishbone_outboard, to: upper_wishbone_outboard}
    housing:                   # housing direction, fixed to the other part
      part: lower_wishbone
      axis: centred
```

The two directions are declared independently, so when they do not coincide at
the neutral pose the bearing is installed deliberately off centre and the
difference is reported as the **install offset**.

The three keywords are the part worth knowing:

| on | keyword | implies |
| --- | --- | --- |
| `bore` | `optimize` | no axis chosen yet — no per-step value, but the report still gives the **best available** axis and what it would cost |
| `housing` | `centred` | housing installed exactly on the bore axis; install offset is zero by construction |
| `housing` | `indeterminate` | housing rides a two-point member whose spin nothing determines — the report gives a **band**: a free-to-spin lower bound plus a locked value and its clocking. **Size against the locked value.** |

Prefer the two-point axis form (`{from:, to:}`) over `{vector: [...]}`: it
tracks the hardpoints instead of going stale the moment one moves.

**Nothing here needs a re-solve.** The sweeps export the axis-independent
relative rotation, so tuning this block is a `--report-only` loop:

```bash
uv run python Working/run_all.py --report-only --no-forces
```

**→ [`models/MODELS.md` §6](models/MODELS.md#6-the-joints-block)** for the
full syntax: all four axis spellings, `perpendicular_to` / `in_plane` /
`cone_deg`, explicit `part: {points: [...]}`, and how to read the output
table.

---

## 3. Run the kinematic sweeps

A **sweep set** is a `run.yaml` plus a `sweeps/` directory. It solves the
suspension through a range of motion, writes a CSV per sweep, renders figures
and animations, and builds `report.md`.

```
sweep_sets/front/   run.yaml  sweeps/01..10     Aurora front — 10 sweeps, 8 enabled
sweep_sets/rear/    run.yaml  sweeps/01..02     Aurora rear  — 2 sweeps
```

The folder name is what `--sets` matches, so `--sets front` is the front
suspension and nothing else.

### What is being swept

| set | sweep | drives | answers |
| --- | --- | --- | --- |
| front | `01_bump_parallel` | both wheels together | camber curve, bump steer, motion ratio, RC height vs ride |
| front | `02_roll` | equal and opposite | camber recovery, RC migration, roll steer, track change |
| front | `03_single_wheel_bump` | left only | **off** — adds nothing 01 does not |
| front | `04_steer_design` | rack lock to lock at design height | Ackermann, steering ratio, camber/caster/KPI vs steer, scrub and trail |
| front | `05_steer_bump` | the same, in bump | how much steering geometry changes when loaded |
| front | `06_steer_droop` | the same, in droop | the other end of that comparison |
| front | `07_bump_at_steer` | bump with the rack held off centre | **off** — turn on when chasing bump steer specifically |
| front | `08_damper_stroke` | damper length | usable wheel travel for a given damper stroke; the honest motion ratio |
| front | `09_steer_in_roll` | rack lock to lock at a held roll attitude | mid-corner steering geometry; the only place Ackermann-in-roll is defined |
| front | `10_corner_ramp` | roll and steer ramping together | one line through corner entry |
| rear | `01_bump` | wheel centre | camber and toe curves, motion ratio, recession, the side-view family |
| rear | `02_damper_stroke` | damper length | usable wheel travel; the honest motion ratio |

Aurora's rear is a single centreline corner with one degree of freedom, so
roll, Ackermann and steer sweeps have no meaning there — the set is small on
purpose rather than a mirror of the front. The reasoning behind every
enabled/disabled choice is in [`sweep_sets/README.md`](sweep_sets/README.md).

### Changing what they do

Three files, in order of how often you touch them:

| To change | Edit | Reference |
| --- | --- | --- |
| ranges, step counts, which sweeps run, which characteristics each reports, plots, gifs, decimals, solver policy | that set's **`run.yaml`** | [`sweep_sets/RUNNING.md`](sweep_sets/RUNNING.md) |
| the *kind* of sweep — which points are driven, in which direction and mode | the **sweep YAML** in `sweeps/` | [`sweep_sets/SWEEPS.md`](sweep_sets/SWEEPS.md) |
| what a reported characteristic means, and its caveats | nothing — read it | [`sweep_sets/CHARACTERISTICS.md`](sweep_sets/CHARACTERISTICS.md) |

Precedence, highest first: **CLI flags → `run.yaml` → the sweep YAML.** A
range set in `run.yaml` *replaces* the one in the sweep file; anything
`run.yaml` does not mention passes through. The merged result is written to
`outputs/<set>/_resolved_sweeps/` and *that* is what gets solved — never edit
those.

There are **no built-in defaults**. A missing or misspelt `run.yaml` key is an
error naming the key, and every file in `sweeps/` needs an entry under
`sweeps:` even if it is only `run: false`.

### Running them

```bash
# just the front set, and the force solve after it
uv run python Working/run_all.py --sets front

# front, no figures and no animations, joints still reported, forces still solved
uv run python Working/run_all.py --sets front --no-plots --no-gifs

# rebuild the reports from the CSVs already on disk — the fastest loop by far
uv run python Working/run_all.py --report-only --no-forces

# two sweeps, with animations, nothing else
uv run python Working/run_all.py --sets front --only 09,10 --gifs 09,10 --no-forces

# the same set against a different car
uv run python Working/run_all.py --sets front --geometry Working/models/gen14/front.yaml

# a run.yaml that lives outside sweep_sets/<name>/
uv run python Working/run_all.py --config some/other/run.yaml
```

Sweep selectors accept the numeric prefix or the full stem: `--only 01,09` and
`--only 01_bump_parallel,09_steer_in_roll` are the same thing. A selector
applies to **every set being run**, so pair it with `--sets` when it only
makes sense for one of them.

Results land **beside the geometry they were run against**:
`models/<car>/outputs/<set>/` (CSVs, gifs) and `models/<car>/report/<set>/`
(`report.md`, plots, `joints.csv`, `summary.csv`).

---

## 4. Run the force solver

Solves the force at every suspension joint, for every load case, on the whole
vehicle. The output is a CSV grouped by part, meant to be used directly as the
load input for a per-part FEA run.

It is **static, at the neutral ride position**. No body roll, no
anti-dive/squat/lift, no spring or damper rate, no bump steer; springs and
dampers are rigid links. It is a load-path calculation, not a vehicle dynamics
model.

Front and rear solve **together** — you cannot find the front/rear load split
without knowing where the rear contact patch is — so the force stage is one
whole-vehicle solve regardless of which sweep sets ran.

### Running it

```bash
# everything, forces included — forces are on by default
uv run python Working/run_all.py

# just the forces, after editing forces.yaml or cases.csv
uv run python Working/run_all.py --no-sweeps

# skip them, when you are only iterating on kinematics
uv run python Working/run_all.py --no-forces
```

Two files are written into `forces/aurora/outputs/`: **`forces.csv`** (the
force at every joint, grouped by part, four columns each — `x, y, z, mag`) and
**`load_transfer.csv`** (each wheel's vertical load, per case).

The force solve is also its own installed command, and that is where its
inspection modes live — they print and stop, so they are not stages of a full
run:

```bash
# print the structural model — parts, joints, coaxial pairs, system size — and stop.
# RUN THIS FIRST ON ANY NEW MODEL: it prints the exact part and joint names
# forces.yaml refers to, so you never have to guess them.
uv run kinematics forces --config Working/forces/aurora/forces.yaml --describe

# per-part equilibrium residuals, and stop. Non-zero exit if a part fails to close.
uv run kinematics forces --config Working/forces/aurora/forces.yaml --check
```

Its other flags — `--front` / `--rear` / `--cases` / `--mass` / `--out` /
`--per-part-files` — are one-off overrides of what `forces.yaml` already says;
see [`forces/force.md`](forces/force.md).

### Changing what it does

| To change | Edit |
| --- | --- |
| the load cases | `forces/aurora/cases.csv` — one row per case, three accelerations in **g**: `bump` (total vertical factor, gravity included, > 0), `brake` (+1 = 1 g deceleration), `corner` (+1 = inertial force acts left, i.e. a right-hand turn) |
| mass, solver policy, the structural filter, output format | `forces/aurora/forces.yaml` — fully commented in place |

The keys in `forces.yaml` worth knowing: `moment_reference` (`centroid` is
better conditioned, `origin` is easier to hand-check), `pivot_axial` (how the
load along a coaxial pivot pair is split — `even`, or name a joint to give it
all of it and bracket the answer), `rack` (`grounded` only), `on_wheel_lift`
(`report` keeps a negative normal load and flags the case; those rows are
physically impossible and must not be used), and `structure:`
(`weld` / `attach` / `ground` / `ignore` — how the kinematic body graph becomes
a structural one). **Every key is required**, so `--dry-run` is a complete
configuration check.

**→ [`forces/force.md`](forces/force.md)** for the full derivation, the sign
conventions in detail, the output layout, every assumption, and the
limitations — four-wheel vehicles, inboard brakes, a floating rack and
`front_brake_bias` are all explicitly not handled.

---

## The command, in full

`Working/run_all.py` **discovers** the work on disk — every
`sweep_sets/*/run.yaml`, then every `forces/*/forces.yaml` — and runs each.
Adding a Gen14 sweep set or a second car's force configuration is a new folder
and nothing else; there is no list to update.

### What runs

| flag | effect |
| --- | --- |
| *(none)* | every sweep set, then every force solve |
| `--sets front,rear` | only these sweep sets, by folder name |
| `--config PATH` | one sweep set by path to its `run.yaml`, for a set outside `sweep_sets/<name>/`. Not with `--sets` |
| `--cars aurora` | only these force configurations, by folder name |
| `--forces-config PATH` | one force configuration by path. Not with `--cars` |
| `--no-sweeps` | skip the sweep sets |
| `--no-forces` | skip the force solve |

### Inside each sweep set

Overrides of that set's `run.yaml`, for this run only.

| flag | effect |
| --- | --- |
| `--only A,B` / `--skip A,B` | run only / all but these sweeps |
| `--plots A,B` / `--gifs A,B` | only these sweeps get a figure / an animation |
| `--no-plots` / `--no-gifs` / `--no-joints` | drop figures / animations / the bearing misalignment section |
| `--jobs N` | parallel solver processes |
| `--report-only` | rebuild the report from existing CSVs, solve nothing |
| `--solve-only` | solve and stop, no report |
| `--on-bad-solve off\|warn\|fail` | what to do about non-converged or high-residual steps |
| `--geometry PATH` | run the set against a different car † |
| `--sweeps-dir PATH` | an alternative directory of sweep YAMLs † |
| `--side left\|right` | which corner the per-corner rows report † |

† These describe **one** set, so they need `--sets` or `--config` to name
which. Running several sets against one geometry would put every result in the
same output folder; the script refuses rather than doing it.

### Other

| flag | effect |
| --- | --- |
| `--list` | print the sweep sets and force configurations found, then stop |
| `--dry-run` | validate every configuration and print every command, writing nothing. A complete check of `Working/` |

Stages run **independently**: the sets read different geometry files, so one
failing says nothing about the others. Every stage is attempted and the exit
code names everything that failed.

---

## Where everything is

```
Working/
  run_all.py         THE command — sweep sets, then forces
  README.md          this page

  models/            the cars — hardpoints, vehicle config, joint declarations
    MODELS.md          geometry + joints syntax reference
    aurora/
      front.yaml  rear.yaml  check.py
      outputs/<set>/   CSVs and gifs      | git-ignored,
      report/<set>/    report.md, plots   | reproducible from the inputs

  sweep_sets/        kinematic sweeps and their reports
    README.md          what each sweep is for, and why two are off
    RUNNING.md         run.yaml key reference, the flags, precedence
    SWEEPS.md          the sweep-authoring grammar
    CHARACTERISTICS.md every characteristic produced, with caveats
    runner.py          the sweep-set solver — a library, called by run_all.py
    susreport*.py  bearings.py    the reporters
    front/  rear/      a run.yaml plus sweeps/

  forces/            static joint-force solves
    force.md           the whole force workflow
    aurora/
      forces.yaml  cases.csv
      outputs/         forces.csv, load_transfer.csv — git-ignored
```

`sweep_sets/runner.py` is **not** a command. It holds the sweep-solving logic
that `run_all.py` imports, so that there is one place to type a flag and one
place for it to be read. A second entry point is a second thing to keep in
sync with the documentation, which is how the two disagree.

A sweep set and a force configuration each name their geometry **relative to
themselves**, so pointing either at a different car is a one-line edit and
adding a car is a new folder rather than a change to an existing one.

| I want to | Start at |
| --- | --- |
| Run everything | `uv run python Working/run_all.py` |
| Run one end of the car | `uv run python Working/run_all.py --sets front` |
| Change a hardpoint | `models/aurora/front.yaml` → [`models/MODELS.md`](models/MODELS.md) |
| Add a bearing to the misalignment table | the `joints:` block → [`models/MODELS.md` §6](models/MODELS.md#6-the-joints-block) |
| Change a sweep range or what it reports | `sweep_sets/<set>/run.yaml` → [`RUNNING.md`](sweep_sets/RUNNING.md) |
| Write a new kind of sweep | `sweep_sets/<set>/sweeps/` → [`SWEEPS.md`](sweep_sets/SWEEPS.md) |
| Understand what a characteristic means | [`CHARACTERISTICS.md`](sweep_sets/CHARACTERISTICS.md) |
| Add a load case | `forces/aurora/cases.csv` → [`force.md`](forces/force.md) |
| Inspect the force model's parts and joints | `uv run kinematics forces --config Working/forces/aurora/forces.yaml --describe` |
| Understand the solver itself | the repository root `README.md` |
