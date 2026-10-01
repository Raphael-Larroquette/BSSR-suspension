# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto15\front.yaml`
- geometry SHA-256: `c0f7fd27054d9959...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto15\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.79e-06 | - |
| `02_roll` | roll | 65 | True | 3.27e-06 | - |

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
| Camber | deg | -0.0000 | -2.8645 | -0.0000 | 2.8645 |
| Caster | deg | 6.9999 | 6.9999 | 7.0716 | 0.0716 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.3380 | 0.2949 | 0.6329 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.008 | 0.006 | 0.014 |
| Mechanical trail | mm | 34.195 | 33.909 | 34.573 | 0.664 |
| Half track | mm | 500.000 | 494.154 | 500.000 | 5.846 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 253.334 | 213.942 | 298.722 | 84.781 |
| Motion ratio (damper/wheel) | mm/mm | 0.8045 | 0.7629 | 0.8571 | 0.0942 |
| Roll-centre height | mm | 0.257 | -59.988 | 35.069 | 95.057 |
| FVIC lateral (y) | mm | -32222594.406 | -32222594.406 | 11093.384 | 32233687.791 |
| FVIC height (z) | mm | 16580.791 | -261.319 | 16580.791 | 16842.110 |
| FVSA length | mm | 32223098.672 | -10596.522 | 32223098.672 | 32233695.194 |
| Track change | mm | 0.000 | -11.691 | 0.000 | 11.691 |
| Steering ratio (rack) | deg/mm | 0.5126 | 0.4522 | 0.6656 | 0.2134 |
| Camber gain | deg/mm | 0.0010 | -0.0657 | 0.1779 | 0.2435 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.4029 | 0.0004 | 0.4033 |
| Camber (right) | deg | 0.0000 | -0.4029 | 0.0004 | 0.4033 |
| Caster (left) | deg | 6.9999 | 6.9999 | 7.0081 | 0.0082 |
| Caster (right) | deg | 6.9999 | 6.9999 | 7.0081 | 0.0082 |
| Toe (left) | deg | -0.0000 | -0.1294 | 0.2238 | 0.3532 |
| Toe (right) | deg | -0.0000 | -0.1294 | 0.2238 | 0.3532 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.002 | 0.006 | 0.007 |
| Half track | mm | 500.000 | 498.435 | 500.002 | 1.566 |
| Track change | mm | 0.000 | -1.625 | 0.000 | 1.625 |
| Motion ratio (damper/wheel) | mm/mm | 0.8045 | 0.7898 | 0.8199 | 0.0300 |
| Camber recovery | deg/deg | 0.0085 | -0.2200 | 0.2868 | 0.5068 |
| Roll-centre height | mm | 0.257 | -23779.717 | 10286.765 | 34066.482 |
| Roll-centre lateral migration vs roll | mm/deg | -23629.4307 | -2640482.5447 | 3488352.0558 | 6128834.6005 |
| Body roll | deg | -0.0000 | -2.8806 | 2.8806 | 5.7612 |
| Steering ratio (rack) | deg/mm | 0.5126 | 0.4888 | 0.5399 | 0.0511 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 26.81 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.32 | - |
| UBJ | spherical | 8.80 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.32 | - |
| Outer Tie Rod End | rod_end | 22.18 | `02_roll` step 0 | 22.61 | 90.4 | 20.58 | 0.46 | - |
| Inner Tie Rod End | rod_end | 2.99 | `01_bump_parallel` step 3 | 3.68 | 270.3 | 2.87 | 0.46 | - |
| Damper Lower Mount | spherical | 0.00 | `01_bump_parallel` step 0 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
