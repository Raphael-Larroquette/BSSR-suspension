# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto5\front.yaml`
- geometry SHA-256: `330bea0877d58d48...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto5\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 4.08e-06 | - |
| `02_roll` | roll | 65 | True | 2.15e-06 | - |

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
| Camber | deg | 0.0000 | -2.9760 | 0.0000 | 2.9760 |
| Caster | deg | 6.9999 | 6.9999 | 7.0753 | 0.0754 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0722 | 0.1095 | 0.1817 |
| Scrub radius (signed lateral) | mm | -0.001 | -0.002 | 0.002 | 0.004 |
| Mechanical trail | mm | 34.195 | 34.069 | 34.267 | 0.198 |
| Half track | mm | 500.000 | 495.649 | 500.000 | 4.351 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 227.022 | 188.645 | 271.034 | 82.389 |
| Motion ratio (damper/wheel) | mm/mm | 0.7805 | 0.7490 | 0.8469 | 0.0979 |
| Roll-centre height | mm | 0.519 | -103.109 | 15.232 | 118.341 |
| FVIC lateral (y) | mm | 93174918.196 | -10298.427 | 93174918.196 | 93185216.624 |
| FVIC height (z) | mm | -96696.296 | -96696.296 | -28.931 | 96667.365 |
| FVSA length | mm | -93174468.372 | -93174468.372 | 10799.971 | 93185268.343 |
| Track change | mm | 0.000 | -8.701 | 0.000 | 8.701 |
| Steering ratio (rack) | deg/mm | 0.5085 | 0.4463 | 0.6895 | 0.2432 |
| Camber gain | deg/mm | -0.0001 | -0.0626 | 0.2137 | 0.2763 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.3784 | 0.0000 | 0.3784 |
| Camber (right) | deg | 0.0000 | -0.3784 | 0.0000 | 0.3784 |
| Caster (left) | deg | 6.9999 | 6.9999 | 7.0085 | 0.0086 |
| Caster (right) | deg | 6.9999 | 6.9999 | 7.0085 | 0.0086 |
| Toe (left) | deg | -0.0000 | -0.0396 | 0.0023 | 0.0419 |
| Toe (right) | deg | -0.0000 | -0.0396 | 0.0023 | 0.0419 |
| Scrub radius (signed lateral) | mm | -0.001 | -0.002 | -0.001 | 0.001 |
| Half track | mm | 500.000 | 498.886 | 500.000 | 1.114 |
| Track change | mm | 0.000 | -0.967 | 0.000 | 0.967 |
| Motion ratio (damper/wheel) | mm/mm | 0.7805 | 0.7689 | 0.7938 | 0.0249 |
| Camber recovery | deg/deg | -0.0006 | -0.2238 | 0.2808 | 0.5046 |
| Roll-centre height | mm | 0.519 | -4856.897 | 6950.741 | 11807.639 |
| Roll-centre lateral migration vs roll | mm/deg | -6774.8409 | -710142.7872 | 1097612.0006 | 1807754.7878 |
| Body roll | deg | -0.0000 | -2.8787 | 2.8787 | 5.7573 |
| Steering ratio (rack) | deg/mm | 0.5085 | 0.4815 | 0.5423 | 0.0608 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 23.11 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.09 | - |
| UBJ | spherical | 8.68 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.09 | - |
| Outer Tie Rod End | rod_end | 11.57 | `02_roll` step 0 | 11.57 | 87.3 | 10.49 | 1.05 | - |
| Inner Tie Rod End | rod_end | 7.41 | `01_bump_parallel` step 3 | 9.25 | 269.2 | 7.41 | 1.03 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 0 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `02_roll` step 35 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
