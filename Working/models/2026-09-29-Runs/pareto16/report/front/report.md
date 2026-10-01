# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto16\front.yaml`
- geometry SHA-256: `ff171c0b6ae3dbb4...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto16\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 1.57e-06 | - |
| `02_roll` | roll | 65 | True | 4.52e-06 | - |

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
| Camber | deg | -0.0000 | -2.2666 | -0.0000 | 2.2666 |
| Caster | deg | 7.0001 | 7.0001 | 7.0560 | 0.0559 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0367 | 0.0240 | 0.0607 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.001 | 0.000 | 0.001 |
| Mechanical trail | mm | 34.196 | 34.173 | 34.230 | 0.057 |
| Half track | mm | 500.000 | 492.273 | 500.000 | 7.727 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 227.905 | 188.534 | 274.371 | 85.838 |
| Motion ratio (damper/wheel) | mm/mm | 0.8149 | 0.7455 | 0.9008 | 0.1553 |
| Roll-centre height | mm | 0.889 | -94.488 | 65.819 | 160.306 |
| FVIC lateral (y) | mm | 112255516.728 | -13907.512 | 112255516.728 | 112269424.240 |
| FVIC height (z) | mm | -199554.134 | -199554.134 | -109.766 | 199444.368 |
| FVSA length | mm | -112255194.100 | -112255194.100 | 14413.162 | 112269607.263 |
| Track change | mm | 0.000 | -15.454 | 0.000 | 15.454 |
| Steering ratio (rack) | deg/mm | 0.5193 | 0.4576 | 0.6829 | 0.2253 |
| Camber gain | deg/mm | 0.0002 | -0.0512 | 0.1569 | 0.2080 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.2912 | -0.0000 | 0.2912 |
| Camber (right) | deg | 0.0000 | -0.2912 | 0.0000 | 0.2912 |
| Caster (left) | deg | 7.0001 | 7.0001 | 7.0065 | 0.0065 |
| Caster (right) | deg | 7.0001 | 7.0001 | 7.0065 | 0.0065 |
| Toe (left) | deg | 0.0000 | -0.0335 | 0.0239 | 0.0574 |
| Toe (right) | deg | -0.0000 | -0.0335 | 0.0239 | 0.0574 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.001 | 0.000 | 0.001 |
| Half track | mm | 500.000 | 498.136 | 500.000 | 1.864 |
| Track change | mm | 0.000 | -2.465 | 0.000 | 2.465 |
| Motion ratio (damper/wheel) | mm/mm | 0.8149 | 0.7909 | 0.8371 | 0.0462 |
| Camber recovery | deg/deg | 0.0015 | -0.1699 | 0.2141 | 0.3839 |
| Roll-centre height | mm | 0.889 | -41163.466 | 83106.210 | 124269.676 |
| Roll-centre lateral migration vs roll | mm/deg | -9771.1167 | -3255616.6635 | 4585303.5435 | 7840920.2069 |
| Body roll | deg | -0.0000 | -2.8806 | 2.8806 | 5.7612 |
| Steering ratio (rack) | deg/mm | 0.5193 | 0.4926 | 0.5523 | 0.0598 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 28.29 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.02 | - |
| UBJ | spherical | 8.47 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.03 | - |
| Outer Tie Rod End | rod_end | 12.74 | `01_bump_parallel` step 6 | 12.74 | 87.8 | 11.57 | 0.95 | - |
| Inner Tie Rod End | rod_end | 6.31 | `01_bump_parallel` step 18 | 7.96 | 269.4 | 6.30 | 0.91 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 1 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
