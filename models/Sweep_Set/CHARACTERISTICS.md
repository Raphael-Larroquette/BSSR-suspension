# Everything you can get out of this sweep set

Every characteristic below is reported four ways by `susreport.py`: value at
the design condition, minimum, maximum, and range across the sweep.

**You choose which ones appear.** `report.md` is not a dump of everything the
solver can compute — each sweep's table is the channel list named under
`sweeps.<name>.report` in `run.yaml`, in that order. This document is the menu:
the **channel** column is the name you write in `run.yaml`, and "best source"
is which sweep gives the *meaningful* version. Most channels exist in every
sweep, but e.g. camber recovery only means something where the axle rolls.

See `RUNNING.md` for the configuration keys themselves.

---

## A. Alignment and steering geometry (corner)

Every channel in this section also has a `_lr` variant (`camber_lr`,
`toe_lr`, …) that reports the left and right corner side by side, which is what
you want in a roll or steer sweep.

| Channel | Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- | --- |
| `camber` | Camber | deg | 01 bump, 02 roll | **Chassis-relative.** See the road-relative row below. |
| `camber_road` | Camber, road-relative | deg | 02 roll | Derived by the parser: `camber − roll`. Not exported by the solver. This is what the tyre sees. |
| `caster` | Caster | deg | 01, 04 | |
| `kpi` | Kingpin inclination | deg | 01, 04 | |
| `toe` | Toe (positive = toe-in) | deg | 01 bump, 02 roll | Project convention, **not** ISO. |
| `steer_angle` | ISO steer angle | deg | 04 steer | The ISO vehicle-fixed angle, reported alongside toe. Use this one when comparing to anything ISO-based. |
| `scrub_iso` | Scrub radius (ISO unsigned) | mm | 01, 04 | **Read the caveat in the convention traps.** |
| `scrub_signed` | Scrub radius (signed lateral) | mm | 01, 04 | Parser alias for `steering_axis_offset_ground`. **This is the number SUSProg calls scrub radius.** |
| `trail` | Mechanical trail | mm | 01, 04 | ISO caster offset at ground, wheel-relative — not a raw chassis-X difference. |
| `half_track` | Half track | mm | 01 | Per corner. |

## B. Instant centres and swing arms (corner)

| Channel | Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- | --- |
| `fvic_y`, `fvic_z` | Front-view IC, lateral and height | mm | 01, 02 | Lives in the Y–Z plane; there is no `fvic_x`. Goes to ±10⁵ mm and flips sign when the arms pass through parallel. Not a bug. |
| `fvsa` | Front-view swing-arm length | mm | 01 | Sets camber gain. |
| `svic_x`, `svic_z` | Side-view IC | mm | 01 | Undefined whenever the wishbone axes are parallel in side view — see "What is undefined, and why". |
| `svsa`, `svsa_angle` | Side-view swing-arm length / angle | mm, deg | 01 | Same. |
| `anti_dive`, `anti_lift`, `anti_squat` | Anti-geometry | % | 01 | Built on the SVIC, so they share its fate. |

**These four are tabulated but never plotted.** FVSA passes through infinity
every time the wishbones cross parallel — on Aurora that happens between −55 mm
and −35 mm of travel, where FVSA runs −4538 → −18506 → +13936 mm without
anything physically dramatic occurring. Plotted raw it flattens every other
panel in the figure. **Camber gain is the bounded equivalent**: to first order
the corner rotates about the FVIC, so

```
d(camber)/dz  ≈  −1 / FVSA        [rad/mm]
              ≈  −57.296 / FVSA   [deg/mm]
```

Checked against Aurora's 01 sweep, that holds to 1–3% across the whole range
(the residual is the difference between wheel-centre and contact-patch travel).
So plot `camber_gain`, and read `fvic_y` / `fvic_z` / `fvsa` from the table when
you want to know *where* to move a hardpoint rather than what the result is.

## C. Springing and travel

| Channel | Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- | --- |
| `damper_length` | Damper length | mm | 01, 08 | |
| `motion_ratio` | Motion ratio (damper/wheel) | mm/mm | **08 damper stroke** | Analytic, from the Jacobian — not finite-differenced. |
| `motion_ratio_sq` | Motion ratio squared | – | 08 | Wheel rate = spring rate × MR². Parser-derived. |
| `damper_rate` | Damper rate vs wheel | mm/mm | 01 | The raw signed derivative; MR is its negation. |
| `wheel_travel` | Wheel travel available for a given damper stroke | mm | **08 damper stroke** | The whole reason sweep 08 exists. |

