# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto9\front.yaml`
- geometry SHA-256: `6fc39b54e82862ca...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto9\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 1.79e-06 | - |
| `02_roll` | roll | 65 | True | 6.09e-06 | - |

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
| Camber | deg | -0.0000 | -1.9897 | -0.0000 | 1.9897 |
| Caster | deg | 7.0000 | 7.0000 | 7.0471 | 0.0472 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.1376 | 0.1929 | 0.3305 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.003 | 0.004 | 0.007 |
| Mechanical trail | mm | 34.195 | 34.016 | 34.338 | 0.322 |
| Half track | mm | 500.000 | 499.974 | 500.243 | 0.269 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 245.581 | 215.063 | 280.956 | 65.893 |
| Motion ratio (damper/wheel) | mm/mm | 0.6265 | 0.5934 | 0.6580 | 0.0647 |
| Roll-centre height | mm | 2.347 | -78.807 | 48.212 | 127.020 |
| FVIC lateral (y) | mm | -9687480.051 | -9687480.051 | 11114.817 | 9698594.868 |
| FVIC height (z) | mm | 45466.010 | -60.912 | 45466.010 | 45526.922 |
| FVSA length | mm | 9688086.737 | -10614.972 | 9688086.737 | 9698701.709 |
| Track change | mm | 0.000 | -0.053 | 0.485 | 0.538 |
| Steering ratio (rack) | deg/mm | 0.6303 | 0.5794 | 0.7349 | 0.1555 |
| Camber gain | deg/mm | 0.0006 | -0.0523 | 0.0812 | 0.1334 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.3752 | 0.0002 | 0.3754 |
| Camber (right) | deg | 0.0000 | -0.3752 | 0.0002 | 0.3754 |
| Caster (left) | deg | 7.0000 | 7.0000 | 7.0077 | 0.0077 |
| Caster (right) | deg | 7.0000 | 7.0000 | 7.0077 | 0.0077 |
| Toe (left) | deg | -0.0000 | -0.0679 | 0.1583 | 0.2262 |
| Toe (right) | deg | -0.0000 | -0.0679 | 0.1583 | 0.2262 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.001 | 0.004 | 0.005 |
| Half track | mm | 500.000 | 499.973 | 500.016 | 0.042 |
| Track change | mm | 0.000 | 0.000 | 1.238 | 1.238 |
| Motion ratio (damper/wheel) | mm/mm | 0.6265 | 0.6105 | 0.6420 | 0.0314 |
| Camber recovery | deg/deg | 0.0057 | -0.2176 | 0.2590 | 0.4766 |
| Roll-centre height | mm | 2.347 | 2.347 | 44.102 | 41.755 |
| Roll-centre lateral migration vs roll | mm/deg | 1725.1340 | 1725.1340 | 87522.9240 | 85797.7900 |
| Body roll | deg | -0.0000 | -2.8720 | 2.8720 | 5.7441 |
| Steering ratio (rack) | deg/mm | 0.6303 | 0.6071 | 0.6586 | 0.0516 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 10.56 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.18 | - |
| UBJ | spherical | 5.18 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.17 | - |
| Outer Tie Rod End | rod_end | 11.52 | `01_bump_parallel` step 4 | 11.52 | 87.6 | 10.17 | 0.69 | - |
| Inner Tie Rod End | rod_end | 7.71 | `01_bump_parallel` step 0 | 8.83 | 269.4 | 7.69 | 0.60 | - |
| Damper Lower Mount | spherical | 0.00 | `01_bump_parallel` step 2 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `02_roll` step 52 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
