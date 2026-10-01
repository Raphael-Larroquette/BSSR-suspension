# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto17\front.yaml`
- geometry SHA-256: `2e46b4a434bf05d7...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto17\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.69e-06 | - |
| `02_roll` | roll | 65 | True | 3.11e-06 | - |

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
| Camber | deg | 0.0000 | -2.9755 | 0.0000 | 2.9755 |
| Caster | deg | 6.9999 | 6.9999 | 7.0753 | 0.0754 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0706 | 0.1070 | 0.1776 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.002 | 0.002 | 0.004 |
| Mechanical trail | mm | 34.195 | 34.072 | 34.266 | 0.194 |
| Half track | mm | 500.000 | 495.649 | 500.000 | 4.351 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 229.373 | 191.119 | 273.476 | 82.357 |
| Motion ratio (damper/wheel) | mm/mm | 0.7803 | 0.7439 | 0.8503 | 0.1064 |
| Roll-centre height | mm | 0.519 | -103.079 | 15.234 | 118.313 |
| FVIC lateral (y) | mm | 93439357.997 | -10298.739 | 93439357.997 | 93449656.736 |
| FVIC height (z) | mm | -96971.146 | -96971.146 | -28.944 | 96942.202 |
| FVSA length | mm | -93438908.316 | -93438908.316 | 10800.283 | 93449708.598 |
| Track change | mm | 0.000 | -8.702 | 0.000 | 8.702 |
| Steering ratio (rack) | deg/mm | 0.5078 | 0.4451 | 0.6884 | 0.2433 |
| Camber gain | deg/mm | -0.0001 | -0.0626 | 0.2134 | 0.2761 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.3784 | 0.0000 | 0.3784 |
| Camber (right) | deg | 0.0000 | -0.3784 | 0.0000 | 0.3784 |
| Caster (left) | deg | 6.9999 | 6.9999 | 7.0085 | 0.0086 |
| Caster (right) | deg | 6.9999 | 6.9999 | 7.0085 | 0.0086 |
| Toe (left) | deg | -0.0000 | -0.0394 | 0.0027 | 0.0421 |
| Toe (right) | deg | -0.0000 | -0.0394 | 0.0027 | 0.0421 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.001 | -0.000 | 0.001 |
| Half track | mm | 500.000 | 498.887 | 500.000 | 1.113 |
| Track change | mm | 0.000 | -0.966 | 0.000 | 0.966 |
| Motion ratio (damper/wheel) | mm/mm | 0.7803 | 0.7665 | 0.7953 | 0.0288 |
| Camber recovery | deg/deg | -0.0007 | -0.2238 | 0.2809 | 0.5047 |
| Roll-centre height | mm | 0.519 | -4847.925 | 6970.060 | 11817.985 |
| Roll-centre lateral migration vs roll | mm/deg | -6775.0119 | -712450.2503 | 1099880.9890 | 1812331.2393 |
| Body roll | deg | -0.0000 | -2.8787 | 2.8787 | 5.7573 |
| Steering ratio (rack) | deg/mm | 0.5078 | 0.4806 | 0.5415 | 0.0608 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 23.11 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.09 | - |
| UBJ | spherical | 8.69 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.09 | - |
| Outer Tie Rod End | rod_end | 17.79 | `01_bump_parallel` step 6 | 17.80 | 89.6 | 16.67 | 0.16 | - |
| Inner Tie Rod End | rod_end | 1.19 | `01_bump_parallel` step 3 | 1.51 | 269.9 | 1.19 | 0.17 | - |
| Damper Lower Mount | spherical | 0.00 | `01_bump_parallel` step 18 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
