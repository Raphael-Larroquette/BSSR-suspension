# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto11\front.yaml`
- geometry SHA-256: `9d2ca11096ed1dcf...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto11\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 1.66e-06 | - |
| `02_roll` | roll | 65 | True | 4.53e-06 | - |

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
| Camber | deg | -0.0000 | -3.9882 | -0.0000 | 3.9882 |
| Caster | deg | 7.0001 | 7.0001 | 7.1058 | 0.1057 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0997 | 0.1458 | 0.2455 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.003 | 0.004 | 0.006 |
| Mechanical trail | mm | 34.196 | 34.015 | 34.299 | 0.284 |
| Half track | mm | 500.000 | 499.350 | 502.969 | 3.619 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 239.971 | 203.418 | 282.118 | 78.700 |
| Motion ratio (damper/wheel) | mm/mm | 0.7445 | 0.7164 | 0.8167 | 0.1003 |
| Roll-centre height | mm | 0.258 | -302.616 | 43.095 | 345.711 |
| FVIC lateral (y) | mm | -51607907.566 | -51607907.566 | 8248.329 | 51616155.895 |
| FVIC height (z) | mm | 26591.393 | -29.211 | 26591.393 | 26620.604 |
| FVSA length | mm | 51608414.416 | -7748.381 | 51608414.416 | 51616162.797 |
| Track change | mm | 0.000 | -1.301 | 5.938 | 7.239 |
| Steering ratio (rack) | deg/mm | 0.5166 | 0.4494 | 0.7697 | 0.3204 |
| Camber gain | deg/mm | -0.0002 | -0.0769 | 0.3085 | 0.3855 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.5031 | -0.0000 | 0.5031 |
| Camber (right) | deg | 0.0000 | -0.5031 | 0.0000 | 0.5031 |
| Caster (left) | deg | 7.0001 | 7.0001 | 7.0116 | 0.0116 |
| Caster (right) | deg | 7.0001 | 7.0001 | 7.0116 | 0.0116 |
| Toe (left) | deg | 0.0000 | -0.0587 | 0.0114 | 0.0701 |
| Toe (right) | deg | -0.0000 | -0.0587 | 0.0114 | 0.0701 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.002 | -0.000 | 0.002 |
| Half track | mm | 500.000 | 499.809 | 500.001 | 0.192 |
| Track change | mm | 0.000 | 0.000 | 0.943 | 0.943 |
| Motion ratio (damper/wheel) | mm/mm | 0.7445 | 0.7314 | 0.7602 | 0.0288 |
| Camber recovery | deg/deg | -0.0014 | -0.2939 | 0.3737 | 0.6676 |
| Roll-centre height | mm | 0.258 | -271.982 | 311.081 | 583.063 |
| Roll-centre lateral migration vs roll | mm/deg | 12094.6764 | -628445.1210 | 410848.4702 | 1039293.5912 |
| Body roll | deg | -0.0000 | -2.8764 | 2.8764 | 5.7528 |
| Steering ratio (rack) | deg/mm | 0.5166 | 0.4877 | 0.5536 | 0.0659 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 17.01 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.12 | - |
| UBJ | spherical | 9.22 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.12 | - |
| Outer Tie Rod End | rod_end | 19.84 | `02_roll` step 0 | 20.23 | 90.2 | 18.73 | 0.18 | - |
| Inner Tie Rod End | rod_end | 0.88 | `01_bump_parallel` step 0 | 1.14 | 270.1 | 0.88 | 0.14 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 61 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
