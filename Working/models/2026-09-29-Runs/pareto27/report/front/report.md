# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\aurora\front.yaml`
- geometry SHA-256: `32dc89d050d038f6...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\aurora\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 1.29e-06 | - |

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
| Camber | deg | 0.0000 | -0.8833 | 0.1210 | 1.0043 |
| Caster | deg | 10.0000 | 9.9963 | 10.0279 | 0.0316 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0073 | 0.0173 | 0.0247 |
| Scrub radius (signed lateral) | mm | -1.459 | -1.463 | -1.458 | 0.005 |
| Mechanical trail | mm | 49.108 | 49.092 | 49.117 | 0.025 |
| Half track | mm | 453.542 | 444.695 | 453.627 | 8.931 |
| Wheel travel | mm | 0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 242.811 | 217.012 | 270.544 | 53.532 |
| Motion ratio (damper/wheel) | mm/mm | 0.5094 | 0.5015 | 0.5223 | 0.0208 |
| Roll-centre height | mm | 13.143 | -41.985 | 76.764 | 118.749 |
| FVIC lateral (y) | mm | -5930.606 | -83588.962 | 49231.544 | 132820.505 |
| FVIC height (z) | mm | 185.000 | -8441.559 | 12425.813 | 20867.373 |
| FVSA length | mm | 6386.828 | -49500.912 | 84957.611 | 134458.523 |
| Track change | mm | 0.000 | -17.693 | 0.169 | 17.862 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6352 | 0.7415 | 0.1062 |
| Camber gain | deg/mm | -0.0089 | -0.0280 | 0.0131 | 0.0411 |

Plots: `plots/01_bump_parallel.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 18.36 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.01 | - |
| UBJ | spherical | 4.24 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.01 | - |
| Outer Tie Rod End | rod_end | 9.90 | `01_bump_parallel` step 1 | 9.90 | 86.3 | 8.37 | 0.40 | - |
| Inner Tie Rod End | rod_end | 9.14 | `01_bump_parallel` step 18 | 9.94 | 269.8 | 9.14 | 0.41 | - |
| Damper Lower Mount | spherical | 0.00 | `01_bump_parallel` step 11 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
