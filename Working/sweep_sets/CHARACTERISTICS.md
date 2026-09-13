# Characteristics reference

Every characteristic is reported four ways: value at the design condition, min, max, and
range across the sweep.

**You choose which appear.** Each sweep's table is the channel list named under
`sweeps.<name>.report` in `run.yaml`, in that order. The **channel** column below is the
name you write there; **best source** is the sweep that gives the meaningful version.
Configuration keys: `RUNNING.md`.

---

## A. Alignment and steering geometry (corner)

Every channel here also has a `_lr` variant (`camber_lr`, `toe_lr`, …) reporting left and
right side by side — what you want in a roll or steer sweep.

| Channel | Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- | --- |
| `camber` | camber | deg | 01, 02 | **Chassis-relative** |
| `camber_road` | camber, road-relative | deg | 02 | Parser-derived: `camber − roll`. This is what the tyre sees |
| `caster` | caster | deg | 01, 04 | |
| `kpi` | kingpin inclination | deg | 01, 04 | |
| `toe` | toe (positive = toe-in) | deg | 01, 02 | Project convention, **not** ISO |
| `steer_angle` | ISO steer angle | deg | 04 | Use this when comparing to anything ISO-based |
| `scrub_iso` | scrub radius (ISO unsigned) | mm | 01, 04 | Includes mechanical trail — see trap 1 |
| `scrub_signed` | scrub radius (signed lateral) | mm | 01, 04 | Alias for `steering_axis_offset_ground`. **This is SUSProg's scrub radius** |
| `trail` | mechanical trail | mm | 01, 04 | ISO caster offset at ground, wheel-relative |
| `half_track` | half track | mm | 01 | Per corner |

## B. Instant centres and swing arms (corner)

| Channel | Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- | --- |
| `fvic_y`, `fvic_z` | front-view IC | mm | 01, 02 | Y–Z plane only; there is no `fvic_x`. Goes to ±10⁵ mm and flips sign when the arms pass through parallel |
| `fvsa` | front-view swing-arm length | mm | 01 | Sets camber gain |
| `svic_x`, `svic_z` | side-view IC | mm | 01 | Undefined when the wishbone axes are parallel in side view |
| `svsa`, `svsa_angle` | side-view swing arm | mm, deg | 01 | Same |
| `anti_dive`, `anti_lift`, `anti_squat` | anti-geometry | % | 01 | Built on the SVIC, so they share its fate |

**Tabulated, never plotted.** FVSA passes through infinity every time the wishbones cross
parallel — on Aurora between −55 and −35 mm of travel, where it runs
−4538 → −18506 → +13936 mm with nothing physical happening. **Plot `camber_gain`
instead**: to first order the corner rotates about the FVIC, so

```
d(camber)/dz ≈ −1 / FVSA  [rad/mm] ≈ −57.296 / FVSA  [deg/mm]
```

which holds to 1–3% across Aurora's whole range. Read `fvic_y` / `fvic_z` / `fvsa` from
the table when you want to know *where* to move a hardpoint.

## C. Springing and travel

| Channel | Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- | --- |
| `damper_length` | damper length | mm | 01, 08 | |
| `motion_ratio` | motion ratio (damper/wheel) | mm/mm | **08** | Analytic, from the Jacobian |
| `motion_ratio_sq` | motion ratio squared | – | 08 | Wheel rate = spring rate × MR². Parser-derived |
| `damper_rate` | damper rate vs wheel | mm/mm | 01 | Raw signed derivative; MR is its negation |
| `wheel_travel` | wheel travel for a given damper stroke | mm | **08** | The reason sweep 08 exists |

**Read motion ratio from 08, not 01.** Both report it, but 08 is driven by damper length
and reads the wheel, so MR is measured in the coordinate the hardware constrains.

**Sweep 08 sets the travel limits everywhere else.** Read usable wheel travel off it, then
write it into the `travel:` ranges in `run.yaml`. On Aurora, ±30 mm of damper gives
−59.5 / +58.0 mm of wheel travel.

## D. Axle-level behaviour

| Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- |
| track, track change, track change rate | mm, mm/mm | 01, 02 | Rate is parser-derived as 2 × half-track rate. Proxy for lateral tyre scrub |
| roll-centre height | mm | 01, 02 | |
| roll-centre lateral position | mm | 02 | Zero by symmetry in heave |
| RC migration vs travel | mm/mm | 01 | Parser-derived |
| RC migration vs roll | mm/deg | 02 | Parser-derived |
| RC lateral migration vs roll | mm/deg | 02 | Parser-derived |
| body roll | deg | 02 | Kinematic axle roll, **not** a solved sprung-mass attitude. Identically zero in parallel bump |

