# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto10\front.yaml`
- geometry SHA-256: `1bac1076f95553f4...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto10\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.59e-06 | - |
| `02_roll` | roll | 65 | True | 5.72e-06 | - |

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
| Camber | deg | -0.0000 | -2.9542 | -0.0000 | 2.9542 |
| Caster | deg | 6.9999 | 6.9999 | 7.0752 | 0.0753 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0867 | 0.0843 | 0.1711 |
| Scrub radius (signed lateral) | mm | -0.001 | -0.002 | 0.001 | 0.004 |
| Mechanical trail | mm | 34.195 | 34.114 | 34.277 | 0.163 |
| Half track | mm | 500.000 | 495.648 | 500.000 | 4.352 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 230.638 | 192.273 | 274.645 | 82.372 |
| Motion ratio (damper/wheel) | mm/mm | 0.7808 | 0.7479 | 0.8411 | 0.0933 |
| Roll-centre height | mm | 0.519 | -102.770 | 15.261 | 118.030 |
| FVIC lateral (y) | mm | 93055165.475 | -10293.477 | 93055165.475 | 93065458.952 |
| FVIC height (z) | mm | -96572.304 | -96572.304 | -29.058 | 96543.246 |
| FVSA length | mm | -93054715.586 | -93054715.586 | 10795.009 | 93065510.595 |
| Track change | mm | 0.000 | -8.704 | 0.000 | 8.704 |
| Steering ratio (rack) | deg/mm | 0.5270 | 0.4705 | 0.7111 | 0.2406 |
| Camber gain | deg/mm | 0.0005 | -0.0637 | 0.2037 | 0.2674 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.3933 | 0.0000 | 0.3933 |
| Camber (right) | deg | 0.0000 | -0.3933 | 0.0000 | 0.3934 |
| Caster (left) | deg | 6.9999 | 6.9999 | 7.0086 | 0.0086 |
| Caster (right) | deg | 6.9999 | 6.9999 | 7.0086 | 0.0086 |
| Toe (left) | deg | -0.0000 | -0.0812 | 0.0785 | 0.1597 |
| Toe (right) | deg | -0.0000 | -0.0812 | 0.0785 | 0.1597 |
| Scrub radius (signed lateral) | mm | -0.001 | -0.002 | 0.001 | 0.003 |
| Half track | mm | 500.000 | 498.839 | 500.000 | 1.161 |
| Track change | mm | 0.000 | -0.944 | 0.000 | 0.944 |
| Motion ratio (damper/wheel) | mm/mm | 0.7808 | 0.7687 | 0.7943 | 0.0256 |
| Camber recovery | deg/deg | 0.0042 | -0.2227 | 0.2856 | 0.5083 |
| Roll-centre height | mm | 0.519 | -4735.460 | 7243.226 | 11978.687 |
| Roll-centre lateral migration vs roll | mm/deg | -6782.1861 | -744845.7474 | 1131973.3193 | 1876819.0668 |
| Body roll | deg | -0.0000 | -2.8787 | 2.8787 | 5.7573 |
| Steering ratio (rack) | deg/mm | 0.5270 | 0.5027 | 0.5590 | 0.0563 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 23.10 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.07 | - |
| UBJ | spherical | 8.78 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.07 | - |
| Outer Tie Rod End | rod_end | 9.58 | `01_bump_parallel` step 6 | 9.59 | 86.7 | 8.34 | 1.41 | - |
| Inner Tie Rod End | rod_end | 9.55 | `01_bump_parallel` step 17 | 11.92 | 268.8 | 9.52 | 1.33 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 0 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 20 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
