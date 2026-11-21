# Front axle characteristic report

## Solve status

| sweep | status | steps | where it stopped | reason |
| --- | --- | --- | --- | --- |
| `10_steady_corner` | ok | 33/33 | - | - |

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\aurora_evo\front.yaml`
- geometry SHA-256: `c138d1e9fd6404ba...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\aurora_evo\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `10_steady_corner` | roll_ramp_at_steer | 33 | True | 3.31e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Road camber (outer) | deg | 0.2293 | 0.2293 | 4.7850 | 4.5558 |
| Road camber (inner) | deg | -0.2284 | -4.9768 | -0.2284 | 4.7484 |
| Camber (left) | deg | -0.2017 | -4.9510 | -0.2017 | 4.7492 |
| Camber (right) | deg | 0.2026 | 0.2026 | 4.5630 | 4.3604 |
| Caster (left) | deg | 10.0010 | 10.0010 | 10.0938 | 0.0928 |
| Caster (right) | deg | 9.9992 | 9.9963 | 10.0005 | 0.0042 |
| Toe (left) | deg | 0.9740 | 0.9740 | 14.2774 | 13.3035 |
| Toe (right) | deg | -0.9855 | -20.8624 | -0.9855 | 19.8769 |
| Scrub radius (signed lateral) | mm | -1.433 | -1.433 | -1.281 | 0.151 |
| Half track | mm | 454.433 | 446.897 | 458.083 | 11.185 |
| Track change | mm | -0.061 | -30.553 | -0.061 | 30.492 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.9594 | 1.8906 | 1.9594 | 0.0688 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5103 | 0.5103 | 0.5289 | 0.0186 |
| Roll-centre height | mm | 11.181 | -4538.560 | 7370.460 | 11909.020 |
| Roll-centre lateral position | mm | -123.437 | -24130.711 | 37102.946 | 61233.658 |
| Body roll | deg | 0.4310 | 0.4310 | 9.8876 | 9.4566 |
| Rack displacement | mm | 1.436 | 1.436 | 26.630 | 25.195 |
| Ackermann | % | - | 185.59 | 421.58 | 235.99 |
| Steering ratio (rack) | deg/mm | 0.6783 | 0.5179 | 0.6783 | 0.1603 |

Plots: `plots/10_steady_corner.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `10_steady_corner` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `10_steady_corner` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 28.75 | `10_steady_corner` step 32 | - | - | 0.00 | 2.17 | - |
| UBJ | spherical | 20.80 | `10_steady_corner` step 32 | - | - | 0.00 | 2.61 | - |
| Outer Tie Rod End | rod_end | 14.49 | `10_steady_corner` step 21 | 14.50 | 77.7 | 8.37 | 2.27 | - |
| Inner Tie Rod End | rod_end | 9.75 | `10_steady_corner` step 32 | 10.34 | 275.1 | 9.14 | 0.43 | - |
| Damper Lower Mount | spherical | 0.00 | `10_steady_corner` step 14 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `10_steady_corner` step 32 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/10_steady_corner.png`
