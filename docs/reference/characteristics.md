# Characteristics

Each reported at design, min, max and range. A sweep's table is the channel list under
`sweeps.<name>.report`; **source** is the sweep giving the meaningful value. Axle
channels also have a `_lr` variant (left and right side by side).

## Alignment and steering geometry

| channel | unit | source | |
| --- | --- | --- | --- |
| `camber` | deg | 01, 02 | chassis-relative (ISO §7.1.17, about vehicle X) |
| `road_camber` | deg | 02, 09, 10 | road-relative: ISO §7.1.16 inclination about tyre X (steer-free), **signed like camber**: `-side_sign × inclination` |
| `road_camber_oi` | deg | 09, 10 | outer / inner by turn direction (axle only) |
| `caster`, `kpi` | deg | 01, 04 | |
| `toe` | deg | 01, 02 | positive = toe-in, side-folded; **not ISO** |
| `steer_angle` | deg | 04 | ISO vehicle-fixed |
| `scrub_iso` | mm | 01, 04 | ISO unsigned distance; includes trail |
| `scrub_signed` | mm | 01, 04 | `steering_axis_offset_ground`; **SUSProg's scrub radius** |
| `trail` | mm | 01, 04 | mechanical trail along tyre X |
| `half_track` | mm | 01 | |

## Instant centres and anti-geometry

| channel | unit | |
| --- | --- | --- |
| `fvic_y`, `fvic_z`, `fvsa` | mm | front view. FVSA passes through ±∞ when arms cross parallel: tabulated, never plotted. Use `camber_gain` ≈ −57.3 / FVSA deg/mm |
| `svic_x`, `svic_z`, `svsa`, `svsa_angle` | mm, deg | side view. Undefined when wishbone axes are parallel in side view (Aurora front). Trailing arm: SVIC = pivot axis |
| `anti_dive`, `anti_lift`, `anti_squat` | % | `100 (L/h) tan θ`, θ from reaction point to SVIC. Reaction point: contact patch for hub motor / outboard brake, wheel centre for inboard. Corner models: design value only |

## Springing and travel

| channel | unit | source | |
| --- | --- | --- | --- |
| `damper_length` | mm | 01, 08 | |
| `motion_ratio` | mm/mm | **08** | MR = wheel / damper, instantaneous, = 1/IR |
| `install_ratio` | mm/mm | **08** | IR = −d(damper)/d(wheel z), analytic |
| `install_ratio_sq` | - | 08 | wheel rate = spring rate × IR² |
| `damper_rate` | mm/mm | 01 | raw signed derivative; IR = −this |
| `wheel_travel` | mm | **08** | travel for a given damper stroke; set `travel:` ranges from it |

## Shock linkage (trailing arm)

| channel | unit | |
| --- | --- | --- |
| `shock_transmission_angle` | deg | shock line vs the lever it acts on (rocker, or arm for layout A), in the plane ⟂ that lever's pivot. 90 = square, 0 = toggle |
| `rod_transmission_angle` | deg | rod vs rocker lever, same definition. Rocker layouts only |
| `rocker_angle` | deg | rocker rotation relative to what carries it (chassis or arm), right-hand about `rocker_axis_a → b` |

Read the minimum over travel. Near toggle the joint forces grow without bound.

## Axle-level (two-wheel axle only)

Track, track change (+ rate), roll-centre height and lateral position, RC migration vs
travel and vs roll, body roll (kinematic axle roll, not sprung-mass attitude), Ackermann.
`heave` (mean wheel-centre z) and `ride_height_change` are CSV-only.

## Steering (04-06, 09, 10)

| channel | unit | |
| --- | --- | --- |
| `steering_ratio` | deg/mm | magnitude of steer per rack mm |
| `steering_ratio_unitless` | - | needs `rack_travel_per_turn` or `pinion_radius`: `360 / (travel × ratio)` |
| `ackermann_error` | deg | inner − outer; positive = toward Ackermann |
| `ackermann` | % | vs geometric ideal; 0/0 with the rack centred: read the range |

## Gradients (analytic, need a wheel-centre target)

Camber gain, bump steer, ISO steer gain, caster/KPI gain (deg/mm); half-track rate,
recession `dx/dz`, damper rate (mm/mm); toe/steer/camber per rack (deg/mm); camber
recovery `d camber / d roll` (roll sweep, parser-derived).

## Bearing misalignment (declared joints only)

| | |
| --- | --- |
| `joint_<name>_rx/ry/rz` | relative rotation, housing neutral frame, deg |
| `misalign_<name>` | angle absorbed per step (authored bore only) |
| install offset | neutral angle between housing and bore |
| required / required (locked) | worst over the set, with sweep and step; **size to this** |
| locked clocking | best assembly clocking for an indeterminate housing |
| best available | requirement with the optimal bore axis |

A switched-off sweep is invisible to the "required" columns; check the "at" column.

## Traps when diffing against SUSProg

1. `scrub_radius` is ISO unsigned (includes trail). Compare `scrub_signed`.
2. `camber` is chassis-relative; the tyre sees `road_camber`. They differ greatly in roll.
3. `toe` ≠ `steer_angle`: negatives on the left, not on the right.
4. Rigid links, ideal joints, rigid disc tyre: no compliance, no load.
5. Gradients are analytic, not finite-differenced.
6. `roll`, `ride_height_change`: single-axle kinematic quantities.
7. Steering ratio sign follows the rack, not physics.

## Three-wheel (Aurora) notes

- Track, roll and roll centre are front-axle only. No roll axis: the front RC carries all
  geometric lateral load transfer.
- Rollover is set by the contact-patch triangle (diagonal), not computed here.
- Centreline rear: no side suffix in CSV columns; camber, toe, steer, caster, KPI, trail,
  scrub, half track and FVIC/FVSA are absent (not blank). Torsion bar: `torsion_bar_twist`,
  positive = bump.
