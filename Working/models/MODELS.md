# Model files — geometry and joints

A model file *is* the car. It holds the hardpoints, the architecture, the
vehicle configuration, and — optionally — the bearing joints you want
misalignment reported for. Both workflows read it: a sweep set solves it
through its range of motion, and the force solve loads it at the neutral
position. There is one copy, so a hardpoint edit reaches both.

```
Working/models/
  aurora/
    front.yaml     an AXLE  : two mirrored double-wishbone corners
    rear.yaml      a CORNER : one centreline trailing arm
```

One folder per car. Results land beside it (`outputs/`, `report/`) and are
git-ignored — everything in them is reproducible from these files.

This document is the syntax reference. For what the numbers *mean* once they
come out, see `../sweep_sets/CHARACTERISTICS.md`.

**Contents**

1. [Coordinates, units, signs](#1-coordinates-units-signs)
2. [The two file shapes](#2-the-two-file-shapes)
3. [Top-level keys](#3-top-level-keys)
4. [Configuration blocks](#4-configuration-blocks)
5. [Hardpoints](#5-hardpoints)
6. [The `joints:` block](#6-the-joints-block)
7. [Checking a file](#7-checking-a-file)

---

## 1. Coordinates, units, signs

ISO 8855, everywhere in the tool:

- **+X forward, +Y left, +Z up.** Left-side hardpoints have **positive Y**.
- Origin: the **front axle centreline** at design ride height, on the ground
  plane. So the rear contact patch sits at `x = -wheelbase`, which the force
  solve checks and rejects if the two files are not in a common frame.
- Lengths in **mm**. `units: millimeters` is the only accepted value.
- Angles in **degrees** in files and output, radians internally.
- Tyre section width in **mm**, rim diameter in **inches**.
- Wheel offset follows ET: **positive is inboard**, measured along the axle
  axis from the wheel centreline to the hub mounting face. It is not the
  difference between two Y coordinates unless the axle happens to be
  transverse.

Hardpoints describe the **design condition**. Fixed chassis points stay fixed;
everything else moves relative to them.

---

## 2. The two file shapes

`scope:` decides which set of keys the file takes, and it is the single most
common source of a confusing schema error.

| | `scope: axle` | `scope: corner` |
| --- | --- | --- |
| models | two corners, composed | one corner |
| vehicle data | `vehicle_config:` | inside `config:` |
| axle data | `axle_config:` | inside `config:` |
| mechanisms | inside `axle_config:` | **top level** (`spring:`, `actuation:`) |
| hardpoints | `hardpoints.left` / `.right` / `.center` | `hardpoints:` flat |
| `side:` | not used | required (defaults `left`) |

`corner` is the default, so a corner file may omit `scope:` — `rear.yaml`
does. An axle file must say `scope: axle` explicitly.

A **corner** file is not a lesser axle file. A single corner has no track, no
roll, no roll centre and no Ackermann, so those characteristics are not
produced at all; in exchange it produces the side-view family (SVIC, SVSA,
anti-squat) that parallel wishbones cannot. That is also why the two are
reported by different modules — see `../sweep_sets/RUNNING.md`.

**`side:` on a corner file** is `left` or, for a wheel on the vehicle
centreline, `center`. The loader **rejects `right`**: a right corner is the
mirror of a left one and adds nothing on its own. If a sided wheel faces the
other way, negate every `y` in the file. `center` is accepted only by
architectures that support a centreline wheel (today, `trailing_arm`) and it
suppresses every metric that needs a lateral datum — camber, toe, caster, KPI,
scrub radius, mechanical trail, half track, front-view swing arm.

---

## 3. Top-level keys

Every model file:

```yaml
type: double_wishbone     # double_wishbone | macpherson | trailing_arm
scope: axle               # axle | corner   (corner is the default)
name: "Aurora Front Axle Recreated"
version: "0.1.2"
units: millimeters
```

`version` is the team's own convention, not the schema's: **major** = a fully
functional version, **minor** = a test version (a new feature), **patch** =
fixes and small changes. It is carried into the report and the force-solve
provenance header, so a result can be traced to the file that produced it.

Then, by shape:

```yaml
# scope: axle
vehicle_config: {...}
axle_config:    {...}
hardpoints:
  left:   {...}
  right:  {...}      # optional — omit to mirror `left` through Y = 0
  center: {...}      # optional — shared points (ARB axis, T-bar pivot)
joints:  {...}       # optional
```

```yaml
# scope: corner
side: center
spring:     {type: coilover}   # mechanisms sit at the top level here
actuation:  {type: direct, mount: lower_wishbone}   # double wishbone only
config:     {...}
hardpoints: {...}
joints:     {...}    # optional
```

**Unknown keys are an error, not a warning.** Every schema block is
`extra="forbid"`, so a misspelt key names itself instead of being silently
dropped — which is what you want when the dropped key was a hardpoint.

---

## 4. Configuration blocks

### `vehicle_config:` (axle) / the vehicle half of `config:` (corner)

| key | required | meaning |
| --- | --- | --- |
| `cg_position` | yes | `{x, y, z}` of the whole-vehicle CG. `z` is above **z = 0**, and the force solve re-measures it from the road plane. Aurora's is 39.844 mm right of centre, which is why its static left/right split is not 50/50. |
| `wheelbase` | yes | mm, positive. Must be **identical** in the front and rear files. |
| `driven_axle` | no | `front` \| `rear` |
| `drive_torque_reaction` | with `driven_axle` | `sprung` (inboard motor — linkage carries force at wheel centre) \| `unsprung` (hub motor — linkage carries force and torque, line runs from the contact patch). No default: the two are a tyre radius of leverage apart, so anti-squat is left undefined rather than guessed. |
| `front_brake_bias` | no | 0–1. Used by the anti-dive geometry. **The force solve ignores it** — it distributes longitudinal force by normal load, which is ideal bias. See `../forces/force.md`. |

`cg_position` and `wheelbase` are authored in **both** files and cross-checked;
a mismatch is an error naming both values.

### `axle_config:` (axle) / the axle half of `config:` (corner)

| key | values | notes |
| --- | --- | --- |
| `axle_position` | `front` \| `rear` | does **not** select steering |
| `steering.type` | `rack` \| `none` | `rack` uses `trackrod_*`; `none` uses `toe_link_*` — a fixed toe link is chassis geometry, not an actuator |
| `wheel.offset` | mm | ET convention, positive inboard |
| `wheel.tire.aspect_ratio` | 0–1 | sidewall height ÷ section width (Aurora: 76 / 95 = 0.8) |
| `wheel.tire.section_width` | mm | |
| `wheel.tire.rim_diameter` | **inches** | the one non-metric input |
| `anti_roll.type` | `none` \| `u_bar` \| `t_bar` | axle files only; requires pushrod-rocker actuation |
| `heave_link.type` | `none` \| `rocker_to_rocker` | axle files only; requires pushrod-rocker actuation |

### Mechanisms

| block | values | rules |
| --- | --- | --- |
| `actuation.type` | `direct` \| `pushrod_rocker` | double wishbone only |
| `actuation.mount` | `lower_wishbone` \| `upright` | which body carries the moving pickup |
| `spring.type` | `none` \| `coilover` \| `torsion_bar` | a torsion bar needs `pushrod_rocker`; a trailing arm needs `coilover` or `torsion_bar` |
| `damper.type` | `none` \| `linear` | a separate linear damper needs `pushrod_rocker` and cannot be combined with a coilover |

Invalid combinations are **rejected at load**, with the reason named. A
trailing arm must also declare `steering.type: none`, and a trailing-arm axle
supports neither shared anti-roll hardware nor a heave link yet.

### `left_setup:` / `right_setup:` (axle only)

Side-local setup — today, an outboard camber shim
(`shim_face_point_a`, `shim_face_point_b`, `shim_face_normal`,
`design_thickness`, `setup_thickness`). Explicit `hardpoints.right` plus a
shim on the left requires a matching `right_setup`, so an asymmetric axle
cannot half-describe itself.

---

## 5. Hardpoints

Point names are fixed vocabulary — the loader knows them, and a typo is an
error rather than an ignored point.

**Mirroring.** On an axle, omitting `hardpoints.right` mirrors the complete
left corner (and its side-local setup) through `Y = 0`. That is the normal
case; author `right` only for a genuinely asymmetric axle.

### Double wishbone

```
lower_wishbone_inboard_front   lower_wishbone_inboard_rear   lower_wishbone_outboard
upper_wishbone_inboard_front   upper_wishbone_inboard_rear   upper_wishbone_outboard
axle_inboard   axle_outboard
```

plus, by configuration:

| when | points |
| --- | --- |
| `steering.type: rack` | `trackrod_inboard`, `trackrod_outboard` |
| `steering.type: none` | `toe_link_inboard`, `toe_link_outboard` |
| `spring.type: coilover`, `actuation.type: direct` | `strut_bottom`, `strut_top` |
| `actuation.type: pushrod_rocker` | `pushrod_inboard`, `pushrod_outboard`, `rocker_axis_a`, `rocker_axis_b` |
| `spring.type: torsion_bar` | `torsion_bar_axis_a`, `torsion_bar_axis_b` |
| `damper.type: linear` | `damper_chassis`, `damper_rocker` |
| `anti_roll.type: u_bar` | `droplink_rocker`, `droplink_u_bar`, and in `center:` `arb_u_bar_axis_a`, `arb_u_bar_axis_b` |
| `anti_roll.type: t_bar` | `droplink_t_bar`, and in `center:` `arb_t_bar_pivot` |
| `heave_link.type: rocker_to_rocker` | `heave_link_rocker` |

**`axle_inboard` / `axle_outboard` define the axle axis.** `axle_outboard` is
where the axis meets the hub mounting face; `axle_inboard` is any second point
on the same axis, roughly 100–200 mm inboard. Its exact position is not
critical — only the direction it gives is used.

### Trailing arm

```
trailing_arm_pivot_a   trailing_arm_pivot_b     the two fixed chassis mounts
axle_inboard   axle_outboard
strut_top   strut_bottom                        (coilover)
torsion_bar_axis_a   torsion_bar_axis_b         (torsion bar)
```

On a **sided** arm, `trailing_arm_outboard` is the arm-to-upright joint.

On a **centreline** arm (`side: center`, as on Aurora) two rules apply, both
enforced:

- **`trailing_arm_outboard` must not be authored.** The arm carries the axle
  directly, so `axle_inboard` *is* the moving arm point. Two points at one
  location would give the solver a duplicate free coordinate.
- **The pivot axis must be transverse** — `pivot_a` and `pivot_b` share an X.
  Plan obliquity is what makes a sided arm a *semi*-trailing arm, and its
  camber/toe signs are defined against a vehicle side that a centreline wheel
  does not have.

### MacPherson

`lower_wishbone_*`, the steering or toe link, the axle points, and the strut.
The authored strut clamp must lie on the lower-ball-joint-to-top-mount
steering axis within 1 mm; offset-axis struts are not modelled.

### Outputs, not inputs

`wheel_center`, `wheel_contact_centre`, `axle_midpoint`, `wheel_inboard` and
`wheel_outboard` are **derived**. Do not author them. `wheel_center` can be a
sweep *target*; `wheel_contact_centre` cannot be either — read ride height
from the `ride_height_change` metric instead.

### Maintained examples

The upstream test data is the authoritative example of each variant:

```
tests/data/geometry.yaml                  double-wishbone corner
tests/data/axle_geometry.yaml             mirrored axle
tests/data/axle_geometry_explicit.yaml    explicit asymmetric axle
tests/data/axle_geometry_rocker.yaml      pushrod-rocker + U-bar
tests/data/axle_geometry_t_bar.yaml       pushrod-rocker + T-bar
tests/data/macpherson_geometry.yaml       MacPherson corner
tests/data/trailing_arm_*_geometry.yaml   trailing-arm variants
```

---

## 6. The `joints:` block

Optional, and it drives exactly one thing: the **bearing misalignment** table
in `report.md`. It is read by the sweep reports and **not read at all** by the
force solve. Adding, removing or re-declaring a joint changes no kinematics
and no loads.

### What it answers

Every bearing has a misalignment rating — how far the ball can tilt in its
race before it binds. The sweeps already export the *relative rotation* of the
two bodies meeting at each joint, which does not depend on any bearing axis,
so this block is how you ask: given that motion, how much tilt does **this**
bearing, on **this** axis, actually have to absorb? The number you take to a
catalogue is the worst value anywhere in the sweep set.

Because the relative rotation is axis-independent, declaring a joint,
re-declaring it, or asking what the best available axis would be are all
answered from the CSVs already on disk — **no re-solve.** `--report-only` is
the right loop for tuning this block.

> An undeclared point produces **no output at all**. There is no default set.

### Shape

```yaml
joints:
  <hardpoint name>:
    label: "LCA Front Bush"    # optional; what the report calls it
    type: bushing              # bushing | spherical | rod_end (default spherical)
    bore:                      # the bolt / ball bore axis, fixed to one part
      part: lower_wishbone
      axis: {from: lower_wishbone_inboard_front, to: lower_wishbone_inboard_rear}
    housing:                   # the housing's centred direction, fixed to the other
      part: chassis
      axis: centred
```

Declared **once** and applied to both sides of an axle, the same way
hardpoints mirror.

`type:` carries **no physics**. It selects report vocabulary and per-side
defaults only — a bushing's angle is called *conical deflection*, everything
else's is *misalignment*. How much freedom each direction has is stated by
`bore:` and `housing:`, because the same part behaves differently depending on
what it is mounted to: a rod end threaded into a wishbone has a fully
determined housing, the identical part on a two-point track rod does not.

### `bore:` and `housing:`

A joint is two rigid bodies meeting at a point. Two unit directions decide how
much the bearing must absorb:

- **`bore`** — the bolt or ball bore axis, fixed to one part.
- **`housing`** — the housing's centred direction, fixed to the other part.

They are declared **independently**, so they need not coincide at the neutral
pose. When they do not, the bearing is installed deliberately off centre and
the difference is reported as the joint's **install offset**. Forcing them to
coincide would hide both an assembly error and a legitimate design move: a
pre-tilted housing can roughly halve the required rating when the excursion is
one-sided.

Each side takes:

| key | value | meaning |
| --- | --- | --- |
| `part` | a name, or `{points: [a, b, ...]}` | which body carries this direction. The explicit form is the escape hatch for a body the assembly does not already declare: ≥3 non-collinear points fully determine its orientation, 2 leave a spin undetermined. |
| `axis` | an axis spec, or `optimize` / `centred` / `indeterminate` | the direction itself — see below |
| `perpendicular_to` | an axis spec | this direction is perpendicular to that one |
| `in_plane` | `{normal: <axis>}` or `{points: [a, b, c]}` | this direction lies in that plane |
| `cone_deg` | float, default `90` | half-angle between this direction and the axis of the body carrying it, used when that body's spin is undetermined. 90 is a rod end, whose bore is perpendicular to its shank. |

### Axis specs — four equivalent spellings

All resolve against the **neutral pose, in chassis coordinates**. Exactly one
per axis:

```yaml
axis: {from: lower_wishbone_outboard, to: upper_wishbone_outboard}   # two points
axis: {vector: [-6.38, 0.191, 1.081]}                                # explicit
axis: {x: -6.38, y: 0.191, z: 1.081}                                 # componentwise
axis: {chassis_axis: x}                                              # principal axis
```

**Reach for the two-point form.** It names the kingpin axis, a wishbone pivot
axis, a link's own axis or a rocker axis without hard-coding numbers that go
stale the moment a hardpoint moves. A `vector:` is a snapshot of a direction
at one instant of one revision of the geometry; nothing warns you when the
hardpoints move out from under it.

### The three keywords, and what each implies

| on | keyword | what it means | what you get |
| --- | --- | --- | --- |
| `bore` | `optimize` | you have not chosen an axis yet | **No per-step `misalign_` value** and no *required* figure. The report still gives the **best available** axis and what it would cost — the design question, before hardware exists. |
| `housing` | `centred` | the housing is installed exactly on the bore axis | Install offset is zero by construction. The ordinary case for a bearing pressed into a fully located part. |
| `housing` | `indeterminate` | the housing rides a body whose spin nothing determines — a two-point member | A **band, not a number**: see below. |

`centred` and `indeterminate` belong on the **housing** only; `optimize`
belongs on the **bore** only. Optimising a housing direction is not
implemented, and the loader says so rather than quietly picking one.

**Why `indeterminate` gives a band.** A track rod or coilover with spherical
joints at both ends carries no axial torque, so its roll about its own axis is
undetermined — the solver neither knows nor can know it. The joint's own
figure then assumes the member turns freely to the best position at every
instant, which is a **lower bound**. The report pairs it with a **locked**
value, which assumes the member never turns, and the **locked clocking** angle
that achieves it. **Size against the locked value** unless you know the member
runs free.

**`perpendicular_to` and `in_plane`** state the same kind of fact — this
direction is perpendicular to some axis — and both narrow the search when a
direction is optimised. Giving both pins it exactly, up to sign: that is how
you declare a housing whose bore must lie in the wishbone's plane *and*
perpendicular to its own shank.

### Reading the output

`report.md`'s joints table carries, per joint: **required** (the worst
misalignment anywhere in the set) and the sweep and step it happened at,
**required (locked)** and **locked clocking** for an indeterminate housing,
**install offset**, and the **best available** axis and its cost. Section G of
`../sweep_sets/CHARACTERISTICS.md` has the column-by-column reading.

There is **no pass/fail** on purpose. The tool says what the geometry demands;
you choose a bearing that covers it.

Two sanity checks worth knowing:

- **A wishbone inboard pivot must read exactly 0.00°.** The arm rotates about
  its own pivot axis and nothing else, so a bore on that axis is a pure
  revolute. A non-zero reading there means the geometry is not what the model
  claims — a free check on your hardpoints. Both of Aurora's front bushes read
  0.00° across the whole set.
- **The outboard ball joints read large, and that is real.** Their bore runs
  along the steering axis, roughly perpendicular to the wishbone pivot axis —
  the opposite limit, where the bearing eats the entire arm sweep. Aurora
  reads 21.8° at the LBJ and 29.8° at the UBJ over 30 mm of travel. Ordinary
  rod ends are rated well below that, so it is a genuine constraint on the
  outboard hardware.

> **A sweep switched off in `run.yaml` is invisible to the bearing table.**
> The required column is a maximum over the sweeps that actually ran, so
> disabling one can silently lower a requirement. Check the "at" column.

### Worked example — Aurora's front

```yaml
joints:
  # Inboard bushes. The arm turns about its own pivot axis, so a bore on that
  # axis is a pure revolute and these must read 0.
  lower_wishbone_inboard_front:
    label: "LCA Front Bush"
    type: bushing
    bore:
      part: lower_wishbone
      axis: {from: lower_wishbone_inboard_front, to: lower_wishbone_inboard_rear}

  # Outboard ball joints, pressed into a fully located arm: the housing is
  # determinate and the bore runs along the steering axis.
  lower_wishbone_outboard:
    label: "LBJ"
    type: spherical
    bore:
      part: upright
      axis: {from: lower_wishbone_outboard, to: upper_wishbone_outboard}

  upper_wishbone_outboard:
    label: "UBJ"
    type: spherical
    bore:    {part: upright,         axis: {vector: [-6.38, 0.191, 1.081]}}
    housing: {part: upper_wishbone,  axis: centred}

  # A track rod is a two-point member: nothing determines its spin, so the
  # housing is indeterminate and the report gives a band.
  trackrod_outboard:
    label: "Outer Tie Rod End"
    type: rod_end
    bore:    {part: upright,    axis: {vector: [-50.284, 16.291, -5.917]}}
    housing: {part: track_rod,  axis: indeterminate}

  trackrod_inboard:
    label: "Inner Tie Rod End"
    type: rod_end
    bore:    {part: chassis,    axis: {chassis_axis: x}}
    housing: {part: track_rod,  axis: indeterminate}
```

---

## 7. Checking a file

Cheapest first:

```bash
# Does it load and build at all? Seconds, no solving.
uv run python Working/models/aurora/check.py Working/models/aurora/front.yaml

# Does the design condition close? Writes a picture and reports whether every
# derived wheel contact centre lies on the reconstructed road plane.
uv run kinematics visualize --geometry Working/models/aurora/front.yaml \
    --output front.png

# Does the whole configuration hang together, without spending the CPU?
# One command, every sweep set and the force solve, validating and writing nothing.
uv run python Working/run_all.py --dry-run
```

A schema error names the key. A contact centre off the road plane means the
tyre or axle points do not agree with the ride height the rest of the file
implies — fix that before reading any characteristic, because every road-plane
metric is built on it.
