# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto6\front.yaml`
- geometry SHA-256: `0411f280bdd03c7e...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto6\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 4.49e-06 | - |
| `02_roll` | roll | 65 | True | 2.83e-06 | - |

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
| Camber | deg | 0.0000 | -2.9571 | 0.0000 | 2.9571 |
| Caster | deg | 6.9999 | 6.9999 | 7.0752 | 0.0752 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0677 | 0.0502 | 0.1178 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.001 | 0.001 | 0.002 |
| Mechanical trail | mm | 34.195 | 34.147 | 34.259 | 0.112 |
| Half track | mm | 500.000 | 495.569 | 500.000 | 4.431 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 244.028 | 205.977 | 288.295 | 82.318 |
| Motion ratio (damper/wheel) | mm/mm | 0.7804 | 0.7348 | 0.8525 | 0.1177 |
| Roll-centre height | mm | 0.458 | -102.131 | 16.136 | 118.267 |
| FVIC lateral (y) | mm | -1463549.275 | -1463549.275 | 10950.024 | 1474499.300 |
| FVIC height (z) | mm | 1342.327 | -204.069 | 1342.327 | 1546.396 |
| FVSA length | mm | 1464049.891 | -10451.962 | 1464049.891 | 1474501.853 |
| Track change | mm | 0.000 | -8.861 | 0.000 | 8.861 |
| Steering ratio (rack) | deg/mm | 0.5186 | 0.4608 | 0.6960 | 0.2351 |
| Camber gain | deg/mm | 0.0003 | -0.0635 | 0.2072 | 0.2707 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.3874 | 0.0000 | 0.3874 |
| Camber (right) | deg | 0.0000 | -0.3874 | 0.0000 | 0.3874 |
| Caster (left) | deg | 6.9999 | 6.9999 | 7.0085 | 0.0086 |
| Caster (right) | deg | 6.9999 | 6.9999 | 7.0085 | 0.0086 |
| Toe (left) | deg | -0.0000 | -0.0626 | 0.0491 | 0.1117 |
| Toe (right) | deg | -0.0000 | -0.0626 | 0.0491 | 0.1117 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.001 | 0.001 | 0.002 |
| Half track | mm | 500.000 | 498.829 | 500.000 | 1.171 |
| Track change | mm | 0.000 | -0.988 | 0.000 | 0.988 |
| Motion ratio (damper/wheel) | mm/mm | 0.7804 | 0.7627 | 0.7985 | 0.0358 |
| Camber recovery | deg/deg | 0.0027 | -0.2227 | 0.2832 | 0.5060 |
| Roll-centre height | mm | 0.458 | -3620.287 | 13187.568 | 16807.855 |
| Roll-centre lateral migration vs roll | mm/deg | -7963.7854 | -1541815.7403 | 1941558.7813 | 3483374.5216 |
| Body roll | deg | -0.0000 | -2.8787 | 2.8787 | 5.7575 |
| Steering ratio (rack) | deg/mm | 0.5186 | 0.4937 | 0.5505 | 0.0567 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 23.27 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.05 | - |
| UBJ | spherical | 8.78 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.05 | - |
| Outer Tie Rod End | rod_end | 11.70 | `02_roll` step 0 | 11.71 | 87.4 | 10.49 | 1.09 | - |
| Inner Tie Rod End | rod_end | 7.38 | `01_bump_parallel` step 17 | 9.23 | 269.1 | 7.36 | 1.03 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 30 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `02_roll` step 30 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
