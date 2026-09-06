# Suspension characteristic report

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\models\aurora\front.yaml`
- geometry SHA-256: `4141bf717bba475c...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\models\aurora\report\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.02e-06 | - |
| `02_roll` | roll | 65 | True | 4.13e-06 | - |
| `04_steer_design` | steer | 65 | True | 2.69e-06 | - |
| `05_steer_bump` | steer | 65 | True | 4.08e-06 | Held at +50.0 mm wheel travel, not design height. |
| `06_steer_droop` | steer | 65 | True | 4.90e-06 | Held at -55.0 mm wheel travel, not design height. |
| `08_damper_stroke` | damper_stroke | 65 | True | 3.25e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 3.99e-06 | Held at -25.0/+25.0 mm wheel travel (-3.19 deg roll) - this is a ROLLED sweep. |
| `10_corner_ramp` | roll_ramp_at_steer | 65 | True | 3.63e-06 | - |

## Notes

Conventions, formulas and the meaningful source sweep for every channel are documented in `CHARACTERISTICS.md`. The ones that bite most often:

- **Scrub radius** is reported as the signed lateral offset (`steering_axis_offset_ground`), which is what SUSProg calls scrub radius. The ISO `scrub_radius` column is an unsigned distance that includes mechanical trail.
- **Camber is chassis-relative.** The road-relative channel folds in body roll and is the one the tyre sees.
- **Steering ratio** is |d(ISO steer)/d(rack y)| in deg/mm. The raw derivative is negative because rack +y is toward the left of the car, which steers the wheels right. A unitless steering-wheel ratio is reported only when the geometry declares `rack_travel_per_turn` or `pinion_radius`.
- **Ackermann is only defined where the rack moves.** With the rack centred the actual and ideal inner-minus-outer differences are both zero, so the percentage is 0/0 and is not reported.
- **Body roll** is a kinematic axle attitude, `atan2(dz between wheel centres, their horizontal spacing)`, not a solved sprung-mass attitude. It is identically zero in a parallel bump sweep and is only reported where the axle actually rolls.
- **Mean wheel-centre travel** (the `heave` column) is the average of the two wheel-centre vertical displacements. It is not CG vertical motion, which a grounded-chassis kinematic model cannot produce. It is reported only where both wheels move equally, where it equals wheel travel.
- **No side-view instant centre on this geometry.** Both wishbone inboard axes are parallel in side view, so the SVIC is at infinity and SVSA, anti-dive, anti-lift and anti-squat are all undefined. That is the correct answer for level arms, not a failure; tilt an inboard axis and these channels populate. Anti-dive additionally needs `front_brake_bias` in `vehicle_config`.
- **FVIC and FVSA are tabulated but not plotted.** They pass through a singularity when the wishbones go parallel and swing to 10^5 mm. Camber gain is their bounded equivalent (`camber_gain ~ -57.296 / FVSA` in deg/mm) and is plotted instead.

