# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto7\front.yaml`
- geometry SHA-256: `4dae23585615f9ec...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto7\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.91e-06 | - |
| `02_roll` | roll | 65 | True | 4.43e-06 | - |

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
| Camber | deg | 0.0000 | -3.9087 | 0.0000 | 3.9087 |
| Caster | deg | 7.0001 | 7.0001 | 7.1036 | 0.1035 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0416 | 0.0916 | 0.1332 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.001 | 0.003 | 0.004 |
| Mechanical trail | mm | 34.196 | 34.083 | 34.241 | 0.158 |
| Half track | mm | 500.000 | 499.070 | 502.491 | 3.421 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 249.872 | 213.127 | 292.094 | 78.967 |
| Motion ratio (damper/wheel) | mm/mm | 0.7473 | 0.7211 | 0.8147 | 0.0937 |
| Roll-centre height | mm | 0.271 | -286.705 | 37.646 | 324.351 |
| FVIC lateral (y) | mm | 155192533.144 | -7756.866 | 155192533.144 | 155200290.009 |
| FVIC height (z) | mm | -84040.584 | -84040.584 | 31.027 | 84071.611 |
| FVSA length | mm | -155192055.899 | -155192055.899 | 8256.914 | 155200312.813 |
| Track change | mm | 0.000 | -1.860 | 4.982 | 6.842 |
| Steering ratio (rack) | deg/mm | 0.5213 | 0.4594 | 0.7624 | 0.3030 |
| Camber gain | deg/mm | 0.0001 | -0.0766 | 0.2976 | 0.3741 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.5009 | -0.0000 | 0.5009 |
| Camber (right) | deg | 0.0000 | -0.5009 | 0.0000 | 0.5009 |
| Caster (left) | deg | 7.0001 | 7.0001 | 7.0114 | 0.0113 |
| Caster (right) | deg | 7.0001 | 7.0001 | 7.0114 | 0.0113 |
| Toe (left) | deg | 0.0000 | -0.0356 | 0.0072 | 0.0428 |
| Toe (right) | deg | -0.0000 | -0.0356 | 0.0072 | 0.0428 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.000 | 0.000 | 0.001 |
| Half track | mm | 500.000 | 499.712 | 500.000 | 0.288 |
| Track change | mm | 0.000 | 0.000 | 0.803 | 0.803 |
| Motion ratio (damper/wheel) | mm/mm | 0.7473 | 0.7352 | 0.7618 | 0.0266 |
| Camber recovery | deg/deg | 0.0012 | -0.2880 | 0.3688 | 0.6568 |
| Roll-centre height | mm | 0.271 | -895.284 | 199.151 | 1094.435 |
| Roll-centre lateral migration vs roll | mm/deg | 9593.3964 | -974569.7470 | 792332.2232 | 1766901.9702 |
| Body roll | deg | -0.0000 | -2.8766 | 2.8766 | 5.7531 |
| Steering ratio (rack) | deg/mm | 0.5213 | 0.4945 | 0.5569 | 0.0624 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 17.48 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.06 | - |
| UBJ | spherical | 9.22 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.06 | - |
| Outer Tie Rod End | rod_end | 5.41 | `01_bump_parallel` step 6 | 5.41 | 85.3 | 4.31 | 2.05 | - |
| Inner Tie Rod End | rod_end | 13.61 | `01_bump_parallel` step 2 | 17.10 | 268.1 | 13.61 | 1.95 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 0 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 20 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
