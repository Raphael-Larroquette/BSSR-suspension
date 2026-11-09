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
| Characteristics | camber, road camber, toe, caster, KPI, scrub, trail, track, ICs/swing arms, roll centre, motion ratio, anti-geometry, analytic gradients | **Exercised** |
| Bearing misalignment | per declared joint, incl. install offset and locked/free band | **Exercised** |
| Static joint forces | every joint per load case, grouped by part, plus chassis reactions | **Exercised** (3 contact patches only) |
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
- `camber` is chassis-relative (ISO 8855 §7.1.17, about the vehicle X axis). `road_camber`
  is road-relative: ISO §7.1.16 inclination angle, measured about the tyre X axis so steer
  does not leak into it, but **signed like camber** (negative = top inboard on both sides)
  rather than ISO's unmirrored right-hand sign: `road_camber = -side_sign × inclination`.
  The road is the plane tangent to both wheels, so in roll it tilts against the fixed
  chassis; that tilt is a kinematic quantity, not body roll.
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
PyYAML, pyarrow, typer, matplotlib, psutil, openpyxl, and the dev tools, plus
`imageio-ffmpeg`, which downloads the **ffmpeg** program the animations are written with,
so you never install ffmpeg yourself), and `uv pip install -e .`
installs the `kinematics` package itself in editable mode so your source edits take effect
immediately.

Without `just`, type those three lines yourself:

```bash
uv venv
uv sync --all-extras --dev
uv pip install -e .
```

Expect a minute or two the first time.

> Already set up from before October 2026? Run `uv sync --all-extras --dev` once to pick up
> the two newer dependencies (`imageio-ffmpeg`, `psutil`). `uv run` also does this by
> itself the first time it notices `pyproject.toml` changed.

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

If both are clean (the dry run exits 0), you're installed. Optionally run the test suite (`just test`).

---

## 5. Quick start

Everything you touch to *use* the tool is in `Working/`; the solver is in `src/`.

```bash
uv run python Working/run_all.py                    # Aurora: every sweep set, then forces
uv run python Working/run_all.py --model <name>     # another model in Working/models/
uv run python Working/run_all.py --dry-run          # validate everything, solve nothing
uv run python Working/check.py <name>               # is this model folder complete and does it build?
```

Results land in the model folder: start at `Working/models/<model>/report/<set>/report.md`.

```
Working/
  run_all.py            the one command
  check.py              model-folder check (also run by --dry-run)
  cases.csv             load cases shared by every model's force solve
  models/<model>/       front.yaml, rear.yaml, forces.yaml (+ results, git-ignored)
  models/opt_<stamp>/   one optimizer run: its Pareto CSV, and exported candidates
  sweep_sets/<set>/     run.yaml: the whole sweep set
  <optimizer>.py        optimizer scripts; opt/ is their library
```

| to | read |
| --- | --- |
| set up a new car | [`docs/guides/new-model.md`](docs/guides/new-model.md) |
| find and read results | [`docs/guides/results.md`](docs/guides/results.md) |
| run the optimizer | [`docs/guides/optimizer.md`](docs/guides/optimizer.md) |
| write a geometry file | [`docs/reference/geometry.md`](docs/reference/geometry.md) |
| configure sweeps, CLI flags | [`docs/reference/sweeps.md`](docs/reference/sweeps.md) |
| understand a reported number | [`docs/reference/characteristics.md`](docs/reference/characteristics.md) |
| configure or read the force solve | [`docs/reference/forces.md`](docs/reference/forces.md) |
