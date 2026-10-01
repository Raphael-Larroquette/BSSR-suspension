# Front axle characteristic report

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\aurora\front.yaml`
- geometry SHA-256: `5fcacbd7276d962e...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\aurora\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.63e-06 | - |

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
| Camber | deg | 0.0000 | -1.3507 | 0.1204 | 1.4711 |
| Caster | deg | 10.0000 | 9.9961 | 10.0471 | 0.0510 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0510 | 0.0002 | 0.0512 |
| Scrub radius (signed lateral) | mm | -8.057 | -8.096 | -8.054 | 0.042 |
| Mechanical trail | mm | 52.094 | 52.091 | 52.153 | 0.062 |
| Half track | mm | 424.000 | 414.509 | 424.121 | 9.612 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 242.811 | 213.393 | 271.862 | 58.469 |
| Motion ratio (damper/wheel) | mm/mm | 0.5559 | 0.5056 | 0.6243 | 0.1188 |
| Roll-centre height | mm | 15.499 | -31.964 | 67.710 | 99.673 |
| FVIC lateral (y) | mm | -4535.693 | -263030.969 | 19465.260 | 282496.229 |
| FVIC height (z) | mm | 181.292 | -3098.060 | 35921.423 | 39019.483 |
| FVSA length | mm | 4963.005 | -19290.088 | 265893.580 | 285183.668 |
| Track change | mm | 0.000 | -18.983 | 0.241 | 19.224 |
| Steering ratio (rack) | deg/mm | 0.6892 | 0.6142 | 0.7900 | 0.1757 |
| Camber gain | deg/mm | -0.0115 | -0.0467 | 0.0336 | 0.0804 |

Plots: `plots/01_bump_parallel.png`

## Plots

- `plots/01_bump_parallel.png`
