# Static joint-force solve

Solves the force at every suspension joint, for every load case, on the whole vehicle.
Output is a CSV grouped by part, meant to be used directly as the load input for a
per-part FEA run.

**Static, at the neutral ride position.** The suspension never moves: no body roll, no
anti-dive/squat/lift, no spring or damper rate, no bump steer. Springs and dampers are
rigid links of fixed length. This is a load-path calculation, not a vehicle dynamics model.

Front and rear solve **together** — you cannot find the front/rear split without knowing
where the rear contact patch is.

---

## Running it

```bash
uv run python Working/run_all.py --no-sweeps          # forces only
uv run kinematics forces --config Working/forces/aurora/forces.yaml
```

`run_all.py` runs this as its last stage after the sweeps, because both read the same
geometry — a hardpoint edit invalidates both.

Two files are written to `<config dir>/outputs/`: **`forces.csv`** (force at every joint,
grouped by part) and **`load_transfer.csv`** (each wheel's vertical load, per case). Both
are git-ignored.

| Flag | Meaning |
| --- | --- |
| `--config PATH` | configuration file; defaults to `./forces.yaml` |
| `--front PATH` / `--rear PATH` | override the geometry files |
| `--cases PATH` | override the load-case file |
| `--mass FLOAT` | override the vehicle mass, kg |
| `--out PATH` | output file, `.csv` or `.xlsx` |
| `--per-part-files DIR` | also write one flat CSV per part |
| `--describe` | print the structural model — parts, joints, coaxial pairs, system size — and stop |
| `--check` | print per-part equilibrium residuals and stop; non-zero exit if a part fails to close |
| `--dry-run` | validate every input, solve, write nothing |

Paths inside `forces.yaml` resolve relative to that file, so a model directory is
self-contained.

**Run `--describe` first on any new model.** It prints the exact part and joint names
`forces.yaml` refers to:

```
subsystem 'left' (front), loaded at 'Left Upright'
  part Left Lower Wishbone (4 joints)
  part Left Spring/Damper (two-force member)
  coaxial left_lower_wishbone_inboard_front / left_lower_wishbone_inboard_rear
      between 'Chassis' and 'Left Lower Wishbone': even
  system: 20 equations, 20 unknowns (2 constraint row(s))
```

---

## Inputs

### Geometry files

The same YAML the sweeps use. The solver reads hardpoints, elements, vehicle configuration
and the derived contact centres from the design condition. **No sweep is required, and the
`joints:` block is not read at all.** `cg_position` and `wheelbase` must be identical in
both files.

### `cases.csv`

`#` comment lines ignored. One header row, then one row per case:

```csv
bump,brake,corner
2,1,1
2,1,-1
4,1,1
6,0,0
```

Each number is an acceleration in **g**:

| Column | Meaning |
| --- | --- |
| `bump` | **total** vertical load factor, gravity included. `1` is static. Must be > 0 |
| `brake` | `+1` = 1 g deceleration. Negative is acceleration/traction |
| `corner` | `+1` = inertial force at the CG acts **left** (+Y), i.e. a right-hand turn |

Signs in full: for `brake = +1` the d'Alembert force at the CG points **forward** (+X),
load transfers **forward**, and the contact-patch force on the car points **rearward**
(−X). For `corner = +1` the CG force points **left** (+Y), load transfers to the **left**
wheels, and the patch force points **right** (−Y).

`bump` includes gravity, so `0,0,1` is meaningless and is rejected by row.

### `forces.yaml`

Mass, structure filter, and every solver policy. **Every key is required**, so `--dry-run`
is a complete configuration check.

| Key | Values |
| --- | --- |
| `vehicle.mass`, `vehicle.g` | kg, m/s² |
| `geometry.front` / `.rear` | paths, relative to this file |
| `cases` | path to the case CSV |
| `solve.moment_reference` | `centroid` \| `origin` \| `{x,y,z}` — all mathematically equivalent; `centroid` is far better conditioned, `origin` is easier to hand-check |
| `solve.pivot_axial.default` | `even`, or a bare point name that takes the whole axial load |
| `solve.pivot_axial.overrides` | keyed by part name, side-agnostic point name |
| `solve.rack` | `grounded` only (`floating` not implemented) |
| `solve.brake_torque_reaction` | `unsprung` only (`sprung` = inboard brake, not implemented) |
| `solve.on_wheel_lift` | `report` (keep the negative load, flag the case) \| `fail` |
| `solve.tolerances.rank` | relative tolerance for the rank check |
| `solve.tolerances.residual` | per-part equilibrium residual, relative to the largest force on that part |
| `structure.weld` | merge parts into one; the **first entry names the merged part and must be present** for the group to apply |
| `structure.attach` | fold a loose point into the part carrying all its anchors |
| `structure.ground` | treat as chassis: no equations |
| `structure.ignore` | drop entirely |
| `output.frame` | `vehicle` (ISO 8855) \| `part` (Y mirrored for right-side parts, for mirrored CAD) |
| `output.moments` | `auto` \| `always` \| `never` |
| `output.per_part_files` | bool |

---

## How it works

**1 — Assemble the vehicle.** Load both geometry files, cross-check `cg_position` and
`wheelbase`, collect the contact patches. Track width is **derived** from the front
`wheel_contact_centre` Y coordinates, not authored. Aurora: three patches — front left,
front right, and one on the centreline at the rear.

**2 — Contact-patch normal loads.** With three patches the vertical loads are statically
determinate — three unknowns, three equations, no roll-stiffness split needed. With
$W = mg$ and each patch at $(x_i, y_i, z_i)$:

$$\sum_i N_i = A_z W$$
$$\sum_i N_i \left( y_i - z_i \tfrac{A_y}{A_z} \right) = y_{cg} A_z W + z_{cg} A_y W$$
$$\sum_i N_i \left( x_i - z_i \tfrac{A_x}{A_z} \right) = x_{cg} A_z W + z_{cg} A_x W$$

The $z_i$ terms are there because a patch's horizontal force is a fixed multiple of its own
normal load and does not act at $z = 0$; dropping them is a 0.4% error on Aurora.

With $h$ the CG height **above the road plane** this reproduces
$\Delta W_x = hWA_x/l$ and $\Delta W_y = hWA_y/t$ exactly, and picks up two things they
cannot express: on a three-wheeler $t$ must be the **front** track and the entire lateral
transfer lands on the front pair (a centreline rear wheel has no moment arm about X); and
Aurora's CG is 39.844 mm off centre, so even the static left/right split is not 50/50.

**If a normal load comes out negative** that wheel has lifted and the vehicle is past
tip-over. Under `on_wheel_lift: report` the value is kept, the case is flagged, and every
corner is still solved — the loaded corner gets a *higher* load this way, so it is the
conservative number for the corner you are sizing. **The flagged corner's own numbers are
physically impossible and must not be used.**

**3 — Contact-patch horizontal forces.** Distributed in proportion to normal load, i.e.
equal friction coefficient everywhere:

$$F_{ix} = -\tfrac{N_i}{\sum_k N_k} A_x W \qquad F_{iy} = -\tfrac{N_i}{\sum_k N_k} A_y W$$

This is **ideal brake bias by definition**; `front_brake_bias` is deliberately not used.

**4 — Build the body graph.** Bodies come from `build_bodies()`, grouped by declared
`body_group`, plus a `Chassis` ground body from every fixed point. Two bodies are jointed
wherever they share a point. The `structure:` block then filters the kinematic model into a
structural one. Aurora's defaults need no overrides:

- `Axle` and `Wheel` are **welded** into the upright — physically one rigid assembly.
  Without this you get a fictitious joint and a singular system.
- Rear `Semi-Trailing Arm` and `Semi-Trailing Arm Carrier` are one weldment, welded.
- `Steering Rack` is **grounded** — the driver holds the wheel.

Corners are then found generically: delete the ground bodies, take the connected
components. Aurora gives three independent subsystems. Add an ARB or set `rack: floating`
and the two front components merge automatically, with no special-casing.

| Subsystem | Parts | Two-force members |
| --- | --- | --- |
| Front left / right | Upper Wishbone, Lower Wishbone, Upright | Track Rod, Spring/Damper |
| Rear | Rear Arm | Spring/Damper |

A body with exactly two joints and no external load is a **two-force member**: its unknown
collapses from three components to one axial magnitude.

> `Semi-Trailing Arm` is the generic label the `trailing_arm` topology gives its elements,
> not a claim about the geometry. On Aurora both pivots share an X, so the part is a pure
> trailing arm.

**5 — Assemble and solve.** Each non-ground, non-two-force body contributes six equations,
with $s_{bj} = \pm 1$ carrying Newton's third law and $\mathbf c_b$ the moment reference:

$$\sum_j s_{bj}\,\mathbf F_j + \mathbf F^{\text{ext}}_b = \mathbf 0$$
$$\sum_j s_{bj}\,(\mathbf r_j - \mathbf c_b) \times \mathbf F_j + (\mathbf r^{\text{ext}} - \mathbf c_b) \times \mathbf F^{\text{ext}}_b = \mathbf 0$$

$\mathbf F^{\text{ext}}$ is non-zero only on the part carrying the wheel, where the
contact-patch force acts at `wheel_contact_centre`. The system is built **M × N and then
checked**, not assumed square: if $M \neq N$ or the rank is short it stops and names the
body. It never falls back to a pseudo-inverse.

**Coaxial pivot pairs.** Two joints connecting the same pair of bodies are a redundancy
statics cannot resolve: with $\hat u$ the direction between them,
$\mathbf r_F \times \hat u = \mathbf r_R \times \hat u$, so the two axial components enter
every row only as their sum. Found automatically by counting joints per body pair; affects
both front wishbones and the rear trailing-arm pivots. `pivot_axial: even` adds one
constraint row, $\hat u \cdot \mathbf F_F - \hat u \cdot \mathbf F_R = 0$ — the best
estimate for two identical bushings. Naming a joint instead gives it the whole axial load;
running `front` then `rear` brackets what `even` splits.

**Conditioning.** On the rear arm, whose joints sit ~2000 mm from the origin,
`moment_reference: centroid` takes the condition number from 6.5 × 10⁴ to 2.8 × 10².

---

## Output

### `forces.csv`

One block per part, in the vehicle frame:

```
# kinematics forces, format 1 | frame: vehicle ISO 8855 (X fwd, Y left, Z up)
# units: N, N-mm | sign: force acting ON the named part AT that joint
# front: .../front.yaml sha256=a3f1... | rear: ... | cases: ... sha256=...
# mass: 294.0 kg | g: 9.80665 | pivot_axial: even | moment_reference: centroid
# rack: grounded | brake_torque_reaction: unsprung

PART:,Upper Wishbone
Case,,,,upper_wishbone_inboard_front,,,,upper_wishbone_inboard_rear,,,,upper_wishbone_outboard,,,,flags
bump,brake,corner,side,x,y,z,mag,x,y,z,mag,x,y,z,mag,
2,1,1,left,...
```

- A reported force is **the force acting on the named part, at that joint** — what you
  apply in FEA. Every part's block therefore sums to zero, which you can check in a
  spreadsheet.
- Each joint is **four columns**: `x, y, z, mag`. The resultant is written out so finding
  the worst case is a sort, not a recalculation.
- **`side`** is a fourth case column rather than a separate block, so there is one block
  per part.
- The part carrying the wheel gets a **`wheel_contact_centre (applied)`** column group —
  the external load, not a joint. Including it is what makes the block sum to zero.
- A two-force member still gets full XYZ at both ends, equal and opposite.
- **`flags`** carries per-case diagnostics, most importantly `WHEEL_LIFT`.

**Moments.** Every joint in the current model is a pure force, so joint moments are zero
by construction and under `output.moments: auto` the `mx,my,mz` columns never appear. The
decision is made per **part block**, so a block's column set is stable across a file.
**Absent moment columns mean the model assumed the moment away, not that the real joint
carries none** — a real bushing does carry moment. `never` would silently discard real
results once a moment-carrying joint exists; do not use it.

### `load_transfer.csv`

One row per wheel per case:

```
bump,brake,corner,wheel,normal_load_N,effective_mass_kg,percent_of_case,percent_of_static_weight,transfer_from_baseline_N,flags
2,1,1,front_left,2404.010,245.1408,41.6906,83.3812,1225.731,
```

| Column | Meaning |
| --- | --- |
| `normal_load_N` | vertical force the road applies to that tyre |
| `effective_mass_kg` | that force ÷ g |
| `percent_of_case` | share of **this case's** total vertical load; sums to 100 |
| `percent_of_static_weight` | share of `mg`; sums to 100 × `bump` |
| `transfer_from_baseline_N` | load that braking and cornering moved onto this wheel |

Two share columns because "percent of the vehicle" is ambiguous once `bump` ≠ 1: at
`bump: 2` a wheel can be at 41.7% of what is on the ground *and* 83.4% of static weight.

**The baseline is the same case with `brake` and `corner` zeroed**, not 1 g static — so
`6,0,0` correctly reads zero across the board and the transfer column sums to zero.

`normal_load_N` is the same number as the `wheel_contact_centre (applied)` z component in
`forces.csv`; the two files are two views of one solve.

---

## Assumptions

**Vehicle and loading**

- Quasi-static equilibrium; no dynamic amplification factor.
- Whole vehicle mass as a point mass at `cg_position`; no sprung/unsprung split, so
  unsprung inertia is not accounted for.
- Load factors applied simultaneously as if independent.
- No aerodynamic load, gyroscopic effects, or drivetrain reaction torque.

**Tyres**

- Point contact at `wheel_contact_centre`. No patch extent, pneumatic trail, self-aligning
  moment or camber thrust.
- One friction coefficient for every tyre — perfect grip, ideal brake bias.
- No friction-ellipse interaction: a case may demand more total grip than a real tyre could
  produce.

**Geometry and structure**

- Neutral ride height, zero steer, roll, pitch and heave.
- All links and the chassis rigid; zero compliance.
- Springs and dampers are fixed-length two-force members.
- Every joint transmits force only, no moment.
- The rack is held (`rack: grounded`), so the front corners are independent.

---

## Diagnostics and errors

| Condition | Behaviour |
| --- | --- |
| `bump` ≤ 0 in a case row | error naming the row |
| negative tyre normal load | case flagged `WHEEL_LIFT`, warning, solve continues |
| `cg_position` / `wheelbase` disagree between files | error naming both values |
| rear contact patch not at `x = -wheelbase` | error — usually the two files are not in a common frame |
| system not square | error naming the body and its joint count |
| system rank-deficient | error naming the coaxial pair and the `pivot_axial` key that closes it |
| per-body residual over tolerance | error; should be impossible, indicates a bug |
| `brake_torque_reaction: sprung`, `rack: floating` | error: not implemented |
| missing or misspelt `forces.yaml` key | error naming the key |

`--check` prints per-part $\sum \mathbf F$ and $\sum \mathbf M$ residuals plus whole-corner
closure instead of writing output.

---

## Limitations

**Four-wheel vehicles are not supported for the normal-load step.** Step 2 is determinate
only with three patches; with four the vertical distribution is indeterminate by one and
needs a roll-stiffness split, which requires spring and ARB rates this solver does not
model. It detects four patches and stops. Everything downstream of step 2 is already
general.

**Inboard brakes are not implemented.** `unsprung` is an outboard brake — the caliper is on
the upright, so the brake torque is an internal couple and the linkage sees the patch force
at the ground. `sprung` would leave the upright seeing the longitudinal force at
**wheel-centre height**. On Aurora $r_{tyre} = 279.2$ mm, so at 1 g braking on a loaded
front wheel the difference is ≈900 N·m, which across the 336 mm between the ball joints is
a fore-aft couple of roughly ±2900 N that **reverses sign** between the two models. Not a
refinement.

**A floating steering rack is not implemented.** It would chain three two-force members
through a single joint, which the unknown catalogue cannot express, and would couple the
two front corners.

**`front_brake_bias` is ignored.** Step 3 distributes longitudinal force by normal load.
Honouring the authored 0.7 would change the front/rear split and every wishbone load under
braking.

**`driven_axle` is ignored.** A negative `brake` is treated as load-proportional traction
at all wheels rather than sent to the driven axle.

**Anti-roll bars and heave links are not handled.** The connected-component partitioning
already copes with the coupling; the element itself needs a torsional force model.

---

## Extending

- **A new suspension topology** needs nothing here — bodies and joints come from
  `elements()`. Check with `--describe`.
- **A moment-carrying joint** (a true revolute rocker, or a bushing with rotational
  stiffness) is the one change touching the solver core: the joint's unknown grows from
  three force components to force plus moment. The results type and the writer already
  handle it, so the change is confined to the unknown catalogue and matrix assembly.
- **Four-wheel support** means replacing step 2 with a roll-stiffness distribution, and
  therefore giving the geometry a spring rate and a motion ratio.

## Verification

Every run checks itself: the assembled system must be square and full rank, and every
subsystem's residual is compared against `solve.tolerances.residual` before any number is
reported.

`tests/test_forces.py` covers load transfer against the closed forms; an independently
assembled 20×20 Aurora front-left solve to nine significant figures; per-part equilibrium
and chassis-reaction closure across the whole case set; mirror symmetry between the two
front corners; and policy invariance (`pivot_axial` changes only the component along that
pivot axis, `moment_reference` changes nothing but the condition number).
