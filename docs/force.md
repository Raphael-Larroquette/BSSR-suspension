# Static suspension force solve

Solves the force at every suspension joint, for every load case, on a full
vehicle. Output is a CSV grouped by part, intended to be used directly as the
load input for a per-part FEA run.

The solve is **static and at the neutral ride position**. The suspension never
moves, so there is no body roll, no anti-dive/squat/lift, no spring or damper
rate, and no bump steer. Springs and dampers are rigid links of fixed length.
This is a load-path calculation, not a vehicle dynamics model.

---

## Quick start

```bash
kinematics forces --config models/aurora/forces.yaml --out forces.csv
```

`forces.yaml` names the two geometry files and the case file, so that one
command covers the whole vehicle. Anything in it can be overridden:

```bash
kinematics forces \
  --config models/aurora/forces.yaml \
  --front  models/aurora/front.yaml \
  --rear   models/aurora/rear.yaml \
  --cases  models/aurora/cases.csv \
  --out    forces.csv          # .csv, or .xlsx with the [xlsx] extra
```

| Flag | Meaning |
| --- | --- |
| `--config PATH` | Configuration file. Defaults to `./forces.yaml`. |
| `--front PATH` / `--rear PATH` | Override the geometry files. |
| `--cases PATH` | Override the load-case file. |
| `--mass FLOAT` | Override the vehicle mass in kg. |
| `--out PATH` | Output file, `.csv` or `.xlsx`. Required unless one of the three flags below is given. |
| `--per-part-files DIR` | Also write one flat CSV per part. |
| `--describe` | Print the structural model -- parts, joints, coaxial pairs, and the size of each subsystem -- and stop. |
| `--check` | Print per-part equilibrium residuals and stop. Exits non-zero if any part fails to close. |
| `--dry-run` | Validate every input, solve, and stop. |

Paths inside `forces.yaml` are resolved relative to that file, so a model
directory is self-contained.

**Run `--describe` first on any new model.** It prints the exact part and joint
names `forces.yaml` refers to, so you never have to guess them:

```
subsystem 'left' (front), loaded at 'Left Upright'
  part Left Lower Wishbone (4 joints)
  part Left Spring/Damper (two-force member)
  ...
  coaxial left_lower_wishbone_inboard_front / left_lower_wishbone_inboard_rear
      between 'Chassis' and 'Left Lower Wishbone': even
  system: 20 equations, 20 unknowns (2 constraint row(s))
```