**Read motion ratio from 08, not 01.** Both report it, but 08 is driven by
damper length and reads the wheel, so MR there is measured in the coordinate
the hardware actually constrains. In 01 it is the same derivative taken the
other way round — correct, but a step further from the thing you buy.

**Sweep 08 is how you set the travel limits in every other sweep.** It maps
damper stroke onto usable wheel travel; you read that off, then write it into
the `travel:` ranges in `run.yaml`. On Aurora, ±30 mm of damper gives
−59.5 / +58.0 mm of wheel travel.

## D. Axle-level behaviour

| Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- |
| Track, track change, track change rate | mm, mm/mm | 01, 02 | Rate is parser-derived as 2 × half-track rate. Proxy for lateral tyre scrub. |
| Roll-centre height | mm | 01, 02 | |
| Roll-centre lateral position | mm | 02 roll | Only interesting in roll — it's zero by symmetry in heave. |
| Roll-centre migration vs travel | mm/mm | 01, 03 | Parser-derived. |
| Roll-centre migration vs roll | mm/deg | 02 | Parser-derived. |
| Roll-centre lateral migration vs roll | mm/deg | 02 | Parser-derived. The one nobody plots and everybody should. |
| Body roll | deg | 02 | Kinematic axle roll, **not** a solved sprung-mass attitude. Identically zero in a parallel bump sweep, so it is only reported where the axle rolls. |
| Mean wheel-centre travel (`heave` column) | mm | 01 | `0.5 × (Δz_left + Δz_right)` of the two wheel centres. **Not CG vertical motion** — see below. |
| Ride-height change | mm | — | Perpendicular chassis-origin-to-road distance. **Not reported.** |

**`heave` is not heave in the vehicle-dynamics sense.** It is the average of
the two wheel-centre vertical displacements. In a roll sweep it is identically
zero by construction, and in a parallel bump sweep it is numerically the same
number as wheel travel — so it is reported once, as wheel travel, and the
`heave` column stays in the CSV only. True CG vertical motion needs a solved
six-degree-of-freedom body attitude; this model grounds the chassis and solves
the linkage against it, so there is no sprung mass to move and no honest way to
report one.

**`ride_height_change` is not reported.** It is the change in perpendicular
distance from the chassis origin to the axle-local road plane, which in roll is
a second-order artefact of the plane tilting — 0 to 0.037 mm on Aurora's roll
sweep. It is not a vehicle ride height and was misleading in the table.

## E. Steering-specific (sweep 04, with 05/06 as the loaded comparison)

| Channel | Characteristic | Unit | Notes |
| --- | --- | --- | --- |
| `steering_ratio` | Steering ratio (rack) | deg/mm | `abs(deriv_steer_angle_wrt_rack_displacement_left)`. See the sign note below. |
| `steering_ratio_unitless` | Steering ratio (wheel : road wheel) | – | Only present when the geometry declares the rack travel per steering-wheel turn. See below. |
| `ackermann_error` | Ackermann error (inner − outer) | deg | Parser-derived. Positive = inner steers more = toward Ackermann. |
| `ackermann` | Ackermann | % | Parser-derived against the geometric ideal. **Only computed where the rack moves.** |
| `camber`, `caster`, `kpi` | vs steer | deg | Straight from the CSV. |
| `scrub_signed`, `trail` | vs steer | mm | Both migrate substantially with steer on your geometry. |

**Why the raw steering ratio is negative.** The exported derivative is
`d(ISO steer angle of the left wheel) / d(rack y)`. Rack +y is toward the left
of the car, which turns the wheels to the right, i.e. to a *negative* ISO
angle. The sign is a convention, not an error, so the report takes the
magnitude: 0.673–0.902 deg/mm on Aurora.

**Getting a real steering ratio.** What people usually mean by "steering ratio"
is unitless — steering-wheel degrees per road-wheel degree — and that needs a
hardware fact the kinematic model does not have. Declare either of these in the
geometry file and `steering_ratio_unitless` appears automatically:

```yaml
vehicle_config:
  steering:
    rack_travel_per_turn: 50.0    # mm of rack per steering-wheel revolution
    # or, equivalently:
    pinion_radius: 7.96           # mm; travel per turn is 2*pi*r
```

The report then adds