**`heave` is not heave in the vehicle-dynamics sense** — it is the mean of the two
wheel-centre vertical displacements. Zero by construction in roll, numerically identical
to wheel travel in parallel bump, so it stays in the CSV only. True CG vertical motion
needs a solved 6-DOF body attitude, which a grounded-chassis model cannot produce.

**`ride_height_change` is not reported.** It is the perpendicular chassis-origin-to-road
distance, which in roll is a second-order artefact of the plane tilting (0 to 0.037 mm on
Aurora). It is not a vehicle ride height.

## E. Steering-specific (04, with 05/06 as the loaded comparison)

| Channel | Characteristic | Unit | Notes |
| --- | --- | --- | --- |
| `steering_ratio` | steering ratio (rack) | deg/mm | Magnitude of `deriv_steer_angle_wrt_rack_displacement_left`; 0.673–0.902 on Aurora |
| `steering_ratio_unitless` | steering wheel : road wheel | – | Only when the geometry declares rack travel per turn — see below |
| `ackermann_error` | inner − outer | deg | Positive = inner steers more = toward Ackermann |
| `ackermann` | Ackermann | % | Against the geometric ideal. **Only where the rack moves** |
| `camber`, `caster`, `kpi` | vs steer | deg | |
| `scrub_signed`, `trail` | vs steer | mm | Both migrate substantially with steer on Aurora |

**Why the raw steering ratio is negative.** Rack +y is toward the left of the car, which
steers the wheels right, i.e. to a negative ISO angle. The report takes the magnitude.

**Getting a unitless steering ratio** needs a hardware fact the kinematic model lacks.
Declare either of these and `steering_ratio_unitless` appears automatically:

```yaml
vehicle_config:
  steering:
    rack_travel_per_turn: 50.0    # mm of rack per steering-wheel revolution
    pinion_radius: 7.96           # mm; equivalently, travel per turn = 2*pi*r
```

Then `i_s = 360 / (rack_travel_per_turn × steering_ratio_deg_per_mm)`. At Aurora's design
0.6833 deg/mm, a 50 mm/rev rack gives 10.5 : 1. Without the field nothing warns.

**Why Ackermann is missing from bump and roll sweeps.** With the rack centred both wheels
are straight, so `%Ack` is 0/0. It is computed only in 04, 05, 06, 09 and 10, and its
design-condition cell in a lock-to-lock sweep is `-` because the design condition of that
sweep *is* zero rack. **Read the range, not the design value.** This is also why 09
exists: it is the only place Ackermann is defined at a rolled attitude.

## F. Gradients (analytic, from the constraint Jacobian)

Available whenever a `hub_z` target exists — every sweep except 08.

| Gradient | Unit |
| --- | --- |
| camber gain (`d camber / d hub z`) | deg/mm |
| bump steer rate (`d toe / d hub z`) | deg/mm |
| ISO steer gain in bump | deg/mm |
| caster gain, KPI gain | deg/mm |
| half-track change rate | mm/mm |
| wheel-centre recession rate (`d x / d hub z`) | mm/mm |
| damper rate vs wheel | mm/mm |
| toe / steer / camber per rack | deg/mm |
| camber recovery (`d camber / d roll`) | deg/deg — parser-derived, **roll sweep only** |

Camber recovery does not exist in a parallel bump sweep: body roll is identically zero
through 01, so the derivative is undefined. Camber gain is 01's equivalent.

## G. Bearing misalignment (opt-in, per declared joint)

Only for joints declared in the geometry file's `joints:` block (`../models/MODELS.md`
§5). An undeclared point is not analysed at all.

| Characteristic | Unit | Notes |
| --- | --- | --- |
| `joint_<name>_rx/ry/rz` | deg | Relative rotation vector of the two bodies, in the housing's neutral frame. Axis-independent |
| `misalign_<name>` | deg | The angle the bearing absorbs at each step. Only when the bore axis is authored |
| install offset | deg | Neutral-pose angle between housing and bore. Non-zero = fitted off centre |
| required / required (locked) | deg | Worst value anywhere in the sweep set, plus the sweep and step it peaked at |
| locked clocking | deg | For a housing on a two-point member: the assembly clocking minimising the worst case |
| best available | deg | What the joint would need with its bore axis chosen optimally |

**Take the *required* column to the catalogue** — the part has to survive the whole set.
There is no pass/fail on purpose.

