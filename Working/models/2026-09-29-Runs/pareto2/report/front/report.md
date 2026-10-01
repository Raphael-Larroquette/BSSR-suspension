# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto2\front.yaml`
- geometry SHA-256: `a4b6e2650bf0a32e...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto2\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.95e-06 | - |
| `02_roll` | roll | 65 | True | 3.70e-06 | - |

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
| Camber | deg | 0.0000 | -3.8819 | 0.0000 | 3.8819 |
| Caster | deg | 7.0001 | 7.0001 | 7.1028 | 0.1028 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0398 | 0.0538 | 0.0936 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.001 | 0.001 | 0.002 |
| Mechanical trail | mm | 34.196 | 34.130 | 34.237 | 0.107 |
| Half track | mm | 500.000 | 499.303 | 502.700 | 3.397 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 233.241 | 196.689 | 275.354 | 78.665 |
| Motion ratio (damper/wheel) | mm/mm | 0.7444 | 0.7165 | 0.8099 | 0.0935 |
| Roll-centre height | mm | 0.256 | -281.246 | 42.009 | 323.255 |
| FVIC lateral (y) | mm | 141132121.105 | -7685.798 | 141132121.105 | 141139806.903 |
| FVIC height (z) | mm | -72210.207 | -72210.207 | 37.726 | 72247.934 |
| FVSA length | mm | -141131639.578 | -141131639.578 | 8185.828 | 141139825.406 |
| Track change | mm | 0.000 | -1.394 | 5.400 | 6.793 |
| Steering ratio (rack) | deg/mm | 0.5328 | 0.4610 | 0.8002 | 0.3391 |
| Camber gain | deg/mm | -0.0001 | -0.0759 | 0.2853 | 0.3612 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.5016 | 0.0000 | 0.5016 |
| Camber (right) | deg | 0.0000 | -0.5016 | 0.0000 | 0.5016 |
| Caster (left) | deg | 7.0001 | 7.0001 | 7.0115 | 0.0114 |
| Caster (right) | deg | 7.0001 | 7.0001 | 7.0115 | 0.0114 |
| Toe (left) | deg | -0.0000 | -0.0260 | 0.0093 | 0.0354 |
| Toe (right) | deg | -0.0000 | -0.0260 | 0.0093 | 0.0354 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.001 | -0.000 | 0.001 |
| Half track | mm | 500.000 | 499.798 | 500.001 | 0.202 |
| Track change | mm | 0.000 | 0.000 | 0.938 | 0.938 |
| Motion ratio (damper/wheel) | mm/mm | 0.7444 | 0.7313 | 0.7600 | 0.0287 |
| Camber recovery | deg/deg | -0.0008 | -0.2914 | 0.3714 | 0.6627 |
| Roll-centre height | mm | 0.256 | -316.590 | 289.959 | 606.549 |
| Roll-centre lateral migration vs roll | mm/deg | 11879.6857 | -573999.3998 | 354481.2662 | 928480.6659 |
| Body roll | deg | -0.0000 | -2.8763 | 2.8763 | 5.7526 |
| Steering ratio (rack) | deg/mm | 0.5328 | 0.5021 | 0.5721 | 0.0700 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 16.90 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.05 | - |
| UBJ | spherical | 9.15 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.05 | - |
| Outer Tie Rod End | rod_end | 5.72 | `01_bump_parallel` step 21 | 5.72 | 85.7 | 0.89 | 2.77 | - |
| Inner Tie Rod End | rod_end | 17.07 | `01_bump_parallel` step 0 | 21.79 | 267.5 | 17.07 | 2.64 | - |
| Damper Lower Mount | spherical | 0.00 | `01_bump_parallel` step 18 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 18 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