## 01_bump_parallel  (heave)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -0.8833 | 0.1210 | 1.0043 |
| Caster | deg | 10.0000 | 9.9963 | 10.0279 | 0.0316 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0073 | 0.0173 | 0.0247 |
| Scrub radius (signed lateral) | mm | -1.582 | -1.587 | -1.581 | 0.006 |
| Mechanical trail | mm | 49.231 | 49.216 | 49.241 | 0.025 |
| Half track | mm | 453.542 | 444.696 | 453.627 | 8.931 |
| Wheel travel | mm | 0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 242.811 | 217.012 | 270.544 | 53.532 |
| Motion ratio (damper/wheel) | mm/mm | 0.5094 | 0.5015 | 0.5223 | 0.0208 |
| Roll-centre height | mm | 12.492 | -42.534 | 75.992 | 118.527 |
| FVIC lateral (y) | mm | -5930.606 | -83588.956 | 49231.540 | 132820.496 |
| FVIC height (z) | mm | 185.000 | -8441.559 | 12425.812 | 20867.371 |
| FVSA length | mm | 6386.849 | -49500.791 | 84957.707 | 134458.497 |
| Track change | mm | 0.000 | -17.692 | 0.170 | 17.862 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6352 | 0.7415 | 0.1062 |
| Camber gain | deg/mm | -0.0089 | -0.0280 | 0.0131 | 0.0411 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.3252 | 0.1210 | 0.4462 |
| Camber (right) | deg | 0.0000 | -0.3252 | 0.1210 | 0.4462 |
| Caster (left) | deg | 10.0000 | 9.9963 | 10.0100 | 0.0137 |
| Caster (right) | deg | 10.0000 | 9.9963 | 10.0100 | 0.0137 |
| Toe (left) | deg | -0.0000 | -0.0066 | 0.0105 | 0.0171 |
| Toe (right) | deg | -0.0000 | -0.0066 | 0.0105 | 0.0171 |
| Scrub radius (signed lateral) | mm | -1.582 | -1.599 | -1.570 | 0.029 |
| Half track | mm | 453.542 | 451.342 | 453.630 | 2.288 |
| Track change | mm | 0.000 | -1.561 | 0.000 | 1.561 |
| Motion ratio (damper/wheel) | mm/mm | 0.5094 | 0.5041 | 0.5160 | 0.0120 |
| Camber recovery | deg/deg | -0.0705 | -0.1344 | -0.0059 | 0.1286 |
| Roll-centre height | mm | 12.492 | -98.150 | 12.492 | 110.642 |
| Roll-centre lateral migration vs roll | mm/deg | -308.4378 | -308.4378 | -274.9713 | 33.4665 |
| Body roll | deg | -0.0000 | -3.1688 | 3.1688 | 6.3376 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6610 | 0.7060 | 0.0449 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -3.4556 | 6.1546 | 9.6101 |
| Caster | deg | 10.0000 | 9.9993 | 10.0014 | 0.0020 |
| Toe (positive = toe-in) | deg | -0.0000 | -26.3323 | 23.6619 | 49.9943 |
| Scrub radius (signed lateral) | mm | -1.582 | -2.174 | -1.040 | 1.134 |
| Mechanical trail | mm | 49.231 | 24.988 | 66.716 | 41.728 |
| Half track | mm | 453.542 | 424.248 | 463.602 | 39.354 |
| Track change | mm | 0.000 | -19.271 | 0.000 | 19.271 |
| Damper length | mm | 242.811 | 240.455 | 244.160 | 3.706 |
| Roll-centre height | mm | 12.492 | 6.414 | 12.492 | 6.079 |
| Roll-centre lateral position | mm | -0.000 | -300.748 | 300.748 | 601.497 |
| FVIC lateral (y) | mm | -5930.606 | -6593.908 | -5028.944 | 1564.964 |
| FVIC height (z) | mm | 185.000 | 44.363 | 289.611 | 245.248 |
| FVSA length | mm | 6386.849 | 5453.368 | 7063.424 | 1610.055 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 43.71 | 60.94 | 17.23 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6729 | 0.9022 | 0.2293 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.8833 | -4.0426 | 4.6637 | 8.7063 |
| Caster | deg | 10.0279 | 10.0257 | 10.0321 | 0.0064 |
| Toe (positive = toe-in) | deg | -0.0058 | -24.6130 | 21.6674 | 46.2804 |
| Scrub radius (signed lateral) | mm | -1.587 | -2.237 | -1.055 | 1.182 |
| Mechanical trail | mm | 49.241 | 25.807 | 68.176 | 42.369 |
| Half track | mm | 449.139 | 420.072 | 459.189 | 39.117 |
| Track change | mm | -8.805 | -27.823 | -8.805 | 19.018 |
| Damper length | mm | 217.012 | 214.731 | 218.288 | 3.557 |
| Roll-centre height | mm | -42.534 | -42.534 | -41.785 | 0.749 |
| Roll-centre lateral position | mm | -0.000 | -14.169 | 14.169 | 28.338 |
| FVIC lateral (y) | mm | -1606.550 | -1699.382 | -1451.146 | 248.236 |
| FVIC height (z) | mm | -371.139 | -373.364 | -368.196 | 5.168 |
| FVSA length | mm | 2098.250 | 1918.528 | 2198.689 | 280.161 |
| Rack displacement | mm | 0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | -1050.41 | -1050.41 | 408.31 | 1458.71 |
| Steering ratio (rack) | deg/mm | 0.6352 | 0.6126 | 0.8402 | 0.2276 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0483 | -3.8593 | 6.9309 | 10.7902 |
| Caster | deg | 10.0014 | 9.9996 | 10.0026 | 0.0030 |
| Toe (positive = toe-in) | deg | 0.0166 | -28.5230 | 26.0821 | 54.6051 |
| Scrub radius (signed lateral) | mm | -1.582 | -2.199 | -0.996 | 1.203 |
| Mechanical trail | mm | 49.216 | 21.973 | 67.387 | 45.414 |
| Half track | mm | 444.696 | 414.186 | 453.997 | 39.812 |
| Track change | mm | -17.692 | -39.312 | -17.692 | 21.620 |
| Damper length | mm | 270.544 | 268.011 | 271.953 | 3.942 |
| Roll-centre height | mm | 75.992 | 70.645 | 75.992 | 5.347 |
| Roll-centre lateral position | mm | -0.000 | -50.069 | 50.069 | 100.137 |
| FVIC lateral (y) | mm | 4796.299 | 4266.496 | 6057.499 | 1791.003 |
| FVIC height (z) | mm | -1344.385 | -1570.733 | -1244.218 | 326.515 |
| FVSA length | mm | -4538.409 | -5843.552 | -3994.005 | 1849.547 |
| Rack displacement | mm | 0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | 95.77 | -658.71 | 95.77 | 754.47 |
| Steering ratio (rack) | deg/mm | 0.7415 | 0.7374 | 0.9975 | 0.2601 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 242.811 | 212.811 | 272.811 | 60.000 |
| Wheel travel (left) | mm | -0.000 | -59.520 | 58.031 | 117.551 |
| Wheel travel (right) | mm | -0.000 | -59.520 | 58.031 | 117.551 |
| Motion ratio (damper/wheel) | mm/mm | 0.5094 | 0.5014 | 0.5237 | 0.0223 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.1210 | -3.4736 | 6.5763 | 10.0499 |
| Camber (right) | deg | -0.3252 | -3.6439 | 5.5484 | 9.1923 |
| Caster (left) | deg | 9.9963 | 9.9963 | 9.9965 | 0.0002 |
| Caster (right) | deg | 10.0100 | 10.0087 | 10.0126 | 0.0039 |
| Toe (left) | deg | 0.0105 | -27.1515 | 24.6204 | 51.7719 |
| Toe (right) | deg | -0.0066 | -25.5461 | 22.7281 | 48.2742 |
| Scrub radius (signed lateral) | mm | -1.599 | -2.504 | -0.952 | 1.552 |
| Mechanical trail | mm | 49.234 | 17.498 | 74.330 | 56.832 |
| Half track | mm | 451.342 | 418.509 | 459.297 | 40.788 |
| Track change | mm | -1.561 | -21.954 | -1.561 | 20.393 |
| Damper length | mm | 255.476 | 253.071 | 256.849 | 3.779 |
| Roll-centre height | mm | -98.150 | -164.711 | -72.060 | 92.650 |
| Roll-centre lateral position | mm | 940.340 | 800.258 | 1322.758 | 522.501 |
| Body roll | deg | -3.1688 | -3.2026 | -3.1686 | 0.0340 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | -498247.26 | -498247.26 | 1292.36 | 499539.61 |
| Steering ratio (rack) | deg/mm | 0.7060 | 0.6987 | 0.9349 | 0.2362 |

