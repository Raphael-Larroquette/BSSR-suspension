# Suspension Explorer — Blue Sky Solar Racing branch

A geometric constraint solver for suspension kinematics, plus a static joint-force
solver, wrapped in a one-command workflow for the Gen13 car.

You describe a car once, in a YAML geometry file. The tool then (a) solves it through
whatever ranges of motion you ask for and reports the resulting suspension
characteristics, (b) reports how much misalignment each declared bearing has to absorb,
and (c) solves the force at every joint for a set of load cases, in a form you can paste
straight into FEA.

This is a fork of [suspension-explorer-core](https://github.com/suspension-explorer/suspension-explorer-core)
(AGPL-3.0-only — see `LICENSE`). The solver is upstream's; `Working/` is ours.

> Results are only as good as the geometry you feed it. Validate anything that drives a
> design decision — the tool has no pass/fail on anything.

---

## 1. What is supported

"Exercised" = used on Aurora and cross-checked against SUSProg / hand calcs.
"Untested here" = implemented upstream, never run on one of our cars — assume nothing.

| Area | Supported | Status |
| --- | --- | --- |
| Double wishbone, direct-acting coilover | corner or mirrored two-corner axle | **Exercised** (Aurora front) |
| Trailing arm, centreline wheel | single corner, transverse pivot | **Exercised** (Aurora rear) |
| Steering | translating rack, or fixed toe link (`type: none`) | **Exercised** |
| Kinematic sweeps | bump, roll, steer, held-attitude, ramp, damper-driven | **Exercised** |
| Characteristics | camber, toe, caster, KPI, scrub, trail, track, ICs/swing arms, roll centre, motion ratio, anti-geometry, analytic gradients | **Exercised** |
| Bearing misalignment | per declared joint, incl. install offset and locked/free band | **Exercised** |
| Static joint forces | every joint, per load case, grouped by part | **Exercised** (3 contact patches only) |
| Output | CSV, Parquet, XLSX; plots and GIF/MP4 animations | **Exercised** (CSV, PNG, GIF) |
| Pushrod-rocker actuation, torsion bar, separate linear damper | double wishbone only | Untested here |
| U-bar / T-bar anti-roll, rocker-to-rocker heave link | requires pushrod-rocker axle | Untested here |
| MacPherson strut | corner or axle | Untested here |
| Outboard camber shims | double wishbone corners | Untested here |
| Explicitly asymmetric axles (authored `hardpoints.right`) | | Untested here |
| Sided (non-centreline) trailing arm | | Untested here |

---

## 2. Assumptions and hard limits

**The kinematic model assumes:**

- Rigid links, ideal joints, zero compliance anywhere (no bushing, chassis, tyre or
  component deflection).
- A rigid disc tyre at nominal radius — no loaded radius, contact patch extent,
  pneumatic trail, camber thrust or self-aligning moment.
- One axle at a time. A single axle cannot determine whole-vehicle pitch, yaw or
  longitudinal position, so those are set to zero rather than inferred.
- A straight, level road. No grade, bank or non-planar surface.
- Camber is chassis-relative. Road-relative wheel inclination is **not** exported.
- Sweeps are 1-D paths, not grids. Targets pair by index; there is no Cartesian product
  anywhere. A 2-D surface needs one run per attitude, stitched afterwards.
- A sweep drives exactly one target per degree of freedom at every step — every corner
  once, plus every actuator.

**The force solve additionally assumes:**

- Static, at neutral ride height, zero steer/roll/pitch. Springs and dampers are
  rigid fixed-length links. No spring rate, no damping, no bump steer, no anti-effects.
- Whole vehicle mass as a point mass at `cg_position`; no sprung/unsprung split.
- Exactly three contact patches.
- Horizontal force split by normal load — i.e. one friction coefficient everywhere and
  ideal brake bias.
- Every joint carries force only, no moment.

**Not possible today:**

| | |
| --- | --- |
| Dynamics, inertia, damping, transient response | not modelled at all |
| Stress, fatigue, packaging or interference checks | out of scope — that is what the force CSV feeds |
| Architectures other than double wishbone, MacPherson, trailing arm | rejected at load |
| Offset-axis MacPherson struts | clamp must lie within 1 mm of the LBJ→top-mount axis |
| Four-wheel force solve | vertical distribution is indeterminate without roll rates; the solver detects 4 patches and stops |
| Inboard brakes (`brake_torque_reaction: sprung`) | errors out |
| Floating steering rack (`rack: floating`) | errors out |
| Anti-roll bars / heave links in the force solve | no torsional force model yet |
| `front_brake_bias` and `driven_axle` in the force solve | authored but ignored |
| Arbitrary mechanism combinations | rejected at load, with the reason named |

---

## 3. Coordinate system and units

**ISO 8855: +X forward, +Y left, +Z up.** Left-side hardpoints have **positive Y**.

- **Origin:** front axle centreline, at design ride height, on the ground plane. The
  rear contact patch therefore sits at `x = -wheelbase`, which the force solve checks.
- **Lengths:** mm. `units: millimeters` is the only accepted value.
- **Angles:** degrees in files and output; radians internally.
- **Forces:** N. **Moments:** N·mm.
- **Tyre:** section width in mm, **rim diameter in inches** (the one non-metric input).
- **Wheel offset:** ET convention, **positive = inboard**, measured along the axle axis
  from the wheel centreline to the hub mounting face. Not a difference of Y coordinates.
- **CG height** in the force solve is measured from the **road plane**, not from `z = 0`.

Hardpoints describe the **design condition**. Fixed chassis points stay fixed; everything
else moves relative to them.

Two sign conventions to watch:

- `toe_angle` is our convention (**positive = toe-in**, side-folded). `steer_angle` is
  ISO vehicle-fixed. Use `steer_angle` when comparing against anything ISO-based.
- `scrub_radius` is the ISO **unsigned** distance and includes mechanical trail.
  SUSProg's scrub radius is our `scrub_signed` / `steering_axis_offset_ground`.

---

## 4. Installation

Written for someone who has never installed Python. If you already have a step, skip it —
nothing below breaks on a re-run.

### 4.1 Git

Git is what downloads the repository and tracks your changes.

- **Windows:** download from [git-scm.com/download/win](https://git-scm.com/download/win),
  run the installer, accept every default.
- **macOS:** `xcode-select --install`, or download from
  [git-scm.com/download/mac](https://git-scm.com/download/mac).
- **Linux:** `sudo apt install git` (or your distro's equivalent).

Check it worked. Open a terminal — **Windows: PowerShell** (Start menu → type
"PowerShell"); **macOS/Linux: Terminal** — and run:

```bash
git --version
```

Anything like `git version 2.4x.x` is fine.

### 4.2 Python 3.12 or newer

The solver needs Python 3.12+. You do **not** have to install it yourself — `uv`
(next step) will fetch the right version automatically if you don't have it. Check what
you have:

```bash
python --version
```

If that prints 3.12 or higher, you're done. If it prints something older, or errors, do
nothing — carry on to `uv` and it will handle it.

> If you use Anaconda, leave it alone. This project uses its own isolated environment and
> will not touch your conda installs.

### 4.3 uv

`uv` is the package manager. It creates the project's isolated environment and installs
every library into it, so nothing here can break your other Python work.

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Close and reopen your terminal**, then check:

```bash
uv --version
```

If the command is not found after reopening, the installer's folder isn't on your PATH —
on Windows that is `%USERPROFILE%\.local\bin`, on macOS/Linux `~/.local/bin`.

### 4.4 just

`just` is a command runner. It turns the multi-step setup below into `just setup`. It is
optional — every `just` recipe is in the `justfile` and can be typed out by hand — but
installing it is two minutes.

**Windows (PowerShell):**

```powershell
winget install --id Casey.Just --exact
```

**macOS:**

```bash
brew install just
```

**Linux:**

```bash
sudo apt install just     # or: cargo install just
```

Check:

```bash
just --version
```

### 4.5 Visual Studio Code (optional, recommended)

VS Code is the editor. You can use anything — the tool is driven from the terminal — but
VS Code is what the team uses and the repo ships its settings.

1. Download from [code.visualstudio.com](https://code.visualstudio.com) and install.
2. Open it, go to the Extensions panel (`Ctrl+Shift+X`), and install:
   - **Python** (Microsoft)
   - **YAML** (Red Hat) — catches indentation mistakes in geometry files as you type
3. VS Code has a built-in terminal (`Ctrl+`` `) — use it for every command below.

### 4.6 Clone the repository

Pick where it should live, `cd` there, and clone:

```bash
cd ~/Documents
git clone https://github.com/Raphael-Larroquette/BSSR-suspension.git
cd BSSR-suspension
```

On Windows, `~/Documents` works in PowerShell. Everything from here on is run **from the
repository root** — the folder containing `justfile` and `pyproject.toml`.

### 4.7 Install the dependencies

```bash
just setup
```

That is three commands in one: `uv venv` creates the isolated environment in `.venv/`,
`uv sync --all-extras --dev` installs every dependency (NumPy, SciPy, Pydantic, pandas,
PyYAML, pyarrow, typer, matplotlib, openpyxl, and the dev tools), and `uv pip install -e .`
installs the `kinematics` package itself in editable mode so your source edits take effect
immediately.

Without `just`, type those three lines yourself:

```bash
uv venv
uv sync --all-extras --dev
uv pip install -e .
```

Expect a minute or two the first time.

> You never activate the environment manually. Every command in this document starts with
> `uv run`, which runs it inside `.venv/` for you.

### 4.8 Check it works

```bash
uv run python Working/run_all.py --list
```

That prints the sweep sets and force configurations it found. Then validate the whole
configuration without solving anything:

```bash
uv run python Working/run_all.py --dry-run
```

If both are clean, you're installed. Optionally run the test suite (`just test`).

---

## 5. Quick start

**Everything you touch to *use* the tool is in `Working/`.** The solver itself lives in
`src/` and you should not need to open it.

```
Working/
  run_all.py              THE command
  models/<car>/           the car: hardpoints, config, joint declarations
    MODELS.md               geometry + joints syntax reference
  sweep_sets/<set>/       kinematic sweeps: one run.yaml, which is the whole set
    RUNNING.md              run.yaml keys, what each sweep drives, CLI flags
    SWEEPS.md               sweep-file grammar (for `file:` sweeps); the sweep catalogue
    CHARACTERISTICS.md      what every reported characteristic means
  forces/<car>/           static force solve: forces.yaml + cases.csv
    force.md                the force workflow
```

### 5.1 Run it

One command, from the repository root:

```bash
uv run python Working/run_all.py
```

That solves every enabled sweep in every sweep set, writes a CSV per sweep, renders the
requested plots and animations, builds `report.md` for each set, and then runs the static
force solve. **There is no second entry point.** `sweep_sets/runner.py` is a library that
`run_all.py` calls, not a command.

### 5.2 CLI overrides

Every flag below overrides `run.yaml` **for that invocation only**. `run.yaml` is the
only other place anything is configured — sweep files are generated from it.

**What runs**

| Flag | Effect |
| --- | --- |
| *(none)* | every sweep set, then every force solve |
| `--sets front,rear` | only these sweep sets, by folder name |
| `--config PATH` | one sweep set by path to its `run.yaml`. Not with `--sets` |
| `--cars aurora` | only these force configurations, by folder name |
| `--forces-config PATH` | one force configuration by path. Not with `--cars` |
| `--no-sweeps` | skip the sweeps |
| `--no-forces` | skip the force solve (it is on by default) |

**Inside each sweep set**

| Flag | Effect |
| --- | --- |
| `--only A,B` / `--skip A,B` | run only / all but these sweeps |
| `--plots A,B` / `--gifs A,B` | only these sweeps get a figure / an animation |
| `--no-plots` / `--no-gifs` / `--no-joints` | drop all figures / animations / the bearing section |
| `--jobs N` | parallel solver processes |
| `--report-only` | rebuild reports from the CSVs already on disk, solve nothing |
| `--solve-only` | solve and stop, no report |
| `--on-bad-solve off\|warn\|fail` | what to do about non-converged or high-residual steps |
| `--geometry PATH` † | run the set against a different car |
| `--side left\|right` † | which corner the per-corner rows report |

† describes **one** set, so it needs `--sets` or `--config` to say which.

**Other**

| Flag | Effect |
| --- | --- |
| `--list` | print the sweep sets and force configurations found, then stop |
| `--dry-run` | validate every configuration and print every command, writing nothing |

Sweep selectors take the numeric prefix or the full stem — `--only 01,09` and
`--only 01_bump_parallel,09_steer_in_roll` are the same. A selector applies to **every**
set being run, so pair it with `--sets`.

**Worked examples**

```bash
# the front set only, forces still solved after it
uv run python Working/run_all.py --sets front

# fastest loop: rebuild the reports from existing CSVs, solve nothing
uv run python Working/run_all.py --report-only --no-forces

# two sweeps with animations, nothing else
uv run python Working/run_all.py --sets front --only 09,10 --gifs 09,10 --no-forces

# numbers only, no figures
uv run python Working/run_all.py --no-plots --no-gifs

# forces only, after editing forces.yaml or cases.csv
uv run python Working/run_all.py --no-sweeps

# the same sweep set against a different car
uv run python Working/run_all.py --sets front --geometry Working/models/gen14/front.yaml
```

### 5.3 Where to read the results

Results land **beside the geometry they were run against**, never in your current
directory:

| Path | Contents |
| --- | --- |
| `Working/models/<car>/report/<set>/report.md` | **start here** — every characteristic, at design / min / max / range, plus the bearing misalignment table |
| `Working/models/<car>/report/<set>/` | the plots, `summary.csv`, `joints.csv` |
| `Working/models/<car>/outputs/<set>/` | one raw CSV per sweep, and the animations |
| `Working/models/<car>/outputs/<set>/_resolved_sweeps/` | the generated sweep files, i.e. exactly what was solved — read, never edit |
| `Working/forces/<car>/outputs/forces.csv` | force at every joint, grouped by part — the FEA input |
| `Working/forces/<car>/outputs/load_transfer.csv` | each wheel's vertical load, per case |

All of it is git-ignored and reproducible from the inputs.

To understand a number in `report.md`, go to
[`Working/sweep_sets/CHARACTERISTICS.md`](Working/sweep_sets/CHARACTERISTICS.md) — it is
the definition list, including the convention traps to check before you diff against
SUSProg.

### 5.4 Change something on an existing car

| To change | Edit | Reference |
| --- | --- | --- |
| a hardpoint, the architecture, the tyre, the CG | `Working/models/<car>/front.yaml` or `rear.yaml` | [`MODELS.md`](Working/models/MODELS.md) |
| which bearings get a misalignment number | the `joints:` block of that same file | [`MODELS.md` §5](Working/models/MODELS.md) |
| anything about a sweep — what it drives, its ranges and step count, whether it runs, which channels it reports or plots | `Working/sweep_sets/<set>/run.yaml` | [`RUNNING.md`](Working/sweep_sets/RUNNING.md) |
| a sweep the `travel`/`damper`/`rack` vocabulary can't express | a hand-written sweep YAML, named with `file:` | [`SWEEPS.md`](Working/sweep_sets/SWEEPS.md) |
| load cases | `Working/forces/<car>/cases.csv` | [`force.md`](Working/forces/force.md) |
| mass, solver policy, structural filter | `Working/forces/<car>/forces.yaml` | [`force.md`](Working/forces/force.md) |

Tuning the `joints:` block never needs a re-solve — the sweeps export the
axis-independent relative rotation, so `--report-only --no-forces` is the loop.

### 5.5 Set up a new car or a new geometry

A car is a folder. Nothing is registered anywhere — `run_all.py` discovers
`sweep_sets/*/run.yaml` and `forces/*/forces.yaml` on disk.

1. **Copy the geometry.** `cp -r Working/models/aurora Working/models/gen13` and edit
   `front.yaml` / `rear.yaml`. Point names are fixed vocabulary and unknown keys are an
   error, so a typo names itself. See [`MODELS.md`](Working/models/MODELS.md).

2. **Check it before spending CPU:**

   ```bash
   uv run python Working/models/gen13/check.py Working/models/gen13/front.yaml
   uv run kinematics visualize --geometry Working/models/gen13/front.yaml --output front.png
   ```

   The first says whether it loads and builds. The second draws the design condition and
   reports whether every derived wheel contact centre lands on the reconstructed road
   plane. **Fix that before reading any characteristic** — every road-plane metric is
   built on it.

3. **Point a sweep set at it.** Either edit `geometry:` in the set's `run.yaml`, or run
   it once with an override:

   ```bash
   uv run python Working/run_all.py --sets front --geometry Working/models/gen13/front.yaml
   ```

   Results follow the geometry, so there is no collision with Aurora's.

4. **New sweep set:** copy `Working/sweep_sets/front/run.yaml` to a new folder, set
   `name:` and `geometry:`, and pick the reporter — `susreport` for a two-wheel axle,
   `susreport_rear` for a single corner. Then write the sweeps you want under `sweeps:`;
   each needs `steps` plus a range for every corner and every actuator. That one file is
   the whole set. Keys: [`RUNNING.md`](Working/sweep_sets/RUNNING.md).

5. **New force configuration:** copy `Working/forces/aurora/` to `Working/forces/gen13/`,
   point `geometry.front` / `geometry.rear` at the new model, set the mass, and edit
   `cases.csv`. Then run:

   ```bash
   uv run kinematics forces --config Working/forces/gen13/forces.yaml --describe
   ```

   `--describe` prints the exact part and joint names the config refers to — run it first
   on any new model so you never have to guess them. `--check` prints per-part
   equilibrium residuals. Details: [`force.md`](Working/forces/force.md).

6. **Validate the lot** without solving:

   ```bash
   uv run python Working/run_all.py --dry-run
   ```
