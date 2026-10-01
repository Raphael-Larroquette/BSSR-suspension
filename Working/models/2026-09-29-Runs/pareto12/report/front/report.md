# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto12\front.yaml`
- geometry SHA-256: `28491977278e76f0...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto12\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 3.78e-06 | - |
| `02_roll` | roll | 65 | True | 2.48e-06 | - |

## Notes

Conventions, formulas and the meaningful source sweep for every channel are documented in `CHARACTERISTICS.md`. The ones that bite most often:

- **Scrub radius** is reported as the signed lateral offset (`steering_axis_offset_ground`), which is what SUSProg calls scrub radius. The ISO `scrub_radius` column is an unsigned distance that includes mechanical trail.
- **Camber is chassis-relative.** The road-relative channel folds in body roll and is the one the tyre sees.
- **Steering ratio** is |d(ISO steer)/d(rack y)| in deg/mm. The raw derivative is negative because rack +y is toward the left of the car, which steers the wheels right. A unitless steering-wheel ratio is reported only when the geometry declares `rack_travel_per_turn` or `pinion_radius`.
- **Ackermann is only defined where the rack moves, and only away from centre.** The formula divides by the ideal inner-minus-outer difference, which is second order in steer angle and vanishes straight-ahead, so the percentage is blanked until that difference reaches 0.25 deg (about 6 deg of outer steer on this geometry). Read the range over real lock, not the value at design.
- **A roll derivative needs roll to be the only thing moving.** Camber recovery and the roll-centre migration rates are computed only where the rack is stationary. In a sweep that ramps roll and steer together they would be derivatives along the path, dominated by the camber change from steering rather than by roll, so they are not reported there. Take them from the roll sweep.
- **Body roll** is a kinematic axle attitude, `atan2(dz between wheel centres, their horizontal spacing)`, not a solved sprung-mass attitude. It is identically zero in a parallel bump sweep and is only reported where the axle actually rolls.
- **Mean wheel-centre travel** (the `heave` column) is the average of the two wheel-centre vertical displacements. It is not CG vertical motion, which a grounded-chassis kinematic model cannot produce. It is reported only where both wheels move equally, where it equals wheel travel.
- **No side-view instant centre on this geometry.** Both wishbone inboard axes are parallel in side view, so the SVIC is at infinity and SVSA, anti-dive, anti-lift and anti-squat are all undefined. That is the correct answer for level arms, not a failure; tilt an inboard axis and these channels populate. Anti-dive additionally needs `front_brake_bias` in `vehicle_config`.
- **FVIC and FVSA are tabulated but not plotted.** They pass through a singularity when the wishbones go parallel and swing to 10^5 mm. Camber gain is their bounded equivalent (`camber_gain ~ -57.296 / FVSA` in deg/mm) and is plotted instead.

## 01_bump_parallel  (heave)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -3.4866 | 0.0000 | 3.4866 |
| Caster | deg | 7.0001 | 7.0001 | 7.0910 | 0.0910 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0850 | 0.0797 | 0.1646 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.002 | 0.002 | 0.003 |
| Mechanical trail | mm | 34.196 | 34.119 | 34.276 | 0.158 |
| Half track | mm | 500.000 | 497.799 | 500.273 | 2.474 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 243.900 | 206.742 | 286.717 | 79.975 |
| Motion ratio (damper/wheel) | mm/mm | 0.7576 | 0.7255 | 0.8202 | 0.0947 |
| Roll-centre height | mm | 0.317 | -202.814 | 12.501 | 215.315 |
| FVIC lateral (y) | mm | 46497396.449 | -8598.037 | 46497396.449 | 46505994.485 |
| FVIC height (z) | mm | -29452.428 | -29452.428 | 9.015 | 29461.442 |
| FVSA length | mm | -46496905.777 | -46496905.777 | 9098.365 | 46506004.142 |
| Track change | mm | 0.000 | -4.403 | 0.546 | 4.949 |
| Steering ratio (rack) | deg/mm | 0.5255 | 0.4672 | 0.7279 | 0.2607 |
| Camber gain | deg/mm | 0.0005 | -0.0718 | 0.2466 | 0.3184 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.4639 | 0.0000 | 0.4639 |
| Camber (right) | deg | 0.0000 | -0.4639 | 0.0000 | 0.4639 |
| Caster (left) | deg | 7.0001 | 7.0001 | 7.0103 | 0.0103 |
| Caster (right) | deg | 7.0001 | 7.0001 | 7.0103 | 0.0103 |
| Toe (left) | deg | -0.0000 | -0.0797 | 0.0749 | 0.1546 |
| Toe (right) | deg | -0.0000 | -0.0797 | 0.0749 | 0.1546 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.001 | 0.002 | 0.003 |
| Half track | mm | 500.000 | 499.367 | 500.001 | 0.633 |
| Track change | mm | 0.000 | 0.000 | 0.159 | 0.159 |
| Motion ratio (damper/wheel) | mm/mm | 0.7576 | 0.7439 | 0.7730 | 0.0290 |
| Camber recovery | deg/deg | 0.0041 | -0.2620 | 0.3375 | 0.5995 |
| Roll-centre height | mm | 0.317 | -151.954 | 161.166 | 313.120 |
| Roll-centre lateral migration vs roll | mm/deg | 912.5518 | -82877.9799 | 52766.7713 | 135644.7512 |
| Body roll | deg | -0.0000 | -2.8773 | 2.8773 | 5.7546 |
| Steering ratio (rack) | deg/mm | 0.5255 | 0.5006 | 0.5580 | 0.0574 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 19.46 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.07 | - |
| UBJ | spherical | 9.02 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.07 | - |
| Outer Tie Rod End | rod_end | 11.72 | `01_bump_parallel` step 6 | 11.73 | 87.5 | 10.47 | 1.15 | - |
| Inner Tie Rod End | rod_end | 7.40 | `01_bump_parallel` step 17 | 9.29 | 269.0 | 7.37 | 1.07 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 0 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