```
i_s = 360 / (rack_travel_per_turn * steering_ratio_deg_per_mm)
```

At Aurora's design value of 0.6833 deg/mm, a 50 mm/rev rack would give
`i_s = 10.5 : 1`. Without the field nothing changes and nothing warns — the
deg/mm channel is reported on its own.

**Why Ackermann is missing from the bump and roll sweeps.** The percentage is

```
%Ack = 100 * (|delta_inner| - |delta_outer|) / (delta_inner_ideal - |delta_outer|)
```

With the rack centred both wheels are straight, so the numerator and the
denominator are both zero and the ratio is 0/0. It is therefore computed only
in sweeps where the rack actually moves — 04, 05, 06, 09 and 10 — and its
design-condition cell in a steer sweep shows `-`, because the design condition
of a lock-to-lock sweep *is* zero rack. Read the range, not the design value.
This is also why sweep 09 exists: it is the only place Ackermann is defined at
a rolled attitude.

## F. Gradients (all analytic, from the constraint Jacobian)

Available whenever a `hub_z` target exists — i.e. every sweep except 08.

| Gradient | Unit |
| --- | --- |
| Camber gain (`d camber / d hub z`) | deg/mm |
| Bump steer rate (`d toe / d hub z`) | deg/mm |
| ISO steer gain in bump | deg/mm |
| Caster gain | deg/mm |
| KPI gain | deg/mm |
| Half-track change rate | mm/mm |
| Wheel-centre recession rate (`d x / d hub z`) | mm/mm |
| Damper rate vs wheel | mm/mm |
| Toe per rack | deg/mm |
| Steer per rack | deg/mm |
| Camber per rack | deg/mm |
| Camber recovery (`d camber / d roll`) | deg/deg — parser-derived, roll sweep only |

**Camber recovery does not exist in a parallel bump sweep.** It is
`d(camber)/d(body roll)`, and body roll is identically zero through 01, so the
derivative is undefined. Camber gain (deg/mm) is the bump-sweep equivalent and
is what 01 reports in that slot.

---

## G. Bearing misalignment (opt-in, per declared joint)

Not part of the 49 above: these appear only for joints you declare in the
geometry file's `joints:` block. An undeclared point is not analysed at all.

| Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- |
| Relative rotation `joint_<name>_rx/ry/rz` | deg | all | Rotation vector of the two bodies' relative rotation, in the housing's neutral frame. Axis-independent, so any bearing axis can be scored against it afterwards. |
| Required misalignment `misalign_<name>` | deg | all | The angle the bearing absorbs at each step. Present only when the bore axis is authored; a bore left as `optimize` has no per-step value until an axis is chosen. |
| Install offset | deg | report | Neutral-pose angle between housing and bore. Non-zero means the bearing is fitted off centre. |
| Best available | deg | report | What the joint would need with its bore axis chosen to minimise the worst case. |
| Locked clocking | deg | report | For a housing on a two-point member: the assembly clocking that minimises the worst case if the member never spins. |

**How to read it.** Misalignment is what the bearing must swallow, so lower is
better and the number you take to a catalogue is the *required* column — the
worst value anywhere in the whole sweep set, because the part has to survive
all of it. There is no pass/fail here on purpose: the tool tells you what the
geometry demands, and you choose a bearing that covers it.

**Why a wishbone pivot reads exactly zero.** The arm rotates about its own
pivot axis and nothing else, so a bore on that axis is a pure revolute. That
is both why these can be plain bushings and a free check on your hardpoints:
a non-zero reading at an inboard pivot means the geometry is not what the
model claims. On Aurora's front both bushes read 0.00 deg across the full
sweep set.

**Why the outboard ball joints read so much.** Their bore runs along the
steering axis, which is roughly perpendicular to the wishbone's pivot axis —
the opposite limit, where the bearing eats the entire arm sweep. Aurora's
front reads 21.8 deg at the LBJ and 29.8 deg at the UBJ against a 30 mm
travel range. Ordinary rod ends are rated well below that, so this is a real
constraint on the outboard hardware, not a reporting artefact.

**Two-point members give a band, not a number.** A track rod or coilover with
spherical joints at both ends carries no axial torque, so its roll about its
own axis is undetermined — the solver neither knows nor can know it. Declaring
such a housing `indeterminate` reports the *lower* bound, which assumes the
member turns freely to the best position at every instant. The report pairs it
with the locked value, which assumes it never turns. Size against the locked
value unless you know the member runs free.

