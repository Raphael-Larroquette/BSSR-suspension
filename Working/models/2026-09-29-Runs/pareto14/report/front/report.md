# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto14\front.yaml`
- geometry SHA-256: `9b4419fd7259ff4b...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto14\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 4.52e-06 | - |
| `02_roll` | roll | 65 | True | 3.65e-06 | - |

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
| Camber | deg | 0.0000 | -4.6990 | 0.1662 | 4.8652 |
| Caster | deg | 6.9999 | 6.9955 | 7.1351 | 0.1397 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.5623 | 0.3049 | 0.8672 |
| Scrub radius (signed lateral) | mm | 0.001 | -0.014 | 0.008 | 0.022 |
| Mechanical trail | mm | 34.195 | 33.900 | 34.837 | 0.936 |
| Half track | mm | 500.000 | 498.009 | 500.920 | 2.911 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 253.846 | 215.780 | 299.292 | 83.511 |
| Motion ratio (damper/wheel) | mm/mm | 0.7913 | 0.7050 | 1.0147 | 0.3096 |
| Roll-centre height | mm | 6.593 | -948.580 | 155.900 | 1104.480 |
| FVIC lateral (y) | mm | -1743.859 | -6211.220 | 142875.041 | 149086.261 |
| FVIC height (z) | mm | 29.590 | -6821.045 | 235.471 | 7056.516 |
| FVSA length | mm | 2244.054 | -142537.962 | 6715.547 | 149253.509 |
| Track change | mm | 0.000 | -3.982 | 1.841 | 5.823 |
| Steering ratio (rack) | deg/mm | 0.5202 | 0.3227 | 0.9082 | 0.5855 |
| Camber gain | deg/mm | -0.0236 | -0.2681 | 0.7657 | 1.0338 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -1.1823 | 0.1670 | 1.3493 |
| Camber (right) | deg | 0.0000 | -1.1823 | 0.1670 | 1.3493 |
| Caster (left) | deg | 6.9999 | 6.9955 | 7.0307 | 0.0352 |
| Caster (right) | deg | 6.9999 | 6.9955 | 7.0307 | 0.0352 |
| Toe (left) | deg | -0.0000 | -0.4515 | 0.2881 | 0.7396 |
| Toe (right) | deg | -0.0000 | -0.4515 | 0.2881 | 0.7396 |
| Scrub radius (signed lateral) | mm | 0.001 | -0.008 | 0.009 | 0.017 |
| Half track | mm | 500.000 | 499.136 | 500.002 | 0.866 |
| Track change | mm | 0.000 | -0.115 | 0.000 | 0.115 |
| Motion ratio (damper/wheel) | mm/mm | 0.7913 | 0.7662 | 0.8138 | 0.0475 |
| Camber recovery | deg/deg | -0.2057 | -0.6427 | 0.1799 | 0.8226 |
| Roll-centre height | mm | 6.593 | 5.838 | 18.626 | 12.787 |
| Roll-centre lateral migration vs roll | mm/deg | -91.3065 | -91.3065 | 260.9832 | 352.2897 |
| Body roll | deg | -0.0000 | -2.8821 | 2.8821 | 5.7642 |
| Steering ratio (rack) | deg/mm | 0.5202 | 0.4733 | 0.5587 | 0.0854 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 24.63 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.44 | - |
| UBJ | spherical | 12.68 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.41 | - |
| Outer Tie Rod End | rod_end | 19.36 | `01_bump_parallel` step 5 | 19.37 | 90.0 | 15.82 | 0.43 | - |
| Inner Tie Rod End | rod_end | 0.28 | `01_bump_parallel` step 18 | 0.28 | 270.1 | 0.04 | 0.14 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 26 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
