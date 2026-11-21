# Front axle characteristic report

## Solve status

| sweep | status | steps | where it stopped | reason |
| --- | --- | --- | --- | --- |
| `10_steady_corner` | ok | 33/33 | - | - |

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\CV3\front.yaml`
- geometry SHA-256: `fc59b2fc25471eb4...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\CV3\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `10_steady_corner` | roll_ramp_at_steer | 33 | True | 2.42e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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

## 10_steady_corner  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 0.0182 | 0.0182 | 0.7970 | 0.7787 |
| Road camber (inner) | deg | -0.0143 | -0.0345 | 0.1820 | 0.2165 |
| Camber (left) | deg | -0.1567 | -2.0638 | -0.1567 | 1.9071 |
| Camber (right) | deg | 0.1606 | 0.1606 | 3.0760 | 2.9154 |
| Caster (left) | deg | 8.9999 | 8.9999 | 9.0013 | 0.0014 |
| Caster (right) | deg | 8.9999 | 8.9999 | 9.0004 | 0.0005 |
| Toe (left) | deg | 0.9953 | 0.9953 | 14.3224 | 13.3271 |
| Toe (right) | deg | -1.0035 | -16.4728 | -1.0035 | 15.4694 |
| Scrub radius (signed lateral) | mm | 0.020 | 0.020 | 0.213 | 0.193 |
| Half track | mm | 480.774 | 480.774 | 487.012 | 6.239 |
| Track change | mm | -0.040 | -10.008 | -0.040 | 9.967 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4903 | 1.4662 | 1.4903 | 0.0241 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6710 | 0.6710 | 0.6820 | 0.0110 |
| Roll-centre height | mm | 8.523 | -5680.037 | 6123.265 | 11803.302 |
| Roll-centre lateral position | mm | -120.428 | -49047.101 | 50939.224 | 99986.325 |
| Body roll | deg | 0.1749 | 0.1749 | 2.8838 | 2.7089 |
| Rack displacement | mm | 1.453 | 1.453 | 21.940 | 20.487 |
| Ackermann | % | - | 113.94 | 131.31 | 17.37 |
| Steering ratio (rack) | deg/mm | 0.6837 | 0.6441 | 0.6837 | 0.0397 |

Plots: `plots/10_steady_corner.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LBJ | spherical | 9.36 | `10_steady_corner` step 32 | - | - | 0.00 | 0.52 | - |
| UBJ | spherical | - | - | - | - | - | 0.57 | - |
| Outer Tie Rod End | rod_end | - | - | - | - | - | 0.41 | - |
| Inner Tie Rod End | rod_end | 0.68 | `10_steady_corner` step 32 | 0.68 | 270.0 | 0.82 | 0.17 | - |

## Plots

- `plots/10_steady_corner.png`
