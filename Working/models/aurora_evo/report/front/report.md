# Front axle characteristic report

## Solve status

| sweep | status | steps | where it stopped | reason |
| --- | --- | --- | --- | --- |
| `01_bump_parallel` | ok | 22/22 | - | - |
| `02_roll` | ok | 65/65 | - | - |
| `04_steer_design` | ok | 65/65 | - | - |
| `05_steer_bump` | ok | 65/65 | - | - |
| `06_steer_droop` | ok | 65/65 | - | - |
| `08_damper_stroke` | ok | 65/65 | - | - |
| `09_steer_in_roll` | ok | 65/65 | - | - |
| `10_corner_ramp` | ok | 65/65 | - | - |

## Provenance

- geometry: `C:\Users\General\Desktop\BSSR-suspension\Working\models\aurora_evo\front.yaml`
- geometry SHA-256: `c138d1e9fd6404ba...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\BSSR-suspension\Working\models\aurora_evo\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 1.29e-06 | - |
| `02_roll` | roll | 65 | True | 4.42e-06 | - |
| `04_steer_design` | steer | 65 | True | 2.88e-06 | - |
| `05_steer_bump` | steer | 65 | True | 2.88e-06 | Held at +50.0 mm wheel travel, not design height. Outer/inner road camber: left turn, so OUTER = RIGHT wheel and INNER = LEFT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 3.40e-06 | Held at -55.0 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a right turn, so the LEFT wheel is outer and should be in bump, but it is at -55.0 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 2.16e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 2.25e-06 | Held at +25.0/-25.0 mm wheel travel (+3.17 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_corner_ramp` | roll_ramp_at_steer | 65 | True | 3.17e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Camber | deg | 0.0000 | -0.8833 | 0.1210 | 1.0043 |
| Caster | deg | 10.0000 | 9.9963 | 10.0279 | 0.0316 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0073 | 0.0173 | 0.0247 |
| Scrub radius (signed lateral) | mm | -1.459 | -1.463 | -1.458 | 0.005 |
| Mechanical trail | mm | 49.108 | 49.092 | 49.117 | 0.025 |
| Half track | mm | 453.542 | 444.695 | 453.627 | 8.931 |
| Wheel travel | mm | 0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 242.811 | 217.012 | 270.544 | 53.532 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.9630 | 1.9146 | 1.9942 | 0.0795 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5094 | 0.5015 | 0.5223 | 0.0208 |
| Roll-centre height | mm | 13.143 | -41.985 | 76.764 | 118.749 |
| FVIC lateral (y) | mm | -5930.606 | -83588.962 | 49231.544 | 132820.505 |
| FVIC height (z) | mm | 185.000 | -8441.559 | 12425.813 | 20867.373 |
| FVSA length | mm | 6386.828 | -49500.912 | 84957.611 | 134458.523 |
| Track change | mm | 0.000 | -17.693 | 0.169 | 17.862 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6352 | 0.7415 | 0.1062 |
| Camber gain | deg/mm | -0.0089 | -0.0280 | 0.0131 | 0.0411 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.3252 | 0.1210 | 0.4462 |
| Camber (right) | deg | 0.0000 | -0.3252 | 0.1210 | 0.4462 |
| Caster (left) | deg | 10.0000 | 9.9963 | 10.0100 | 0.0137 |
| Caster (right) | deg | 10.0000 | 9.9963 | 10.0100 | 0.0137 |
| Toe (left) | deg | 0.0000 | -0.0066 | 0.0105 | 0.0171 |
| Toe (right) | deg | -0.0000 | -0.0066 | 0.0105 | 0.0171 |
| Scrub radius (signed lateral) | mm | -1.459 | -1.474 | -1.448 | 0.026 |
| Half track | mm | 453.542 | 451.344 | 453.629 | 2.286 |
| Track change | mm | 0.000 | -1.564 | 0.000 | 1.564 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.9630 | 1.9379 | 1.9839 | 0.0460 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5094 | 0.5041 | 0.5160 | 0.0120 |
| Camber recovery | deg/deg | -0.0705 | -0.1344 | -0.0059 | 0.1286 |
| Roll-centre height | mm | 13.143 | -98.182 | 13.143 | 111.325 |
| Roll-centre lateral migration vs roll | mm/deg | -310.0888 | -310.0888 | -276.3923 | 33.6965 |
| Body roll | deg | -0.0000 | -3.1688 | 3.1688 | 6.3376 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6610 | 0.7060 | 0.0449 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -3.4556 | 6.1546 | 9.6101 |
| Caster | deg | 10.0000 | 9.9993 | 10.0014 | 0.0020 |
| Toe (positive = toe-in) | deg | -0.0000 | -26.3323 | 23.6619 | 49.9943 |
| Scrub radius (signed lateral) | mm | -1.459 | -2.050 | -0.916 | 1.134 |
| Mechanical trail | mm | 49.108 | 24.925 | 66.551 | 41.626 |
| Half track | mm | 453.542 | 424.308 | 463.568 | 39.260 |
| Track change | mm | 0.000 | -19.246 | 0.000 | 19.246 |
| Damper length | mm | 242.811 | 240.455 | 244.160 | 3.706 |
| Roll-centre height | mm | 13.143 | 7.031 | 13.143 | 6.112 |
| Roll-centre lateral position | mm | -0.000 | -302.321 | 302.321 | 604.642 |
| FVIC lateral (y) | mm | -5930.606 | -6593.908 | -5028.944 | 1564.964 |
| FVIC height (z) | mm | 185.000 | 44.363 | 289.611 | 245.248 |
| FVSA length | mm | 6386.828 | 5453.423 | 7063.360 | 1609.937 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 43.95 | 60.94 | 16.98 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6729 | 0.9022 | 0.2293 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.8833 | -4.0426 | 4.6637 | 8.7063 |
| Caster | deg | 10.0279 | 10.0257 | 10.0321 | 0.0064 |
| Toe (positive = toe-in) | deg | -0.0058 | -24.6130 | 21.6674 | 46.2804 |
| Scrub radius (signed lateral) | mm | -1.463 | -2.113 | -0.931 | 1.182 |
| Mechanical trail | mm | 49.117 | 25.741 | 68.007 | 42.266 |
| Half track | mm | 449.129 | 420.119 | 459.146 | 39.027 |
| Track change | mm | -8.827 | -27.819 | -8.827 | 18.992 |
| Damper length | mm | 217.012 | 214.731 | 218.288 | 3.557 |
| Roll-centre height | mm | -41.985 | -41.985 | -41.240 | 0.746 |
| Roll-centre lateral position | mm | 0.000 | -14.201 | 14.201 | 28.402 |
| FVIC lateral (y) | mm | -1606.550 | -1699.382 | -1451.146 | 248.236 |
| FVIC height (z) | mm | -371.139 | -373.364 | -368.196 | 5.168 |
| FVSA length | mm | 2098.380 | 1918.728 | 2198.780 | 280.052 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 64.56 | 80.30 | 15.74 |
| Steering ratio (rack) | deg/mm | 0.6352 | 0.6126 | 0.8402 | 0.2276 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0483 | -3.8593 | 6.9309 | 10.7902 |
| Caster | deg | 10.0014 | 9.9996 | 10.0026 | 0.0030 |
| Toe (positive = toe-in) | deg | 0.0166 | -28.5230 | 26.0821 | 54.6051 |
| Scrub radius (signed lateral) | mm | -1.458 | -2.076 | -0.873 | 1.203 |
| Mechanical trail | mm | 49.093 | 21.917 | 67.221 | 45.304 |
| Half track | mm | 444.695 | 414.251 | 453.962 | 39.712 |
| Track change | mm | -17.693 | -39.284 | -17.693 | 21.591 |
| Damper length | mm | 270.544 | 268.011 | 271.953 | 3.942 |
| Roll-centre height | mm | 76.764 | 71.412 | 76.764 | 5.352 |
| Roll-centre lateral position | mm | 0.000 | -50.047 | 50.047 | 100.094 |
| FVIC lateral (y) | mm | 4796.299 | 4266.496 | 6057.499 | 1791.003 |
| FVIC height (z) | mm | -1344.385 | -1570.733 | -1244.218 | 326.515 |
| FVSA length | mm | -4538.609 | -5843.670 | -3994.249 | 1849.421 |
| Rack displacement | mm | 0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 16.51 | 45.85 | 29.35 |
| Steering ratio (rack) | deg/mm | 0.7415 | 0.7374 | 0.9975 | 0.2601 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 242.811 | 212.811 | 272.811 | 60.000 |
| Wheel travel (left) | mm | -0.000 | -59.520 | 58.031 | 117.551 |
| Wheel travel (right) | mm | -0.000 | -59.520 | 58.031 | 117.551 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.9630 | 1.9095 | 1.9942 | 0.0847 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5094 | 0.5014 | 0.5237 | 0.0223 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 2.8403 | -0.4341 | 2.8403 | 3.2745 |
| Road camber (inner) | deg | -3.0445 | -3.0445 | 3.0317 | 6.0763 |
| Camber (left) | deg | -0.3252 | -3.6439 | -0.3252 | 3.3187 |
| Camber (right) | deg | 0.1210 | 0.1210 | 6.5763 | 6.4553 |
| Caster (left) | deg | 10.0100 | 10.0087 | 10.0100 | 0.0013 |
| Caster (right) | deg | 9.9963 | 9.9963 | 9.9965 | 0.0002 |
| Toe (left) | deg | -0.0066 | -0.0066 | 22.7281 | 22.7347 |
| Toe (right) | deg | 0.0105 | -27.1515 | 0.0105 | 27.1620 |
| Scrub radius (signed lateral) | mm | -1.448 | -1.448 | -1.023 | 0.425 |
| Mechanical trail | mm | 49.099 | 31.525 | 49.099 | 17.574 |
| Half track | mm | 452.795 | 452.795 | 465.220 | 12.425 |
| Track change | mm | -1.564 | -21.926 | -1.564 | 20.362 |
| Damper length | mm | 229.994 | 229.994 | 231.314 | 1.320 |
| Roll-centre height | mm | -98.182 | -98.182 | -72.033 | 26.149 |
| Roll-centre lateral position | mm | -945.314 | -945.314 | -805.733 | 139.581 |
| Body roll | deg | 3.1688 | 3.1686 | 3.1946 | 0.0260 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 108.07 | 200.20 | 92.13 |
| Steering ratio (rack) | deg/mm | 0.6610 | 0.6464 | 0.6610 | 0.0146 |

