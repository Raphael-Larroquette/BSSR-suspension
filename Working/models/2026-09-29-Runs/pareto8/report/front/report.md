# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto8\front.yaml`
- geometry SHA-256: `8a165f32f9283faf...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto8\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 4.80e-06 | - |
| `02_roll` | roll | 65 | True | 4.41e-06 | - |

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
| Camber | deg | -0.0000 | -4.0168 | 2.4385 | 6.4553 |
| Caster | deg | 7.0000 | 6.9533 | 7.1064 | 0.1530 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0128 | 0.0301 | 0.0428 |
| Scrub radius (signed lateral) | mm | 0.000 | 0.000 | 0.001 | 0.001 |
| Mechanical trail | mm | 34.196 | 34.163 | 34.206 | 0.043 |
| Half track | mm | 500.000 | 489.441 | 500.000 | 10.559 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 197.448 | 154.672 | 243.935 | 89.263 |
| Motion ratio (damper/wheel) | mm/mm | 0.8560 | 0.8345 | 0.8607 | 0.0262 |
| Roll-centre height | mm | 0.310 | -71.856 | 144.424 | 216.280 |
| FVIC lateral (y) | mm | -574.676 | -929.068 | 44.099 | 973.168 |
| FVIC height (z) | mm | 0.666 | -96.151 | 522.497 | 618.648 |
| FVSA length | mm | 1074.677 | 461.815 | 1531.463 | 1069.648 |
| Track change | mm | 0.000 | -21.118 | 0.000 | 21.118 |
| Steering ratio (rack) | deg/mm | 0.5371 | 0.3957 | 0.5911 | 0.1954 |
| Camber gain | deg/mm | -0.0534 | -0.1329 | -0.0399 | 0.0930 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -1.5646 | 1.1999 | 2.7645 |
| Camber (right) | deg | 0.0000 | -1.5646 | 1.1999 | 2.7645 |
| Caster (left) | deg | 7.0000 | 6.9755 | 7.0369 | 0.0615 |
| Caster (right) | deg | 7.0000 | 6.9755 | 7.0369 | 0.0615 |
| Toe (left) | deg | -0.0000 | -0.0128 | 0.0254 | 0.0382 |
| Toe (right) | deg | -0.0000 | -0.0128 | 0.0254 | 0.0382 |
| Scrub radius (signed lateral) | mm | 0.000 | 0.000 | 0.001 | 0.001 |
| Half track | mm | 500.000 | 497.901 | 500.000 | 2.099 |
| Track change | mm | 0.000 | -2.764 | 0.000 | 2.764 |
| Motion ratio (damper/wheel) | mm/mm | 0.8560 | 0.8454 | 0.8607 | 0.0154 |
| Camber recovery | deg/deg | -0.4662 | -0.6380 | -0.3777 | 0.2603 |
| Roll-centre height | mm | 0.310 | -936.666 | 0.310 | 936.975 |
| Roll-centre lateral migration vs roll | mm/deg | -30973.5285 | -30973.5285 | 4308.8037 | 35282.3321 |
| Body roll | deg | -0.0000 | -2.8791 | 2.8791 | 5.7581 |
| Steering ratio (rack) | deg/mm | 0.5371 | 0.4920 | 0.5658 | 0.0738 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 22.49 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.02 | - |
| UBJ | spherical | 5.17 | `01_bump_parallel` step 21 | - | - | 0.00 | 0.02 | - |
| Outer Tie Rod End | rod_end | 13.22 | `01_bump_parallel` step 0 | 13.22 | 80.8 | 8.17 | 0.31 | - |
| Inner Tie Rod End | rod_end | 4.58 | `01_bump_parallel` step 18 | 5.30 | 270.2 | 4.58 | 0.38 | - |
| Damper Lower Mount | spherical | 0.00 | `01_bump_parallel` step 0 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