- **A wishbone pivot reads exactly zero.** The arm rotates about that axis and nothing
  else. A non-zero reading is a free check that your hardpoints are wrong. Aurora's front
  bushes both read 0.00°.
- **The outboard ball joints read large and that is real.** Their bore runs along the
  steering axis, roughly perpendicular to the pivot axis. Aurora: 21.8° at the LBJ,
  29.8° at the UBJ over 30 mm of travel — well above ordinary rod-end ratings.
- **Two-point members give a band, not a number.** A track rod or coilover with spherical
  joints at both ends carries no axial torque, so its spin is unknowable. `indeterminate`
  reports the free-to-spin lower bound; the report pairs it with a locked value.
  **Size against the locked value** unless you know the member runs free.
- **Nothing here needs a re-solve** — the relative rotation is axis-independent, so
  `--report-only` answers every axis question from the CSVs.

---

## Convention traps before you diff against SUSProg

1. **`scrub_radius` is not scrub radius.** It follows ISO 8855 §7.2.10 — the unsigned
   road-plane *distance* from contact centre to steering-axis ground intersection — so it
   includes mechanical trail and is never negative. Compare
   **`steering_axis_offset_ground`** (emitted as `scrub_radius_signed`) against SUSProg.
   On Aurora: `scrub_radius = 54.709`, `steering_axis_offset_ground = −23.861`,
   `mechanical_trail = 49.231`, and `hypot(−23.861, 49.231) = 54.709` ✓ (verified every
   run).
2. **Camber is chassis-relative.** Road-relative inclination is not exported. In roll the
   difference is large: Aurora reaches only −0.33° chassis camber at 3.3° roll, while
   road-relative reaches −3.66°.
3. **`toe_angle` ≠ `steer_angle`.** Both are exported. They are negatives of each other on
   the left and not on the right.
4. **Nothing here is compliance or load.** Rigid links, ideal joints, rigid disc tyre at
   nominal radius. If SUSProg applies a loaded radius, ride heights will not match and
   neither tool is wrong.
5. **Gradients are analytic, not differenced.** Expect small disagreements with any tool
   that finite-differences between steps; the Jacobian value is more accurate.
6. **`ride_height_change` and `roll` are single-axle kinematic quantities**, not
   whole-vehicle attitude.
7. **Steering ratio is signed by the rack direction**, not by anything physical.
8. **Ackermann is 0/0 with the rack centred.**
9. **`heave` is mean wheel-centre displacement**, not CG vertical motion.
10. **A sweep switched off in `run.yaml` is invisible to the bearing table.** Check the
    "at" column before turning one off.

---

## What is undefined, and why

Each of these is the geometry telling you something true, not a tool limitation.

**Side-view IC and the anti-geometry channels** are undefined whenever the two wishbone
inboard axes are **parallel in side view** — the SVIC is then at infinity. On Aurora's
front both inboard axes are exactly horizontal (`lower_*: z 185`, `upper_*: z 514.82`), so
they are parallel and every metric built on the SVIC is blank. Anti-dive is a design
output of where you put the inboard pivots: if the real arms are level, **0% anti-dive is
the correct answer** — record it rather than chase the blank. Tilt either axis and they
all populate.

**Anti-dive also needs `front_brake_bias`** in `vehicle_config`; it is optional in the
schema and absent from Aurora's front, so anti-dive would return `None` regardless.
`anti_squat` stays `None` on the front and that is physically correct — an undriven axle
cannot squat. Do not set `driven_axle: front` to make the number appear.

---

## Reading these on a three-wheel car

Aurora is a tadpole. Every axle-level channel is computed from the **two front wheels
only**, and the vocabulary is borrowed from four-wheel practice.

- **Track, roll and roll-centre height are front-axle quantities.** None of them knows the
  rear wheel exists.
- **There is no roll axis.** A single rear wheel has no roll centre, so there is no second
  point and no axis. Consequence: **the front roll-centre height carries essentially the
  entire geometric lateral load transfer**, with no rear geometry to share it. A
  roll-centre height that would be unremarkable on a four-wheel car is doing much more
  work here.
- **Rollover is a three-wheel problem, not an axle problem.** The stability boundary is
  the triangle joining the three contact patches, so the critical direction is diagonal,
  not lateral. Front track buys less than it would on a four-wheel car and CG longitudinal
  position matters as much as CG height. Nothing in this sweep set computes that
  threshold — do not read a comfortable roll-centre number as rollover margin. (Zandieh,
  *Dynamics of a Three-Wheel Vehicle with Tadpole Design*, Waterloo MASc 2014.)