Plots: `plots/09_steer_in_roll.png`

## 10_corner_ramp  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 0.0000 | -0.4458 | 0.0000 | 0.4458 |
| Road camber (inner) | deg | 0.0000 | 0.0000 | 3.0317 | 3.0317 |
| Camber (left) | deg | 0.0000 | -3.6439 | 0.0000 | 3.6439 |
| Camber (right) | deg | 0.0000 | 0.0000 | 6.5763 | 6.5763 |
| Caster (left) | deg | 10.0000 | 10.0000 | 10.0087 | 0.0087 |
| Caster (right) | deg | 10.0000 | 9.9965 | 10.0000 | 0.0035 |
| Toe (left) | deg | -0.0000 | -0.0000 | 22.7281 | 22.7281 |
| Toe (right) | deg | -0.0000 | -27.1515 | -0.0000 | 27.1515 |
| Scrub radius (signed lateral) | mm | -1.459 | -1.459 | -1.023 | 0.436 |
| Half track | mm | 453.542 | 453.542 | 465.220 | 11.678 |
| Track change | mm | 0.000 | -21.926 | 0.000 | 21.926 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.9630 | 1.9327 | 1.9630 | 0.0303 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5094 | 0.5094 | 0.5174 | 0.0080 |
| Roll-centre height | mm | 13.143 | -72.033 | 13.143 | 85.176 |
| Roll-centre lateral position | mm | -0.000 | -805.752 | -0.000 | 805.752 |
| Body roll | deg | 0.0000 | 0.0000 | 3.1946 | 3.1946 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 82.41 | 109.47 | 27.05 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6493 | 0.6833 | 0.0339 |

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
| Outer Tie Rod End | rod_end | 29.86 | `04_steer_design` step 64 | 30.68 | 91.5 | 8.37 | 26.13 | - |
| Inner Tie Rod End | rod_end | 15.14 | `06_steer_droop` step 0 | 15.46 | 267.6 | 9.14 | 3.25 | - |
| Damper Lower Mount | spherical | 0.00 | `08_damper_stroke` step 33 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `08_damper_stroke` step 9 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/08_damper_stroke.png`
- `plots/09_steer_in_roll.png`
- `plots/10_corner_ramp.png`
