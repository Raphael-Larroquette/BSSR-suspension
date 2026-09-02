# Everything you can get out of this sweep set

49 distinct characteristics, each reported four ways by `susreport.py`: value
at design condition, minimum, maximum, and range across the sweep. Times two
sides. Times eight sweeps where applicable — **347 numbers** from your current
geometry.

Legend for "best source": which sweep gives the *meaningful* version. Most
channels are present in every sweep, but e.g. camber recovery only means
something in the roll sweep.
---

## A. Alignment and steering geometry (corner)

| Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- |
| Camber | deg | 01 bump, 02 roll | **Chassis-relative.** See the road-relative row below. |
| Camber, road-relative | deg | 02 roll | Derived by the parser: `camber − roll`. Not exported by the solver. This is what the tyre sees. |
| Caster | deg | 01, 04 | |
| Kingpin inclination | deg | 01, 04 | |
| Toe (positive = toe-in) | deg | 01 bump, 02 roll | Project convention, **not** ISO. |
| ISO steer angle | deg | 04 steer | The ISO vehicle-fixed angle, reported alongside toe. Use this one when comparing to anything ISO-based. |
| Scrub radius (ISO unsigned) | mm | 01, 04 | **Read the caveat in §E.** |
| Scrub radius (signed lateral) | mm | 01, 04 | Parser alias for `steering_axis_offset_ground`. **This is the number SUSProg calls scrub radius.** |
| Steering-axis offset at ground | mm | 01, 04 | Signed, positive = axis inboard of the contact centre. |
| Mechanical trail | mm | 01, 04 | ISO caster offset at ground, wheel-relative — not a raw chassis-X difference. |
| Half track | mm | 01 | Per corner. |

## B. Instant centres and swing arms (corner)

| Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- |
| Front-view IC, y and z | mm | 01, 02 | Goes to ±10⁴ mm and flips sign when the arms pass through parallel. Not a bug. |
| Front-view swing-arm length | mm | 01 | Sets camber gain. |
| Side-view IC, x and z | mm | 01 | **NaN on your geometry** — see §F. |
| Side-view swing-arm length / angle | mm, deg | 01 | Same. |
| Anti-dive / anti-lift / anti-squat | % | 01 | **All NaN on your geometry** — see §F. |

## C. Springing and travel

| Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- |
| Damper length | mm | 01, 08 | |
| Motion ratio (damper/wheel) | mm/mm | 01 | Analytic, from the Jacobian — not finite-differenced. |
| Motion ratio squared | – | 01 | Wheel rate = spring rate × MR². Parser-derived. |
| Damper rate vs wheel | mm/mm | 01 | The raw signed derivative; MR is its negation. |
| Wheel travel available for a given damper stroke | mm | **08 damper stroke** | The whole reason sweep 08 exists. |

## D. Axle-level behaviour

| Characteristic | Unit | Best source | Notes |
| --- | --- | --- | --- |
| Track, track change, track change rate | mm, mm/mm | 01, 02 | Rate is parser-derived as 2 × half-track rate. Proxy for lateral tyre scrub. |
| Roll-centre height | mm | 01, 02 | |
| Roll-centre lateral position | mm | 02 roll | Only interesting in roll — it's zero by symmetry in heave. |
| Roll-centre migration vs travel | mm/mm | 01, 03 | Parser-derived. |
| Roll-centre migration vs roll | mm/deg | 02 | Parser-derived. |
| Roll-centre lateral migration vs roll | mm/deg | 02 | Parser-derived. The one nobody plots and everybody should. |
| Body roll | deg | 02 | Kinematic axle roll, **not** a solved sprung-mass attitude. |
| Heave | mm | 01 | Sanity check: should be ~0 in a pure roll sweep. |
| Ride-height change | mm | 01 | Perpendicular chassis-origin-to-road distance. Not a full-vehicle ride height. |

## E. Steering-specific (sweep 04, with 05/06 as the loaded comparison)

| Characteristic | Unit | Notes |
| --- | --- | --- |
| Steering ratio | deg/mm | Analytic `deriv_steer_angle_wrt_rack_displacement`. |
| Ackermann error (inner − outer) | deg | Parser-derived. Positive = inner steers more = toward Ackermann. |
| Ackermann | % | Parser-derived against the geometric ideal. `NaN` at exactly zero steer (0/0) — read the range, not the design value. |
| Camber / caster / KPI vs steer | deg | Straight from the CSV. |
| Scrub and trail vs steer | mm | Both migrate substantially with steer on your geometry. |

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

---

## What is NaN on your geometry, and why

Two independent blockers, both fixable, neither a bug:

**Side-view IC and all three anti-* metrics are NaN.**

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
answer and you should record it as such rather than chase the NaN.

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