**Nothing here needs a re-solve.** The sweeps export the relative rotation
itself, which does not depend on any bearing axis, so choosing axes,
re-choosing them, or asking what the best available one would be are all
answered by `susreport.py` from the CSVs alone.

## Convention traps before you diff against SUSProg

1. **`scrub_radius` is not scrub radius.** The exported `scrub_radius` follows
   ISO 8855 §7.2.10: the unsigned road-plane *distance* from contact centre to
   steering-axis ground intersection. It therefore includes mechanical trail
   and can never be negative. On your geometry:

   ```
   scrub_radius            = 54.709 mm
   steering_axis_offset_ground = −23.861 mm
   mechanical_trail        =  49.231 mm
   hypot(−23.861, 49.231)  =  54.709 mm   ✓
   ```

   Compare **`steering_axis_offset_ground`** against SUSProg's scrub radius,
   not `scrub_radius`. The parser emits it as `scrub_radius_signed` for
   exactly this reason and verifies the hypotenuse identity every run.

2. **Camber is chassis-relative.** Road-relative wheel inclination is
   explicitly not exported. In roll the difference is enormous — your
   chassis camber reaches only −0.33° at 3.3° roll, while road-relative
   reaches −3.66°.

3. **`toe_angle` ≠ `steer_angle`.** Both are exported. `toe_angle` is the
   project's side-folded convention (positive = toe-in); `steer_angle` is ISO
   vehicle-fixed. They are negatives of each other on the left and not on the
   right.

4. **Nothing here is compliance or load.** Rigid links, ideal joints, rigid
   disc tyre at nominal radius. If SUSProg is applying a loaded radius, ride
   heights will not match and neither tool is wrong.

5. **Gradients are analytic, not differenced.** Expect small disagreements
   with any tool that finite-differences between sweep steps. The Jacobian
   value is the more accurate one.

6. **`ride_height_change` and `roll` are single-axle kinematic quantities**,
   not whole-vehicle attitude. One axle cannot determine pitch.

7. **Steering ratio is signed by the rack direction, not by anything
   physical.** Rack +y is toward the left of the car and steers the wheels
   right, so the raw derivative is negative. The report takes its magnitude.

8. **Ackermann is 0/0 with the rack centred**, so it is only computed in
   sweeps where the rack moves. Its design-condition cell in a lock-to-lock
   sweep is empty for the same reason.

9. **`heave` is the mean wheel-centre displacement**, not CG vertical motion,
   which a grounded-chassis model cannot produce.

10. **A sweep switched off in `run.yaml` is invisible to the bearing table.**
    Requirements there are the worst value across the sweeps that *ran*, so
    disabling one can silently lower a bearing requirement. Check the "at"
    column before turning a sweep off.

---

## What is undefined, and why

Nothing in this section is a bug or a limitation of the tool: each is a
geometry telling you something true. The report emits a single note when it
detects the first case, rather than repeating it per channel.

### Side-view IC and the anti-geometry channels

These are undefined whenever the two wishbone inboard axes are **parallel in
side view**, because the side-view instant centre is then at infinity and every
metric built on it goes with it. That is a general condition, not an Aurora
one: tilt either inboard axis and all of these populate automatically.

On Aurora's current front geometry they happen to be exactly parallel:

```yaml
lower_wishbone_inboard_front: {z: 185}     # same
lower_wishbone_inboard_rear:  {z: 185}     # same  -> axis horizontal
upper_wishbone_inboard_front: {z: 514.82}  # same
upper_wishbone_inboard_rear:  {z: 514.82}  # same  -> axis horizontal
```

Both inboard pivot axes are exactly horizontal in side view, so the arms are
parallel there, the side-view instant centre is at infinity, and every metric
built on it is undefined. Anti-dive is a *design output of where you put the
inboard pivots* — if Aurora's real arms are level, 0% anti-dive is the correct
answer and you should record it as such rather than chase the blank.

### Anti-dive additionally needs a brake bias

**Even with a finite SVIC, `anti_dive` needs `front_brake_bias`.** It is
optional in the schema and absent from your `vehicle_config`, so anti-dive
would return `None` regardless. Add it:

```yaml
vehicle_config:
  cg_position: {x: 1127.778, y: 39.844, z: 320}
  wheelbase: 2240.00
  front_brake_bias: 0.7      # your actual bias
  driven_axle: rear          # RWD
```

