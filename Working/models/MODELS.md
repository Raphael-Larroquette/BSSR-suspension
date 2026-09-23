# Model files — geometry and joints

A model file is the car: hardpoints, architecture, vehicle configuration, and optionally
the bearings you want misalignment reported for. One copy, read by both the sweeps and
the force solve.

```
Working/models/aurora/
  front.yaml    scope: axle    two mirrored double-wishbone corners
  rear.yaml     scope: corner  one centreline trailing arm
```

One folder per car. `outputs/` and `report/` land beside it and are git-ignored.

Coordinates, units and signs: see the root `README.md` §3. What the outputs *mean*:
`../sweep_sets/CHARACTERISTICS.md`.

1. [The two file shapes](#1-the-two-file-shapes)
2. [Top-level keys](#2-top-level-keys)
3. [Configuration blocks](#3-configuration-blocks)
4. [Hardpoints](#4-hardpoints)
5. [The `joints:` block](#5-the-joints-block)
6. [Checking a file](#6-checking-a-file)

---

## 1. The two file shapes

`scope:` decides which keys the file takes. It is the most common source of a confusing
schema error.

| | `scope: axle` | `scope: corner` |
| --- | --- | --- |
| models | two corners, composed | one corner |
| vehicle data | `vehicle_config:` | inside `config:` |
| axle data | `axle_config:` | inside `config:` |
| mechanisms | inside `axle_config:` | **top level** (`spring:`, `actuation:`) |
| hardpoints | `hardpoints.left` / `.right` / `.center` | `hardpoints:` flat |
| `side:` | not used | required (default `left`) |

`corner` is the default and may be omitted. An axle file must say `scope: axle`.

A corner is not a lesser axle: it has no track, roll, roll centre or Ackermann, and those
channels are not produced at all. In exchange it produces the side-view family (SVIC,
SVSA, anti-squat) that parallel wishbones cannot.

**`side:` on a corner file** is `left` or `center`. `right` is rejected — a right corner
is the mirror of a left one. If a sided wheel faces the other way, negate every `y`.
`center` is accepted only by architectures supporting a centreline wheel (today,
`trailing_arm`) and suppresses every metric needing a lateral datum: camber, toe, caster,
KPI, scrub radius, mechanical trail, half track, front-view swing arm.

---

## 2. Top-level keys

```yaml
type: double_wishbone     # double_wishbone | macpherson | trailing_arm
scope: axle               # axle | corner   (corner is the default)
name: "Aurora Front Axle Recreated"
version: "0.1.2"
units: millimeters
```

`version` is our convention, not the schema's: **major** = fully functional version,
**minor** = a test version / new feature, **patch** = fixes and small changes. It is
carried into the report and the force-solve provenance header.

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
spring:     {type: coilover}                        # mechanisms at top level here
actuation:  {type: direct, mount: lower_wishbone}   # double wishbone only
config:     {...}
hardpoints: {...}
joints:     {...}    # optional
```

**Unknown keys are an error, not a warning** — every block is `extra="forbid"`, so a
misspelt key names itself instead of being silently dropped.

---

## 3. Configuration blocks

### Vehicle

| key | required | meaning |
| --- | --- | --- |
| `cg_position` | yes | `{x, y, z}` of the whole-vehicle CG. Must be **identical** in the front and rear files |
| `wheelbase` | yes | mm, positive. Must be **identical** in both files |
| `driven_axle` | no | `front` \| `rear` |
| `drive_torque_reaction` | with `driven_axle` | `sprung` (inboard motor) \| `unsprung` (hub motor). **No default** — the two are a tyre radius of leverage apart, so anti-squat is left blank rather than guessed |
| `front_brake_bias` | no | 0–1, used by anti-dive geometry. **The force solve ignores it** |

A mismatch between the two files is an error naming both values.

### Axle

| key | values | notes |
| --- | --- | --- |
| `axle_position` | `front` \| `rear` | does **not** select steering |
| `steering.type` | `rack` \| `none` | `rack` uses `trackrod_*`; `none` uses `toe_link_*` |
| `wheel.offset` | mm | ET convention, positive inboard |
| `wheel.tire.aspect_ratio` | 0–1 | sidewall height ÷ section width (Aurora: 76/95 = 0.8) |
| `wheel.tire.section_width` | mm | |
| `wheel.tire.rim_diameter` | **inches** | |
| `wheel.tire.loaded_radius` | mm, optional | the radius **at design ride height**. The section dimensions give the *unloaded* radius; a loaded tyre deflects, so its centre sits lower. Hardpoints are authored loaded, so stating this puts the contact centre on `z = 0` instead of a deflection below it. Omit it and the unloaded radius is used for both — the behaviour before this key existed. Positive, and no larger than the unloaded radius |
| `anti_roll.type` | `none` \| `u_bar` \| `t_bar` | axle only; requires pushrod-rocker |
| `heave_link.type` | `none` \| `rocker_to_rocker` | axle only; requires pushrod-rocker |

### Mechanisms

| block | values | rules |
| --- | --- | --- |
| `actuation.type` | `direct` \| `pushrod_rocker` | double wishbone only |
| `actuation.mount` | `lower_wishbone` \| `upright` | which body carries the moving pickup |
| `spring.type` | `none` \| `coilover` \| `torsion_bar` | torsion bar needs `pushrod_rocker`; a trailing arm needs `coilover` or `torsion_bar` |
| `damper.type` | `none` \| `linear` | needs `pushrod_rocker`; cannot combine with a coilover |

Invalid combinations are rejected at load with the reason named. A trailing arm must
declare `steering.type: none`, and a trailing-arm axle supports neither shared anti-roll
hardware nor a heave link.

### `left_setup:` / `right_setup:` (axle only)

Side-local setup — today, an outboard camber shim (`shim_face_point_a`,
`shim_face_point_b`, `shim_face_normal`, `design_thickness`, `setup_thickness`). An
explicit `hardpoints.right` plus a shim on the left requires a matching `right_setup`.

---

## 4. Hardpoints

Point names are fixed vocabulary; a typo is an error, not an ignored point.

**Mirroring.** On an axle, omitting `hardpoints.right` mirrors the complete left corner
(and its side-local setup) through `Y = 0`. Author `right` only for a genuinely
asymmetric axle.

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
| `spring: coilover` + `actuation: direct` | `strut_bottom`, `strut_top` |
| `actuation: pushrod_rocker` | `pushrod_inboard`, `pushrod_outboard`, `rocker_axis_a`, `rocker_axis_b` |
| `spring: torsion_bar` | `torsion_bar_axis_a`, `torsion_bar_axis_b` |
| `damper: linear` | `damper_chassis`, `damper_rocker` |
| `anti_roll: u_bar` | `droplink_rocker`, `droplink_u_bar`; in `center:` `arb_u_bar_axis_a/b` |
| `anti_roll: t_bar` | `droplink_t_bar`; in `center:` `arb_t_bar_pivot` |
| `heave_link: rocker_to_rocker` | `heave_link_rocker` |

**`axle_inboard` / `axle_outboard` define the axle axis.** `axle_outboard` is where the
axis meets the hub mounting face; `axle_inboard` is any second point on the same axis,
roughly 100–200 mm inboard. Only the direction is used.

### Trailing arm

```
trailing_arm_pivot_a   trailing_arm_pivot_b     the two fixed chassis mounts
axle_inboard   axle_outboard
strut_top   strut_bottom                        (coilover)
torsion_bar_axis_a   torsion_bar_axis_b         (torsion bar)
```

On a **sided** arm, `trailing_arm_outboard` is the arm-to-upright joint.

On a **centreline** arm (`side: center`, as on Aurora), both enforced:

- **`trailing_arm_outboard` must not be authored.** The arm carries the axle directly, so
  `axle_inboard` *is* the moving arm point.
- **The pivot axis must be transverse** — `pivot_a` and `pivot_b` share an X.
- `axle_inboard` must lie rearward of the pivot axis, and not on it.

### MacPherson

`lower_wishbone_*`, the steering or toe link, the axle points, and the strut. The
authored strut clamp must lie on the LBJ-to-top-mount steering axis within 1 mm.

### Derived — do not author

`wheel_center`, `wheel_contact_centre`, `axle_midpoint`, `wheel_inboard`,
`wheel_outboard`. `wheel_center` can be a sweep target; `wheel_contact_centre` cannot —
read ride height from the `ride_height_change` metric.

### Upstream examples

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

## 5. The `joints:` block

Optional. Drives exactly one thing: the **bearing misalignment** table in `report.md`.
Not read by the force solve, and it changes no kinematics. **An undeclared point produces
no output at all** — there is no default set.

It answers: given how the suspension moves, how much tilt does this bearing, on this
axis, have to absorb? The number you take to a catalogue is the worst value anywhere in
the sweep set.

The sweeps export the relative rotation of the two bodies, which is axis-independent, so
**declaring or re-declaring a joint never needs a re-solve** — use
`--report-only --no-forces`.

### Shape

```yaml
joints:
  <hardpoint name>:
    label: "LCA Front Bush"    # optional
    type: bushing              # bushing | spherical | rod_end (default spherical)
    bore:                      # bolt / ball bore axis, fixed to one part
      part: lower_wishbone
      axis: {from: lower_wishbone_inboard_front, to: lower_wishbone_inboard_rear}
    housing:                   # housing's centred direction, fixed to the other part
      part: chassis
      axis: centred            # omit `housing:` entirely to mean centred
```

Declared once, applied to both sides of an axle.

`type:` carries **no physics** — it selects report vocabulary only (a bushing's angle is
called *conical deflection*, everything else's *misalignment*). How much freedom each
direction has is stated by `bore:` and `housing:`.

### Fields on `bore` and `housing`

| key | value | meaning |
| --- | --- | --- |
| `part` | a body name, or `{points: [a, b, ...]}` | which body carries this direction. Optional when exactly two bodies meet at the point. ≥3 non-collinear points fully determine orientation; 2 leave a spin undetermined |
| `axis` | an axis spec, or `optimize` / `centred` / `indeterminate` | the direction |
| `perpendicular_to` | an axis spec | this direction is perpendicular to that one |
| `in_plane` | `{normal: <axis>}` or `{points: [a, b, c]}` | this direction lies in that plane |
| `cone_deg` | float, default `90` | half-angle to the carrying body's axis, used when that body's spin is undetermined. 90 = a rod end |

`bore` and `housing` are declared **independently** and need not coincide at the neutral
pose. When they don't, the bearing is installed deliberately off centre and the
difference is reported as the **install offset** — a pre-tilted housing can roughly halve
the required rating when the excursion is one-sided.

### Axis specs — four spellings, exactly one per axis

All resolve at the **neutral pose, in chassis coordinates**.

```yaml
axis: {from: lower_wishbone_outboard, to: upper_wishbone_outboard}   # two points
axis: {vector: [-6.38, 0.191, 1.081]}                                # explicit
axis: {x: -6.38, y: 0.191, z: 1.081}                                 # componentwise
axis: {chassis_axis: x}                                              # principal axis
```

**Prefer the two-point form.** A `vector:` is a snapshot of one revision of the geometry
and goes stale silently when a hardpoint moves.

### The three keywords

| on | keyword | meaning | what you get |
| --- | --- | --- | --- |
| `bore` | `optimize` | no axis chosen yet | no per-step `misalign_` value; the report still gives the **best available** axis and its cost |
| `housing` | `centred` | installed exactly on the bore axis | install offset zero by construction. The default when `housing:` is omitted |
| `housing` | `indeterminate` | housing rides a two-point member whose spin nothing determines | a **band**: a free-to-spin lower bound, plus a locked value and its clocking. **Size against the locked value** |

`centred` / `indeterminate` belong on the housing only; `optimize` on the bore only.
Optimising a housing direction is not implemented.

`perpendicular_to` and `in_plane` narrow an optimised search; giving both pins the
direction exactly, up to sign.

### Output

Per declared joint, per side: `joint_<name>_rx/ry/rz` (relative rotation vector, deg, in
the housing's neutral frame — always) and `misalign_<name>` (only when the bore axis is
authored). Plus `joints.csv` and a report section carrying required angle and where it
peaked, required (locked), locked clocking, install offset, and best available.

Column-by-column reading: `../sweep_sets/CHARACTERISTICS.md` §G.

**Two sanity checks:**

- A wishbone inboard pivot **must read exactly 0.00°** — the arm rotates about that axis
  and nothing else. A non-zero reading means the geometry is not what the model claims.
  Both of Aurora's front bushes read 0.00° across the whole set.
- The outboard ball joints read large and that is real: their bore runs along the
  steering axis, roughly perpendicular to the pivot axis. Aurora reads 21.8° at the LBJ
  and 29.8° at the UBJ over 30 mm of travel — a genuine constraint on the hardware.

> **A sweep switched off in `run.yaml` is invisible to the bearing table.** The required
> column is a maximum over the sweeps that *ran*, so disabling one can silently lower a
> requirement. Check the "at" column.

### Errors

| Message | Cause |
| --- | --- |
| `Joint '...' does not name a suspension point` | spelling; the key must be a lowercase PointID |
| `...names part '...', which is not a body. Available parts: ...` | wrong body name — the message lists every legal one |
| `...needs exactly two bodies meeting at its point, but 1 carry it` | name both sides with `part`, by name or `{points: [...]}` |
| `...declares an indeterminate housing, but part '...' is fitted from >=3 points` | `indeterminate` only applies to a two-point member |
| `...needs a bore axis: give 'bore.axis' a direction, or 'optimize'` | `bore:` omitted or missing `axis` |
| `'centred'/'indeterminate' belongs on the housing` | keyword on the wrong side |
| `Optimising the housing direction is not implemented yet` | use `centred` or `indeterminate` |
| `...declares a bore axis 90.000 degrees away from the perpendicularity it also declares` | `axis` and `perpendicular_to` contradict each other |

To list the bodies and the two-body points in *your* geometry, see `../sweep_sets/SWEEPS.md` §8.

---

## 6. Checking a file

Cheapest first:

```bash
# Does it load and build at all? Seconds, no solving.
uv run python Working/models/aurora/check.py Working/models/aurora/front.yaml

# Does the design condition close? Writes a picture and reports whether every derived
# wheel contact centre lies on the reconstructed road plane.
uv run kinematics visualize --geometry Working/models/aurora/front.yaml --output front.png

# Does the whole configuration hang together? Every sweep set and the force solve,
# validated, nothing written.
uv run python Working/run_all.py --dry-run
```

A schema error names the key. A contact centre off the road plane means the tyre or axle
points disagree with the ride height the rest of the file implies — **fix that before
reading any characteristic**, because every road-plane metric is built on it.
