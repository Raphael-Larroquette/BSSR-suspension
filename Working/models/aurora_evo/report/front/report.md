# Front axle characteristic report

## Solve status

| sweep | status | steps | where it stopped | reason |
| --- | --- | --- | --- | --- |
| `01_bump_parallel` | ok | 65/65 | - | - |
| `02_roll` | ok | 65/65 | - | - |
| `04_steer_design` | ok | 65/65 | - | - |
| `05_steer_bump` | ok | 65/65 | - | - |
| `06_steer_droop` | ok | 65/65 | - | - |
| `08_damper_stroke` | ok | 65/65 | - | - |
| `09_steer_in_roll` | ok | 65/65 | - | - |
| `10_corner_ramp` | ok | 65/65 | - | - |

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\aurora_evo\front.yaml`
- geometry SHA-256: `c138d1e9fd6404ba...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\aurora_evo\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 65 | True | 3.95e-06 | - |
| `02_roll` | roll | 65 | True | 4.13e-06 | - |
| `04_steer_design` | steer | 65 | True | 2.55e-06 | - |
| `05_steer_bump` | steer | 65 | True | 4.09e-06 | Held at +50.8 mm wheel travel, not design height. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 2.60e-06 | Held at -50.8 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a right turn, so the LEFT wheel is outer and should be in bump, but it is at -50.8 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 3.25e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 3.54e-06 | Held at +25.0/-25.0 mm wheel travel (+3.17 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_corner_ramp` | roll_ramp_at_steer | 65 | True | 1.35e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Camber | deg | 0.0000 | -0.9059 | 0.1215 | 1.0274 |
| Caster | deg | 10.0000 | 9.9963 | 10.0287 | 0.0324 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0073 | 0.0173 | 0.0247 |
| Scrub radius (signed lateral) | mm | -1.459 | -1.463 | -1.458 | 0.005 |
| Mechanical trail | mm | 49.108 | 49.092 | 49.117 | 0.025 |
| Half track | mm | 453.542 | 445.896 | 453.629 | 7.733 |
| Wheel travel | mm | -0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 242.811 | 216.594 | 268.438 | 51.844 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.9630 | 1.9140 | 1.9942 | 0.0802 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5094 | 0.5014 | 0.5225 | 0.0210 |
| Roll-centre height | mm | 13.143 | -42.825 | 71.945 | 114.770 |
| FVIC lateral (y) | mm | -5930.606 | -106218.413 | 1327866.569 | 1434084.981 |
| FVIC height (z) | mm | 185.000 | -209472.216 | 15984.557 | 225456.773 |
| FVSA length | mm | 6386.828 | -1343837.523 | 107864.465 | 1451701.989 |
| Track change | mm | 0.000 | -15.292 | 0.175 | 15.466 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6343 | 0.7354 | 0.1011 |
| Camber gain | deg/mm | -0.0089 | -0.0284 | 0.0107 | 0.0391 |

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
| Scrub radius (signed lateral) | mm | -1.459 | -1.474 | -1.448 | 0.026 |
| Half track | mm | 453.542 | 451.344 | 453.629 | 2.286 |
| Track change | mm | 0.000 | -1.564 | 0.000 | 1.564 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.9630 | 1.9379 | 1.9839 | 0.0460 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5094 | 0.5041 | 0.5160 | 0.0120 |
| Camber recovery | deg/deg | -0.0705 | -0.1344 | -0.0059 | 0.1286 |
| Roll-centre height | mm | 13.143 | -98.182 | 13.143 | 111.325 |
| Roll-centre lateral migration vs roll | mm/deg | -310.0889 | -310.0889 | -276.3902 | 33.6987 |
| Body roll | deg | -0.0000 | -3.1688 | 3.1688 | 6.3376 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6610 | 0.7060 | 0.0449 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0112 | -3.0266 | 4.4130 | 7.4396 |
| Caster | deg | 10.0000 | 9.9994 | 10.0010 | 0.0016 |
| Toe (positive = toe-in) | deg | 0.0640 | -20.3739 | 20.2635 | 40.6374 |
| Scrub radius (signed lateral) | mm | -1.457 | -1.945 | -0.979 | 0.966 |
| Mechanical trail | mm | 49.051 | 28.754 | 63.762 | 35.008 |
| Half track | mm | 453.597 | 431.533 | 463.479 | 31.946 |
| Track change | mm | -0.000 | -14.063 | -0.000 | 14.063 |
| Damper length | mm | 242.816 | 241.044 | 244.022 | 2.977 |
| Roll-centre height | mm | 13.143 | 8.855 | 13.143 | 4.288 |
| Roll-centre lateral position | mm | 0.720 | -229.808 | 249.255 | 479.063 |
| FVIC lateral (y) | mm | -5932.735 | -6519.351 | -5230.110 | 1289.241 |
| FVIC height (z) | mm | 185.335 | 75.508 | 277.823 | 202.314 |
| FVSA length | mm | 6389.020 | 5662.137 | 6988.341 | 1326.204 |
| Rack displacement | mm | 0.094 | -28.000 | 30.000 | 58.000 |
| Ackermann | % | - | 43.98 | 54.65 | 10.67 |
| Steering ratio (rack) | deg/mm | 0.6831 | 0.6729 | 0.8090 | 0.1361 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.9195 | -3.8272 | 3.0872 | 6.9145 |
| Caster | deg | 10.0286 | 10.0266 | 10.0318 | 0.0053 |
| Toe (positive = toe-in) | deg | 0.0736 | -19.0227 | 19.7948 | 38.8176 |
| Scrub radius (signed lateral) | mm | -1.461 | -1.986 | -0.967 | 1.019 |
| Mechanical trail | mm | 49.041 | 27.905 | 64.713 | 36.808 |
| Half track | mm | 449.033 | 427.326 | 458.899 | 31.572 |
| Track change | mm | -9.158 | -24.957 | -9.158 | 15.799 |
| Damper length | mm | 216.600 | 214.891 | 217.792 | 2.901 |
| Roll-centre height | mm | -42.825 | -42.825 | -42.189 | 0.636 |
| Roll-centre lateral position | mm | -0.053 | -12.670 | 11.272 | 23.942 |
| FVIC lateral (y) | mm | -1577.531 | -1662.730 | -1461.622 | 201.108 |
| FVIC height (z) | mm | -371.822 | -373.330 | -369.492 | 3.838 |
| FVSA length | mm | 2070.170 | 1936.058 | 2162.965 | 226.908 |
| Rack displacement | mm | 0.125 | -28.000 | 32.000 | 60.000 |
| Ackermann | % | - | 64.84 | 76.36 | 11.52 |
| Steering ratio (rack) | deg/mm | 0.6341 | 0.6116 | 0.7558 | 0.1441 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0147 | -3.2084 | 4.6457 | 7.8541 |
| Caster | deg | 9.9999 | 9.9988 | 10.0007 | 0.0019 |
| Toe (positive = toe-in) | deg | 0.1092 | -20.9603 | 21.3364 | 42.2967 |
| Scrub radius (signed lateral) | mm | -1.456 | -1.951 | -0.957 | 0.993 |
| Mechanical trail | mm | 49.011 | 27.482 | 63.932 | 36.450 |
| Half track | mm | 445.971 | 424.084 | 455.251 | 31.166 |
| Track change | mm | -15.292 | -29.772 | -15.292 | 14.480 |
| Damper length | mm | 268.445 | 266.645 | 269.673 | 3.028 |
| Roll-centre height | mm | 71.945 | 68.541 | 71.945 | 3.404 |
| Roll-centre lateral position | mm | 0.195 | -40.581 | 43.355 | 83.936 |
| FVIC lateral (y) | mm | 5805.188 | 5177.657 | 6987.164 | 1809.506 |
| FVIC height (z) | mm | -1526.465 | -1730.826 | -1414.322 | 316.504 |
| FVSA length | mm | -5558.668 | -6774.894 | -4915.419 | 1859.474 |
| Rack displacement | mm | 0.125 | -27.000 | 29.000 | 56.000 |
| Ackermann | % | - | 14.91 | 38.42 | 23.50 |
| Steering ratio (rack) | deg/mm | 0.7353 | 0.7309 | 0.8594 | 0.1285 |

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
| Road camber (outer) | deg | 2.8403 | -0.2068 | 2.8403 | 3.0472 |
| Road camber (inner) | deg | -3.0445 | -3.0445 | 2.3194 | 5.3639 |
| Camber (left) | deg | -0.3252 | -3.3990 | -0.3252 | 3.0738 |
| Camber (right) | deg | 0.1210 | 0.1210 | 5.7232 | 5.6022 |
| Caster (left) | deg | 10.0100 | 10.0088 | 10.0100 | 0.0013 |
| Caster (right) | deg | 9.9963 | 9.9963 | 9.9965 | 0.0002 |
| Toe (left) | deg | -0.0066 | -0.0066 | 20.7817 | 20.7884 |
| Toe (right) | deg | 0.0105 | -24.4259 | 0.0105 | 24.4364 |
| Scrub radius (signed lateral) | mm | -1.448 | -1.448 | -1.057 | 0.391 |
| Mechanical trail | mm | 49.099 | 33.251 | 49.099 | 15.848 |
| Half track | mm | 452.795 | 452.795 | 464.819 | 12.025 |
| Track change | mm | -1.564 | -18.536 | -1.564 | 16.972 |
| Damper length | mm | 229.994 | 229.994 | 231.235 | 1.240 |
| Roll-centre height | mm | -98.182 | -98.182 | -73.019 | 25.164 |
| Roll-centre lateral position | mm | -945.314 | -945.314 | -807.140 | 138.174 |
| Body roll | deg | 3.1688 | 3.1686 | 3.1896 | 0.0210 |
| Rack displacement | mm | 0.000 | 0.000 | 32.000 | 32.000 |
| Ackermann | % | - | 108.08 | 205.21 | 97.13 |
| Steering ratio (rack) | deg/mm | 0.6610 | 0.6464 | 0.6610 | 0.0146 |

Plots: `plots/09_steer_in_roll.png`

## 10_corner_ramp  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 0.0000 | -0.2589 | 0.0000 | 0.2589 |
| Road camber (inner) | deg | 0.0000 | 0.0000 | 2.3194 | 2.3194 |
| Camber (left) | deg | 0.0000 | -3.3990 | 0.0000 | 3.3990 |
| Camber (right) | deg | 0.0000 | 0.0000 | 5.7232 | 5.7232 |
| Caster (left) | deg | 10.0000 | 10.0000 | 10.0088 | 0.0087 |
| Caster (right) | deg | 10.0000 | 9.9965 | 10.0000 | 0.0035 |
| Toe (left) | deg | -0.0000 | -0.0000 | 20.7817 | 20.7817 |
| Toe (right) | deg | -0.0000 | -24.4259 | -0.0000 | 24.4259 |
| Scrub radius (signed lateral) | mm | -1.459 | -1.459 | -1.057 | 0.402 |
| Half track | mm | 453.542 | 453.542 | 464.819 | 11.277 |
| Track change | mm | 0.000 | -18.536 | 0.000 | 18.536 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.9630 | 1.9330 | 1.9630 | 0.0300 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5094 | 0.5094 | 0.5173 | 0.0079 |
| Roll-centre height | mm | 13.143 | -73.019 | 13.143 | 86.161 |
| Roll-centre lateral position | mm | -0.000 | -807.140 | -0.000 | 807.140 |
| Body roll | deg | 0.0000 | 0.0000 | 3.1896 | 3.1896 |
| Rack displacement | mm | 0.000 | 0.000 | 32.000 | 32.000 |
| Ackermann | % | - | 86.16 | 108.13 | 21.97 |
| Steering ratio (rack) | deg/mm | 0.6833 | 0.6483 | 0.6833 | 0.0350 |

Plots: `plots/10_corner_ramp.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 20.00 | `08_damper_stroke` step 64 | - | - | 0.00 | 18.88 | - |
| UBJ | spherical | 23.75 | `06_steer_droop` step 0 | - | - | 0.00 | 21.43 | - |
| Outer Tie Rod End | rod_end | 27.19 | `04_steer_design` step 64 | 27.75 | 89.9 | 8.37 | 21.42 | - |
| Inner Tie Rod End | rod_end | 12.63 | `06_steer_droop` step 0 | 13.15 | 269.1 | 9.14 | 2.09 | - |
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
