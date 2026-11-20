# Front axle characteristic report

## Solve status

| sweep | status | steps | where it stopped | reason |
| --- | --- | --- | --- | --- |
| `01_bump_parallel` | ok | 65/65 | - | - |

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\CV2\front.yaml`
- geometry SHA-256: `f38153da12a40561...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\CV2\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 65 | True | 3.24e-06 | - |

## Notes

Conventions, formulas and the meaningful source sweep for every channel are documented in `docs/reference/characteristics.md`. The ones that bite most often:

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
| Camber | deg | -0.0000 | -0.2096 | 0.0001 | 0.2097 |
| Caster | deg | 8.9999 | 8.9999 | 9.0053 | 0.0054 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0088 | 0.0120 | 0.0208 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.000 | 0.000 |
| Mechanical trail | mm | 44.110 | 44.100 | 44.117 | 0.017 |
| Half track | mm | 490.000 | 481.017 | 490.032 | 9.014 |
| Wheel travel | mm | -0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 262.991 | 228.412 | 296.681 | 68.269 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4480 | 1.5175 | 0.0694 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6590 | 0.6906 | 0.0316 |
| Roll-centre height | mm | 9.727 | -92.736 | 113.811 | 206.546 |
| FVIC lateral (y) | mm | -246117.346 | -18684517.830 | 251797.787 | 18936315.617 |
| FVIC height (z) | mm | 4895.300 | -9787.127 | 549106.366 | 558893.493 |
| FVSA length | mm | 246655.929 | -251498.262 | 18693074.539 | 18944572.801 |
| Track change | mm | 0.000 | -17.965 | 0.063 | 18.028 |
| Steering ratio (rack) | deg/mm | 0.6883 | 0.6574 | 0.7246 | 0.0672 |
| Camber gain | deg/mm | -0.0002 | -0.0082 | 0.0096 | 0.0178 |

Plots: `plots/01_bump_parallel.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LBJ | spherical | 18.85 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.01 | - |
| UBJ | spherical | - | - | - | - | - | 0.01 | - |
| Outer Tie Rod End | rod_end | - | - | - | - | - | 0.03 | - |
| Inner Tie Rod End | rod_end | 0.82 | `01_bump_parallel` step 50 | 0.88 | 270.0 | 0.82 | 0.03 | - |

## Plots

- `plots/01_bump_parallel.png`