`anti_squat` will stay `None` on the front axle and that is physically correct
— an undriven axle cannot squat. Don't set `driven_axle: front` to make the
number appear.


---

## Reading these on a three-wheel car

Aurora is a tadpole: two wheels at the front, one at the rear. Every axle-level
channel above is computed from the **two front wheels only**, and several of
them mean something narrower than they would on a four-wheel car. This matters
because the vocabulary is borrowed from four-wheel practice and will mislead
you if you take it at face value.

**Track, roll and roll-centre height are front-axle quantities.** `track` is
the front contact-centre separation, `roll` is the inclination of the line
between the two front wheel centres, and `roll_center_z` is the front-view
construction on those two corners. None of them knows the rear wheel exists.

**There is no roll axis.** On a four-wheel car the roll axis is the line
joining the front and rear roll centres, and load transfer splits between the
two ends according to where the CG sits along it. A single rear wheel has no
roll centre — one contact patch cannot define a front-view construction — so
there is no second point and no axis. The consequence is direct: **the front
roll-centre height carries essentially the entire geometric lateral load
transfer**, because there is no rear geometry to share it with. A roll-centre
height you would consider unremarkable on a four-wheel car is doing
substantially more work here.

**Rollover is a three-wheel problem, not an axle problem.** The stability
boundary of a tadpole is the triangle joining the three contact patches, so the
critical direction is not lateral but diagonal, toward the line from a front
contact patch to the rear one. Front track width buys you less than the same
number would on a four-wheel car, and CG longitudinal position matters as much
as CG height. Nothing in this sweep set computes that threshold — these are
kinematic channels, not a load case — so do not read a comfortable roll-centre
number as a comfortable rollover margin. (Zandieh, *Dynamics of a Three-Wheel
Vehicle with Tadpole Design*, Waterloo MASc 2014, has the derivation.)

**`ackermann` uses the front track and the wheelbase**, which is the right
construction here: the turn centre still lies on the rear axle line, and with
one rear wheel that line passes through the single rear contact patch. So the
Ackermann geometry is unaffected by the missing wheel.

**Anti-squat will stay blank on the front axle and that is correct** — an
undriven axle cannot squat. Aurora drives the rear wheel, so anti-squat belongs
to the rear model.

#### Anti-squat depends on where the drive torque is reacted

All three anti percentages are the inclination of a force line running from a
reaction point to the SVIC, scaled by `L / h`:

```
anti % = 100 * (L / h) * tan(theta),    tan(theta) = rise / run  (R -> SVIC)
```

What changes between them is **R**, and R is decided by which body reacts the
torque, not by the linkage:

| layout | torque reacted by | R | why |
| --- | --- | --- | --- |
| inboard motor / diff through halfshafts | the chassis | wheel centre | the chassis takes the torque, so only the longitudinal force reaches the linkage, applied at the hub |
| hub motor | the suspension linkage | contact patch | the arm takes the torque as well as the force; together they act along the contact-patch line |
| outboard brake | the suspension linkage | contact patch | same argument as the hub motor |
| inboard brake | the chassis | wheel centre | same argument as the halfshaft drive |

The gap between the two rows is a whole tyre radius of leverage, and on Aurora
it is the difference between **0% and 520%**. At the design pose the SVIC sits
at the arm pivot, `(-1865, 278.5)`, exactly level with the hub — so the
wheel-centre line is horizontal and the sprung answer is *zero*. From the
contact patch the same SVIC rises its full 278.5 mm over a 375 mm run:

```
tan(theta) = 278.5 / 375 = 0.743      ->  theta = 36.6 deg
h / L      = 320 / 2240  = 0.143
anti-squat = 0.743 / 0.143            =  520%
```

Because the two answers are so far apart, `drive_torque_reaction` has **no
default**: declare it as `sprung` or `unsprung` alongside `driven_axle`, or
`anti_squat` stays blank. Aurora's rear is a hub motor, so it declares
`unsprung`.

Anti-dive and anti-lift currently assume **outboard brakes** and always measure
from the contact patch. If an inboard brake ever appears on the car, they need
the same treatment as the drive side.

#### Read the anti percentages at the design pose only

All three scale by `L / h`, and on a single-corner model neither term survives
away from design:

- `h` is the CG height above the road plane, and a standalone corner places
  that plane through its own contact patch. Drive the wheel 60 mm into bump and
  `h` falls 60 mm, as though the whole car sank on one corner. With Aurora's CG
  roughly half the wheelbase back, the true drop is nearer 30 mm.