**Front and rear run together, in one command.** The load distribution needs
the whole vehicle — you cannot find the front/rear split without knowing where
the rear contact patch is. The individual corner solves are then automatically
independent (see [Step 4](#step-4--build-the-body-graph)).

---

## Coordinate system, units, and signs

Everything follows the repo-wide ISO 8855 convention, unchanged from the rest
of the tool:

- **+X forward, +Y left, +Z up.** Left-side hardpoints have positive Y.
- Lengths in **mm**, forces in **N**, moments in **N·mm**.
- The origin is the front axle centreline at design ride height; the rear
  contact patch therefore sits at `x = -wheelbase`, which the solver checks.
- Centre-of-gravity height is measured from the **road plane**, which is where
  the contact patches actually are, not from `z = 0`. The two differ by a
  fraction of a millimetre on Aurora because the contact patch is constructed
  from the tyre radius and the axle position, and measuring from the road is
  what makes the closed-form transfer formulas reproduce the solved answer
  exactly.

A reported force is **the force acting on the named part, at that joint**,
expressed in the vehicle frame. That is what you apply in FEA, and it means
every part's block sums to zero — a check you can do in a spreadsheet.

---

## Inputs

### 1. Geometry files

Ordinary geometry YAML — the same files the sweep uses. The solver reads
hardpoints, elements, the vehicle configuration, and the derived wheel contact
centres straight from the design condition. **No sweep is required, and the
`joints:` block is not read at all.** That block exists only for bearing
misalignment reporting and has no effect here.

`cg_position` and `wheelbase` must be identical in both files; a mismatch is an
error naming both values.

### 2. `cases.csv`

Comment lines beginning with `#` are ignored. One header row, then one row per
case:

```csv
bump,brake,corner
2,1,1
2,1,-1
4,1,1
6,0,0
```

Each number is an acceleration expressed in **g**:

| Column | Symbol | Meaning |
| --- | --- | --- |
| `bump` | $A_z$ | **Total** vertical load factor, gravity included. `1` is static. Must be greater than zero. |
| `brake` | $A_x$ | `+1` = 1 g deceleration. Negative is acceleration/traction. |
| `corner` | $A_y$ | `+1` = the inertial force at the CG acts to the **left** (+Y), i.e. a right-hand turn. |

Worked example — `2,1,1` means twice static vertical load, 1 g of braking, and
1 g of cornering in a right-hand turn.

Signs in full, because this is the easiest place to get it backwards. For
`brake = +1`, the d'Alembert inertial force at the CG points **forward** (+X),
load transfers to the **front**, and the contact-patch force on the car points
**rearward** (−X). For `corner = +1`, the inertial force at the CG points
**left** (+Y), load transfers to the **left** wheels, and the contact-patch
force points **right** (−Y).

`bump` includes gravity, so a row like `0,0,1` is meaningless — zero vertical
load with a lateral demand. The solver rejects it and names the row.

### 3. `forces.yaml`

Mass, the structure filter, and every solver policy. Fully commented in the
shipped template. **Every key is required**; a missing or misspelt key is an
error naming it, so `--dry-run` is a complete configuration check.

---

## How it works

### Step 1 — assemble the vehicle

Load both geometry files, cross-check `cg_position` and `wheelbase`, and
collect the contact patches. Track width is **derived** from the front
`wheel_contact_centre` Y coordinates rather than authored, so there is one
source of truth. Aurora: three contact patches — front left, front right, and
one on the centreline at the rear.

### Step 2 — contact-patch normal loads

With three contact patches the vertical loads are **statically determinate**:
three unknowns, three equations. No roll-stiffness distribution is needed or
assumed. Writing $W = m g$ for the vehicle weight, and taking moments about the
origin with each patch at its own $(x_i, y_i, z_i)$:

$$\sum_i N_i = A_z W$$

$$\sum_i N_i \left( y_i - z_i \frac{A_y}{A_z} \right)
  = y_{cg} A_z W + z_{cg} A_y W$$

$$\sum_i N_i \left( x_i - z_i \frac{A_x}{A_z} \right)
  = x_{cg} A_z W + z_{cg} A_x W$$

The $z_i$ terms are there because a patch's horizontal force is a fixed
multiple of its own normal load and does not act at $z = 0$. Dropping them is a
0.4 % error on Aurora and grows with however far the contact-patch construction
lands from the origin.

With $h$ the centre-of-gravity height **above the road plane**, this
reproduces the classical load-transfer formulas exactly, to every digit:

$$\Delta W_x = \frac{h}{l} W A_x \qquad \Delta W_y = \frac{h}{t} W A_y$$

and picks up two things they cannot express. First, on a three-wheeler $t$ must
be the **front** track and the entire lateral transfer lands on the front pair —
a centreline rear wheel has no moment arm about X, so its normal load is
completely unaffected by cornering. Second, Aurora's CG is 39.844 mm right of
centre, so even the static left/right split is 0.2043 / 0.2922 rather than
50/50; $\Delta W_y = hWA_y/t$ assumes a centred CG and misses it.

**If a normal load comes out negative**, that wheel has lifted and the vehicle
is past its tip-over threshold. Under the default `on_wheel_lift: report` the
negative value is kept, the case is flagged in the output and in a terminal
warning, and every corner is still solved. This is deliberate: the loaded
corner gets a *higher* load this way than it would if the lifted wheel were
clamped to zero and the rest re-solved, so it is the conservative number for the
corner you are actually sizing. **The flagged corner's own numbers are
physically impossible and must not be used** — a negative normal load means the
tyre pulling down on the road.

### Step 3 — contact-patch horizontal forces

Horizontal force is distributed in proportion to normal load, which is the
same as assuming an equal friction coefficient at every tyre:

$$F_{ix} = -\frac{N_i}{\sum_k N_k} A_x W \qquad
  F_{iy} = -\frac{N_i}{\sum_k N_k} A_y W$$

This is **ideal brake bias by definition**. The `front_brake_bias: 0.7` in
`rear.yaml` is deliberately **not used** — see [Limitations](#limitations).

### Step 4 — build the body graph

Bodies come from `build_bodies()`, which groups elements by their declared
`body_group` and appends a `Chassis` ground body built from every fixed point.
Two bodies are jointed wherever they share a point. Both facts come from the
geometry alone.

The kinematic model contains bodies that are not separate structural parts, so
the `structure:` block filters it with four operations — `weld`, `attach`,
`ground`, `ignore`. The defaults handle Aurora with no overrides:

- `Axle` and `Wheel` come out as bodies sharing the axle points with the
  upright; physically they are one rigid assembly, so they are **welded** into
  it. Without this you get a fictitious joint and a singular system.
- On the rear, `Semi-Trailing Arm` and `Semi-Trailing Arm Carrier` are two
  bodies at the same anchor point — one weldment, welded together.
- `Steering Rack` is **grounded**, which is what `rack: grounded` means: the
  driver holds the wheel, so the rack cannot translate.

A weld group's **first entry names the merged part and must be present for the
group to apply**, so the rule written for a double wishbone is simply inert on
a trailing arm and vice versa. If two axles end up with a part of the same
name, the output qualifies both with their axle -- `Front Spring/Damper` and
`Rear Spring/Damper` -- and leaves every unambiguous name alone.

> **A note on names.** `Semi-Trailing Arm` is the generic label the
> `trailing_arm` topology gives its elements; it is not a claim about the
> geometry. On Aurora both pivots sit at the same X and differ only in Y, so
> the pivot axis is transverse and the part is a **pure trailing arm**.

Corners are then found generically: delete the ground bodies and take the
connected components of what is left. Aurora gives three independent
subsystems — front left, front right, rear. Add an anti-roll bar or set
`rack: floating` and the two front components merge into one larger system
automatically, with no special-casing anywhere.

After the filter, Aurora's parts are:

| Subsystem | Parts | Two-force members |
| --- | --- | --- |
| Front left / right | Upper Wishbone, Lower Wishbone, Upright | Track Rod, Spring/Damper |
| Rear | Rear Arm | Spring/Damper |

A body is treated as a **two-force member** when it has exactly two joints and
no external load. Its unknown collapses from three components to one axial
magnitude along the line joining its ends.

### Step 5 — assemble and solve

Each body that is not ground and not a two-force member contributes six
equations. With $s_{bj} = \pm 1$ carrying Newton's third law and $\mathbf c_b$
the body's moment reference:

$$\sum_j s_{bj}\,\mathbf F_j + \mathbf F^{\text{ext}}_b = \mathbf 0$$

$$\sum_j s_{bj}\,(\mathbf r_j - \mathbf c_b) \times \mathbf F_j
  + (\mathbf r^{\text{ext}} - \mathbf c_b) \times \mathbf F^{\text{ext}}_b
  = \mathbf 0$$

$\mathbf F^{\text{ext}}$ is non-zero only on the part carrying the wheel — the
upright at the front, the arm at the rear — where the contact-patch force acts
at `wheel_contact_centre`. The cross product is assembled as the skew-symmetric
matrix of $(\mathbf r_j - \mathbf c_b)$, and a two-force member's column is its
unit direction $\hat u$ rather than an identity block.

The result is $[A]\{x\} = \{B\}$, built as **M × N and then checked**, not
assumed square. If $M \neq N$, or the rank is short, the solver stops and names
the offending body. It never falls back to a least-squares pseudo-inverse: that
would silently return the minimum-norm answer to a badly posed model, and those
numbers would look perfectly reasonable in a CSV.

#### Coaxial pivot pairs

Two joints connecting the same pair of bodies are a redundancy that statics
cannot resolve. If $\hat u$ is the direction between them, then
$(\mathbf r_F - \mathbf r_R) \parallel \hat u$, so

$$\mathbf r_F \times \hat u \;=\; \mathbf r_R \times \hat u$$

and the two axial components enter *every* row — force and moment alike — only
as their sum. This is the classic locating-bearing / floating-bearing problem.
It affects both wishbones at the front and the trailing-arm pivots at the rear,
and it is found automatically by counting joints per body pair; nothing has to
be declared.

`pivot_axial` closes it. The default `even` adds one constraint row per pair,

$$\hat u \cdot \mathbf F_F - \hat u \cdot \mathbf F_R = 0$$

which is the best estimate for two identical bushings. Naming a joint instead
gives it the whole axial load and the other none, which bounds the answer.
Running `front` and `rear` in turn brackets what `even` splits.

#### Conditioning

`moment_reference: centroid` matters more than it looks. On the rear arm, whose
joints sit around 2000 mm from the global origin, moving the reference to the
body's own centroid takes the condition number from **6.5 × 10⁴ to 2.8 × 10²**.
All three options are mathematically equivalent given the force rows; `origin`
is kept because it is easier to check by hand.

---

## Output

One block per part, in the vehicle frame, matching the reference layout:

```
# kinematics forces, format 1 | frame: vehicle ISO 8855 (X fwd, Y left, Z up)
# units: N, N-mm | sign: force acting ON the named part AT that joint
# front: models/aurora/front.yaml sha256=a3f1... | rear: ... | cases: ... sha256=...
# mass: 294.0 kg | g: 9.80665 | pivot_axial: even | moment_reference: centroid
# rack: grounded | brake_torque_reaction: unsprung

PART:,Upper Wishbone,,,,,,,,,,,,
Case,,,,upper_wishbone_inboard_front,,,upper_wishbone_inboard_rear,,,upper_wishbone_outboard,,,flags
bump,brake,corner,side,x,y,z,x,y,z,x,y,z,
2,1,1,left,...
2,1,1,right,...
2,1,-1,left,...

PART:,Upright,,,,,,,,,,,,,,,
Case,,,,upper_wishbone_outboard,,,lower_wishbone_outboard,,,trackrod_outboard,,,wheel_contact_centre (applied),,,flags
bump,brake,corner,side,x,y,z,x,y,z,x,y,z,x,y,z,
...
```

Notes on the layout:

- **`side`** is a fourth case column rather than a separate block, so there is
  one block per part rather than two. With `corner ≠ 0` the two sides are
  genuinely different and both are needed.
- The part carrying the wheel gets a **`wheel_contact_centre (applied)`**
  column group. It is the external load, not a joint, and including it is what
  makes every part block sum to zero.
- A two-force member still gets full XYZ vectors at both ends — equal and
  opposite — because that is what you paste into FEA.
- **`flags`** carries per-case diagnostics, most importantly `WHEEL_LIFT`.
- `output.frame: part` mirrors Y for right-side parts, for mirrored CAD. The
  header always records which frame was used.

### Moments

Every joint in the current model is a pure force, so joint moments are
identically zero *by construction*. Under `output.moments: auto` (the default)
the `mx,my,mz` columns therefore never appear today. The decision is made per
**part block**, not per joint or per case, so a block's column set is stable
across a whole file. `always` freezes the schema at the cost of dead columns;
`never` would silently discard real results once a moment-carrying joint exists,
and should not be used.

**Absent moment columns mean the model assumed the moment away, not that the
real joint carries none.** A real bushing does carry moment. Adding that is a
modelling change, described under [Extending](#extending).

---

## Assumptions

Every one of these is a real limitation on how far you should trust the output.

**Vehicle and loading**

- Quasi-static equilibrium; no dynamic amplification factor is applied.
- The whole vehicle mass is a point mass at `cg_position`. No sprung/unsprung
  split, so unsprung inertia is not accounted for.
- Load factors are applied simultaneously as if independent.
- No aerodynamic load, no gyroscopic effects, no drivetrain reaction torque.

**Tyres**

- Point contact at `wheel_contact_centre`. No contact patch extent, no
  pneumatic trail, no self-aligning moment, no camber thrust.
- Horizontal force distributed by normal load, i.e. one friction coefficient
  for every tyre — perfect grip, ideal brake bias.
- No friction-ellipse interaction between longitudinal and lateral force: a
  case may demand more total grip than a real tyre could produce.

**Geometry and structure**

- Neutral ride height, zero steer, zero roll, pitch and heave. The geometry
  never moves, so no jacking, anti-dive/squat/lift, or bump-steer effects
  appear anywhere in the result.
- All links and the chassis are rigid; zero compliance everywhere.
- Springs and dampers are fixed-length two-force members.
- Every joint transmits force only, no moment.
- The steering rack is held (`rack: grounded`), so the front corners are
  independent.

---

## Diagnostics and errors

| Condition | Behaviour |
| --- | --- |
| `bump` ≤ 0 in a case row | Error naming the row. Zero vertical load has no meaningful solution. |
| Negative tyre normal load | Case flagged `WHEEL_LIFT`, terminal warning, solve continues (`on_wheel_lift: report`). |
| `cg_position` / `wheelbase` disagree between files | Error naming both values. |
| Rear contact patch not at `x = -wheelbase` | Error. Usually means the two files are not in a common frame. |
| System not square | Error naming the body and its joint count. |
| System rank-deficient | Error naming the coaxial pair and the `pivot_axial` key that would close it. |
| Per-body equilibrium residual over tolerance | Error. This should be impossible and indicates a bug. |
| `brake_torque_reaction: sprung`, or `rack: floating` | Error: not implemented, naming the reason. |
| Missing or misspelt `forces.yaml` key | Error naming the key. |

`--check` prints per-part $\sum \mathbf F$ and $\sum \mathbf M$ residuals plus
the whole-corner closure (the chassis-side joint forces must sum to the
contact-patch force) instead of writing output.

---

## Limitations

**Four-wheel vehicles are not supported for the normal-load step.** Step 2 is
determinate only because Aurora has three contact patches. With four, the
vertical distribution is indeterminate by one and needs a roll-stiffness split
between the axles — which requires spring and anti-roll rates this solver does
not model. The solver detects four patches and stops with an explanation rather
than guessing. Everything downstream of Step 2 is already general.

**Inboard brakes are not implemented.** `brake_torque_reaction` uses the same
vocabulary as the geometry file's `drive_torque_reaction`. `unsprung` is an
outboard brake: the caliper is on the upright and the disc on the hub, so the
brake torque is an internal couple inside the upright/hub assembly and the
linkage sees the contact-patch force applied at the ground. `sprung` is an
inboard brake, whose torque is reacted straight to the chassis, leaving the
upright to see the longitudinal force at **wheel-centre height** instead.

On Aurora, $r_{\text{tyre}} = 279.2$ mm, so at 1 g braking on a heavily loaded
front wheel the difference is of order 900 N·m — which across the 336 mm
between the ball joints is a fore-aft couple of roughly ±2900 N that
**reverses sign** between the two models. It is not a refinement. All Aurora
brakes are outboard, so only `unsprung` is implemented; `sprung` raises an
error naming the reason.

**A floating steering rack is not implemented.** `rack: floating` would chain
three two-force members — both track rods and the rack — through a single
joint, which the unknown catalogue cannot express, and would couple the two
front corners into one system. Only `grounded` is implemented.

**`front_brake_bias` is ignored.** Step 3 distributes longitudinal force by
normal load, which is ideal bias. The `front_brake_bias: 0.7` authored in
`rear.yaml` is not read. Honouring it would change the front/rear split of
longitudinal force and, through it, every wishbone load under braking.

**`driven_axle` is ignored.** A negative `brake` value is treated as
load-proportional traction at all wheels rather than being sent entirely to the
driven axle.

**A floating steering rack is not implemented.** `rack: floating` would chain
three two-force members -- both track rods and the rack -- through a single
joint, which the unknown catalogue cannot express, and would couple the two
front corners into one system. Only `grounded` is implemented.

**Anti-roll bars and heave links are not handled.** Neither is fitted to
Aurora. Adding one couples the two corners, which the connected-component
partitioning already handles, but the element itself needs a torsional force
model.

---

## Extending

**A new suspension topology** needs nothing here. Bodies and joints come from
`elements()`, so a topology that declares its elements correctly is solved
without changes to the force code. Check with `--describe` before trusting it.

**A moment-carrying joint** — a rocker as a true revolute, or a bushing with
rotational stiffness — is the one change that touches the solver core: the
joint's unknown grows from three force components to force plus moment. The
results type already carries an optional moment per joint and the writer
already knows how to emit it, so the change is confined to the unknown
catalogue and the matrix assembly.

**Four-wheel support** means replacing Step 2 with a roll-stiffness
distribution, and therefore giving the geometry a spring rate and a motion
ratio. Nothing else in the pipeline changes.

---

## Verification

The solve checks itself on every run: the assembled system must be square and
full rank, and the residual of every subsystem is compared against
`solve.tolerances.residual` before any number is reported.

`tests/test_forces.py` covers:

- **Load transfer**, against the closed forms $\Delta W_x = hWA_x/l$ and
  $\Delta W_y = hWA_y/t_f$, and against the rear normal load being untouched by
  cornering. Written this way deliberately: comparing against a formula rather
  than against the code's own output is what caught a sign error on the
  contact-patch height term during development.
- **An independent linkage solve.** The Aurora front-left corner, against a
  separately assembled 20x20 system, to nine significant figures.
- **Per-part equilibrium** across the whole shipped case set, and closure of
  the chassis reactions onto the contact-patch force.
- **Mirror symmetry.** The two front corners fed the same force, mirrored in
  Y, must produce mirrored joint loads. This catches sign errors nothing else
  will.
- **Policy invariance.** Switching `pivot_axial` between `even` and a named
  carrier changes only the component along that pivot axis; switching
  `moment_reference` changes nothing but the condition number.
- **Both regression fixes** that this feature required: the trailing arm
  carrying its own spring pickup, and an axle forwarding its corners' rigid
  attachments.
