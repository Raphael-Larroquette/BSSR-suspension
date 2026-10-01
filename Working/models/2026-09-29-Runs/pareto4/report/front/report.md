# Front axle characteristic report

## Provenance

- geometry: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto4\front.yaml`
- geometry SHA-256: `7765c6bd2bc53dd0...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\Suspension Optimizer\BSSR-suspension\Working\models\pareto4\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.45e-06 | - |
| `02_roll` | roll | 65 | True | 2.33e-06 | - |

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
| Camber | deg | -0.0000 | -3.4986 | -0.0000 | 3.4986 |
| Caster | deg | 7.0001 | 7.0001 | 7.0913 | 0.0912 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0804 | 0.0551 | 0.1356 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.001 | 0.002 | 0.003 |
| Mechanical trail | mm | 34.196 | 34.143 | 34.272 | 0.129 |
| Half track | mm | 500.000 | 497.802 | 500.310 | 2.508 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 238.729 | 201.516 | 281.568 | 80.052 |
| Motion ratio (damper/wheel) | mm/mm | 0.7582 | 0.7271 | 0.8221 | 0.0951 |
| Roll-centre height | mm | 0.319 | -204.153 | 12.563 | 216.716 |
| FVIC lateral (y) | mm | -71261431.670 | -71261431.670 | 9199.580 | 71270631.250 |
| FVIC height (z) | mm | 45489.212 | -89.311 | 45489.212 | 45578.524 |
| FVSA length | mm | 71261946.189 | -8700.005 | 71261946.189 | 71270646.194 |
| Track change | mm | 0.000 | -4.397 | 0.620 | 5.017 |
| Steering ratio (rack) | deg/mm | 0.5169 | 0.4604 | 0.7045 | 0.2441 |
| Camber gain | deg/mm | 0.0004 | -0.0718 | 0.2506 | 0.3224 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.4617 | -0.0000 | 0.4617 |
| Camber (right) | deg | 0.0000 | -0.4617 | 0.0000 | 0.4617 |
| Caster (left) | deg | 7.0001 | 7.0001 | 7.0103 | 0.0103 |
| Caster (right) | deg | 7.0001 | 7.0001 | 7.0103 | 0.0103 |
| Toe (left) | deg | 0.0000 | -0.0746 | 0.0551 | 0.1298 |
| Toe (right) | deg | -0.0000 | -0.0746 | 0.0551 | 0.1298 |
| Scrub radius (signed lateral) | mm | 0.000 | -0.001 | 0.002 | 0.003 |
| Half track | mm | 500.000 | 499.371 | 500.000 | 0.629 |
| Track change | mm | 0.000 | 0.000 | 0.152 | 0.152 |
| Motion ratio (damper/wheel) | mm/mm | 0.7582 | 0.7451 | 0.7732 | 0.0281 |
| Camber recovery | deg/deg | 0.0035 | -0.2622 | 0.3367 | 0.5988 |
| Roll-centre height | mm | 0.319 | -161.459 | 152.720 | 314.179 |
| Roll-centre lateral migration vs roll | mm/deg | 919.2831 | -80246.8880 | 49579.2389 | 129826.1269 |
| Body roll | deg | -0.0000 | -2.8773 | 2.8773 | 5.7546 |
| Steering ratio (rack) | deg/mm | 0.5169 | 0.4928 | 0.5480 | 0.0553 |

Plots: `plots/02_roll.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 19.47 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.05 | - |
| UBJ | spherical | 9.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.06 | - |
| Outer Tie Rod End | rod_end | 13.25 | `01_bump_parallel` step 6 | 13.25 | 88.0 | 12.01 | 0.87 | - |
| Inner Tie Rod End | rod_end | 5.85 | `01_bump_parallel` step 17 | 7.30 | 269.2 | 5.83 | 0.81 | - |
| Damper Lower Mount | spherical | 0.00 | `02_roll` step 31 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `01_bump_parallel` step 21 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
