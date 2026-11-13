# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto21\front.yaml`
- geometry SHA-256: `bd45b9dce5fe4b3c...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto21\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 3.17e-06 | - |

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
| Camber | deg | -0.0000 | -0.7773 | 0.0807 | 0.8580 |
| Caster | deg | 6.9999 | 6.9982 | 7.0169 | 0.0187 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Scrub radius (signed lateral) | mm | 0.001 | 0.001 | 0.001 | 0.000 |
| Mechanical trail | mm | 34.195 | 34.195 | 34.195 | 0.000 |
| Half track | mm | 500.000 | 496.306 | 500.060 | 3.753 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 271.220 | 235.108 | 311.445 | 76.337 |
| Motion ratio (damper/wheel) | mm/mm | 0.7267 | 0.7171 | 0.7366 | 0.0196 |
| Roll-centre height | mm | 7.723 | 3.555 | 10.925 | 7.370 |
| FVIC lateral (y) | mm | -7303.854 | -85028.685 | 54061.974 | 139090.659 |
| FVIC height (z) | mm | 120.543 | -3382.287 | 4536.187 | 7918.474 |
| FVSA length | mm | 7804.785 | -53668.064 | 85649.269 | 139317.333 |
| Track change | mm | 0.000 | -7.387 | 0.120 | 7.507 |
| Steering ratio (rack) | deg/mm | 0.5772 | 0.5517 | 0.6072 | 0.0555 |
| Camber gain | deg/mm | -0.0073 | -0.0240 | 0.0127 | 0.0367 |

Plots: `plots/01_bump_parallel.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 8.58 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UBJ | spherical | 2.71 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| Outer Tie Rod End | rod_end | 2.57 | `01_bump_parallel` step 0 | 2.57 | 83.2 | 1.28 | 0.26 | - |
| Inner Tie Rod End | rod_end | 16.32 | `01_bump_parallel` step 4 | 16.86 | 269.8 | 16.32 | 0.27 | - |
| Damper Lower Mount | spherical | 0.00 | `01_bump_parallel` step 4 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