- **`ackermann` uses the front track and the wheelbase**, which is correct here: the turn
  centre still lies on the rear axle line, which passes through the single rear patch.

### Anti-squat depends on where the drive torque is reacted

All three anti percentages are the inclination of a force line from a reaction point to
the SVIC, scaled by `L / h`:

```
anti % = 100 * (L / h) * tan(theta),    tan(theta) = rise / run  (R -> SVIC)
```

What changes is **R**, decided by which body reacts the torque:

| layout | reacted by | R |
| --- | --- | --- |
| inboard motor / diff through halfshafts | chassis | wheel centre |
| hub motor | suspension linkage | contact patch |
| outboard brake | suspension linkage | contact patch |
| inboard brake | chassis | wheel centre |

The gap is a whole tyre radius of leverage — on Aurora, the difference between **0% and
520%**. At the design pose the rear SVIC sits at the arm pivot `(-1865, 278.5)`, exactly
level with the hub, so the wheel-centre line is horizontal and the sprung answer is zero.
From the contact patch: `tan θ = 278.5/375 = 0.743`, `h/L = 320/2240 = 0.143`,
anti-squat = 520%.

So `drive_torque_reaction` has **no default** — declare `sprung` or `unsprung` alongside
`driven_axle`, or `anti_squat` stays blank. Aurora's rear is a hub motor: `unsprung`.
Anti-dive and anti-lift currently assume **outboard brakes** and always measure from the
contact patch.

### Read the anti percentages at the design pose only

On a single-corner model neither term of `L / h` survives away from design:

- `h` is CG height above the road plane, and a standalone corner places that plane through
  its own contact patch. Drive the wheel 60 mm into bump and `h` falls 60 mm, as though
  the whole car sank on one corner; the true drop is nearer 30 mm.
- `L` is held at the authored wheelbase though the contact patch moves ≈5 mm (0.2%) — the
  lesser error by a factor of fifty.

The geometric half, `z_P / x_P`, is right everywhere. So the rear report prints the design
value, leaves min/max/range blank, and plots no curve. To see how the geometry itself
moves through travel, read **SVSA angle** — the same line without the scaling.

---

## The rear is a centreline corner

Aurora's rear is one trailing-arm corner with its wheel on the vehicle centreline, modelled
as a standalone corner declared `side: center`. Three consequences:

1. **CSV columns carry no side suffix** — `damper_length`, not `damper_length_left`.
2. **Every axle channel is absent by definition**: track, track change, body roll,
   roll-centre height and lateral migration, rack displacement, Ackermann, axle steering
   ratio.
3. **The side-view family finally means something.** A trailing arm's SVIC is its pivot
   axis, so `svic_x`, `svic_z`, `svsa`, `svsa_angle` and `anti_squat` all populate where
   the front leaves them blank.

### What a centreline wheel cannot report

A wheel on the centreline has no inboard and no outboard, so every metric measured against
a lateral datum has **no** answer, not a small one:

| absent | because it measures |
| --- | --- |
| `camber`, `toe_angle`, `steer_angle` | a wheel-axis angle whose sign mirrors about a vehicle side |
| `caster`, `kpi`, `mechanical_trail` | an angle of, or offset along, a kingpin axis — an unsteered arm has none |
| `scrub_radius`, `steering_axis_offset_ground` | where that kingpin axis meets the ground |
| `half_track` | lateral distance from the centreline the wheel is already on |
| `fvic_y`, `fvic_z`, `fvsa_length` | the front-view swing arm, whose sign follows the vehicle side |

These are removed at the source (`TrailingArmSuspension.suppressed_metric_keys()`). They
are **not** in the CSV as blanks, and naming them under `plots:` will not bring them back.

Camber and toe are doubly gone: the sign convention has no referent, **and** a transverse
pivot would hold both at their design values anyway. Camber gain at the rear needs plan
obliquity — and an oblique centreline arm is a different architecture.

**There is no `trailing_arm_outboard` on a centreline arm.** The arm bolts straight to the
motor axle, so `axle_inboard` is the arm point and the single free coordinate. Nothing is
lost: the motion is one rotation about the pivot axis whatever point you pick, so the
wheel path is identical, and what the choice used to change — the nominal alignment line,
and caster and KPI about it — is exactly the set a centreline wheel does not report.

Both spring layouts work on a centreline arm. A torsion bar reports `torsion_bar_twist`
with **positive twist = bump**, fixed once from the design geometry.