Plots: `plots/09_steer_in_roll.png`

## 10_corner_ramp  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -3.4736 | 0.0000 | 3.4736 |
| Camber (right) | deg | 0.0000 | 0.0000 | 5.5484 | 5.5484 |
| Caster (left) | deg | 10.0000 | 9.9963 | 10.0000 | 0.0037 |
| Caster (right) | deg | 10.0000 | 10.0000 | 10.0126 | 0.0126 |
| Toe (left) | deg | -0.0000 | -0.0000 | 24.6204 | 24.6204 |
| Toe (right) | deg | -0.0000 | -25.5461 | -0.0000 | 25.5461 |
| Scrub radius (signed lateral) | mm | -1.582 | -1.582 | -0.952 | 0.630 |
| Half track | mm | 453.542 | 453.542 | 460.727 | 7.185 |
| Track change | mm | 0.000 | -20.764 | 0.000 | 20.764 |
| Motion ratio (damper/wheel) | mm/mm | 0.5094 | 0.5051 | 0.5094 | 0.0044 |
| Camber recovery | deg/deg | 1.2507 | 0.9730 | 1.2507 | 0.2777 |
| Roll-centre height | mm | 12.492 | -164.711 | 12.492 | 177.203 |
| Roll-centre lateral position | mm | -0.000 | -0.000 | 1322.759 | 1322.759 |
| Roll-centre lateral migration vs roll | mm/deg | -393.2143 | -477.6487 | -393.2143 | 84.4344 |
| Body roll | deg | 0.0000 | -3.2026 | 0.0000 | 3.2026 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 6.10 | 19.51 | 13.41 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6805 | 0.7141 | 0.0336 |

Plots: `plots/10_corner_ramp.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 20.00 | `08_damper_stroke` step 64 | - | - | 0.00 | 19.38 | - |
| UBJ | spherical | 31.37 | `06_steer_droop` step 0 | - | - | 0.00 | 25.94 | - |
| Outer Tie Rod End | rod_end | 30.66 | `10_corner_ramp` step 64 | 30.68 | 91.5 | 8.37 | 26.13 | - |
| Inner Tie Rod End | rod_end | 15.14 | `06_steer_droop` step 0 | 15.46 | 267.6 | 9.14 | 3.28 | - |
| Damper Lower Mount | spherical | 0.00 | `08_damper_stroke` step 32 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `08_damper_stroke` step 11 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/08_damper_stroke.png`
- `plots/09_steer_in_roll.png`
- `plots/10_corner_ramp.png`
