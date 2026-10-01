# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto1\front.yaml`
- geometry SHA-256: `543225334cf5a986...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto1\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.10e-06 | - |
| `02_roll` | roll | 65 | True | 2.48e-06 | - |

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
| Camber | deg | 0.0000 | -2.2775 | 0.0000 | 2.2775 |
| Caster | deg | 7.0001 | 7.0001 | 7.0564 | 0.0563 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0581 | 0.0672 | 0.1253 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.001 | 0.002 | 0.003 |
| Mechanical trail | mm | 34.196 | 34.132 | 34.260 | 0.128 |
| Half track | mm | 500.000 | 492.601 | 500.000 | 7.399 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 292.059 | 252.613 | 338.294 | 85.681 |
| Motion ratio (damper/wheel) | mm/mm | 0.8129 | 0.7546 | 0.8901 | 0.1355 |
| Roll-centre height | mm | 0.577 | -89.503 | 61.131 | 150.634 |
| FVIC lateral (y) | mm | 166682107.750 | -13626.348 | 166682107.750 | 166695734.099 |
| FVIC height (z) | mm | -192417.630 | -192417.630 | -105.634 | 192311.997 |
| FVSA length | mm | -166681718.814 | -166681718.814 | 14131.753 | 166695850.567 |
| Track change | mm | 0.000 | -14.798 | 0.000 | 14.799 |
| Steering ratio (rack) | deg/mm | 0.5309 | 0.4684 | 0.7061 | 0.2377 |
| Camber gain | deg/mm | 0.0003 | -0.0519 | 0.1526 | 0.2045 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.3006 | 0.0000 | 0.3006 |
| Camber (right) | deg | 0.0000 | -0.3006 | 0.0000 | 0.3006 |
| Caster (left) | deg | 7.0001 | 7.0001 | 7.0066 | 0.0066 |
| Caster (right) | deg | 7.0001 | 7.0001 | 7.0066 | 0.0066 |
| Toe (left) | deg | -0.0000 | -0.0485 | 0.0576 | 0.1061 |
| Toe (right) | deg | -0.0000 | -0.0484 | 0.0576 | 0.1061 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.001 | 0.002 | 0.002 |
| Half track | mm | 500.000 | 498.180 | 500.000 | 1.820 |
| Track change | mm | 0.000 | -2.333 | 0.000 | 2.333 |
| Motion ratio (damper/wheel) | mm/mm | 0.8129 | 0.7914 | 0.8337 | 0.0423 |
| Camber recovery | deg/deg | 0.0027 | -0.1730 | 0.2193 | 0.3923 |
| Roll-centre height | mm | 0.577 | -22253.259 | 1420149.678 | 1442402.937 |
| Roll-centre lateral migration vs roll | mm/deg | -14335.9342 | -82757245.3593 | 84116557.3938 | 166873802.7532 |
| Body roll | deg | 0.0000 | -2.8804 | 2.8804 | 5.7608 |
| Steering ratio (rack) | deg/mm | 0.5309 | 0.5039 | 0.5648 | 0.0609 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 27.76 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.06 | - |
| UBJ | spherical | 8.47 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.06 | - |
| Outer Tie Rod End | rod_end | 10.81 | `01_bump_parallel` step 6 | 10.81 | 87.1 | 9.60 | 1.30 | - |
| Inner Tie Rod End | rod_end | 8.28 | `01_bump_parallel` step 0 | 10.49 | 269.1 | 8.27 | 1.25 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 6 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