- `L` is held at the authored wheelbase, though the contact patch does move
  longitudinally as the arm swings. That one is small - about 5 mm, or 0.2% -
  and it is the lesser of the two errors by a factor of fifty.

The geometric half of the formula, `z_P / x_P`, is right everywhere; it is only
the load-transfer scaling that is not. So the rear report prints the design
value and leaves min, max and range blank, and does not plot a curve. If you
want to see how the geometry itself moves through travel, read **SVSA angle**,
which is the same line without the scaling.

A real anti-geometry envelope needs a whole-vehicle pitch and heave case, where
both axles move and `h` and `L` mean what the formula assumes.

### The rear is a centreline corner, and gets its own report

Aurora's rear is one trailing-arm corner whose wheel sits on the vehicle
centreline, so it is modelled as a standalone corner declared `side: center`
rather than as an axle. Three consequences:

1. **Its CSV columns carry no side suffix** — `damper_length`, not
   `damper_length_left`.
2. **Every axle channel is absent by definition**: track, track change, body
   roll, roll-centre height and lateral migration, rack displacement,
   Ackermann, and the axle steering ratio all need two wheels.
3. **The side-view family finally means something.** A trailing arm's SVIC is
   its pivot axis — a well-defined line — so `svic_x`, `svic_z`, `svsa`,
   `svsa_angle` and `anti_squat` all populate, where the front leaves them
   blank. Anti-squat needs the driven axle declared; anti-lift needs
   `front_brake_bias`.

#### What a centreline wheel cannot report

A wheel on the centreline has no inboard and no outboard, so every metric
measured against a lateral datum has no answer, not a small one:

| absent | because it measures |
| --- | --- |
| `camber`, `toe_angle`, `steer_angle` | a wheel-axis angle whose sign mirrors about a vehicle side |
| `caster`, `kpi`, `mechanical_trail` | an angle of, or an offset along, a kingpin axis — and an unsteered arm has none |
| `scrub_radius`, `steering_axis_offset_ground` | where that kingpin axis meets the ground, relative to the contact patch |
| `half_track` | lateral distance from the centreline the wheel is already on |
| `fvic_y`, `fvic_z`, `fvsa_length` | the front-view swing arm, whose sign follows the vehicle side |

These are removed at the source: `TrailingArmSuspension.suppressed_metric_keys()`
names them, and both the exported columns and the metric registry drop them
together. They are **not** in the CSV as blanks, and naming them under `plots:`
in `run.yaml` will not bring them back. The alternative — inventing a lateral
sign so the columns exist — would put a number in the report that means nothing,
which is worse than an absence you can explain.

Camber and toe are the two worth dwelling on, because they are physical on a
sided corner. Here they are doubly gone: the sign convention has no referent,
**and** a transverse pivot would hold both at their design values anyway. If you
want camber gain at the rear, plan obliquity is the lever — and an oblique
centreline arm is a different architecture, because its camber and toe signs
would need a vehicle side to be defined against.

#### There is no `trailing_arm_outboard` on a centreline arm

On a sided corner `TRAILING_ARM_OUTBOARD` is the arm-to-upright joint. On a
hub-motor arm the arm bolts straight to the motor axle, so no such joint exists,
and the centreline variant forbids the point: `AXLE_INBOARD` is the arm point
and the single free coordinate.

Nothing is lost by the substitution. The arm is constrained by two distances
from the two pivot mounts, which put that one point on a circle about the pivot
axis; every other carrier point is then rotated rigidly by the same rotation.
**The motion is one rotation about the pivot axis whatever point you pick**, so
the wheel path is identical. What the choice used to change — the nominal
alignment line, and the caster and KPI measured about it — is exactly the set of
channels a centreline wheel does not report.

Two requirements remain, both on `AXLE_INBOARD`: it must lie rearward of the
pivot axis, and it must not lie **on** that axis, since two distances to a point
on the axis do not define a rotation.

Both spring layouts are available on a centreline arm. A torsion bar reports
`torsion_bar_twist` as usual, but its sign needs a convention, and the vehicle
side a sided arm mirrors against does not exist here. **Positive twist is
bump**: the factor is fixed once from the design geometry so the reported angle
rises as the wheel rises.

The rear report is built by `susreport_rear.py`; the front by `susreport.py`.
See `RUNNING.md`.
