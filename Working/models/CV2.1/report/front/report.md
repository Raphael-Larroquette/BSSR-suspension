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

- geometry: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV2.1\front.yaml`
- geometry SHA-256: `41f9fdec47b315f0...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV2.1\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.76e-06 | - |
| `02_roll` | roll | 65 | True | 1.76e-06 | - |
| `04_steer_design` | steer | 65 | True | 3.14e-06 | - |
| `05_steer_bump` | steer | 65 | True | 3.54e-06 | Held at +50.0 mm wheel travel, not design height. Outer/inner road camber: left turn, so OUTER = RIGHT wheel and INNER = LEFT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 3.48e-06 | Held at -55.0 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a left turn, so the RIGHT wheel is outer and should be in bump, but it is at -55.0 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: left turn, so OUTER = RIGHT wheel and INNER = LEFT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 1.09e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 2.77e-06 | Held at +25.0/-25.0 mm wheel travel (+2.93 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_corner_ramp` | roll_ramp_at_steer | 65 | True | 3.89e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Camber | deg | -0.0000 | -0.3172 | 0.0246 | 0.3417 |
| Caster | deg | 8.9470 | 8.9465 | 8.9546 | 0.0081 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.1117 | 0.1103 | 0.2221 |
| Scrub radius (signed lateral) | mm | 0.448 | 0.446 | 0.450 | 0.005 |
| Mechanical trail | mm | 43.678 | 43.585 | 43.769 | 0.185 |
| Half track | mm | 490.000 | 478.395 | 490.116 | 11.721 |
| Wheel travel | mm | 0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 262.991 | 229.069 | 299.487 | 70.418 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4932 | 1.4561 | 1.5132 | 0.0571 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6697 | 0.6608 | 0.6868 | 0.0259 |
| Roll-centre height | mm | 18.188 | -81.877 | 133.603 | 215.480 |
| FVIC lateral (y) | mm | -23321.996 | -201863.361 | 120411.005 | 322274.366 |
| FVIC height (z) | mm | 883.868 | -19110.621 | 25932.767 | 45043.388 |
| FVSA length | mm | 23828.394 | -121433.001 | 204008.974 | 325441.975 |
| Track change | mm | 0.000 | -23.210 | 0.232 | 23.442 |
| Steering ratio (rack) | deg/mm | 0.6875 | 0.6567 | 0.7267 | 0.0700 |
| Camber gain | deg/mm | -0.0026 | -0.0106 | 0.0073 | 0.0179 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.1099 | 0.0247 | 0.1346 |
| Camber (right) | deg | -0.0000 | -0.1099 | 0.0247 | 0.1346 |
| Caster (left) | deg | 8.9470 | 8.9465 | 8.9496 | 0.0031 |
| Caster (right) | deg | 8.9470 | 8.9465 | 8.9496 | 0.0031 |
| Toe (left) | deg | -0.0000 | -0.0375 | 0.0434 | 0.0810 |
| Toe (right) | deg | 0.0000 | -0.0375 | 0.0434 | 0.0810 |
| Scrub radius (signed lateral) | mm | 0.448 | 0.445 | 0.451 | 0.006 |
| Half track | mm | 490.000 | 487.142 | 490.122 | 2.980 |
| Track change | mm | 0.000 | -2.498 | 0.000 | 2.498 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4932 | 1.4738 | 1.5081 | 0.0343 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6697 | 0.6631 | 0.6785 | 0.0154 |
| Camber recovery | deg/deg | -0.0226 | -0.0520 | 0.0081 | 0.0601 |
| Roll-centre height | mm | 18.188 | -176.338 | 18.188 | 194.526 |
| Roll-centre lateral migration vs roll | mm/deg | -448.8050 | -448.8050 | -414.0793 | 34.7257 |
| Body roll | deg | -0.0000 | -2.9333 | 2.9333 | 5.8666 |
| Steering ratio (rack) | deg/mm | 0.6875 | 0.6728 | 0.7029 | 0.0301 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -3.0505 | 6.1957 | 9.2462 |
| Caster | deg | 8.9470 | 8.9469 | 8.9473 | 0.0004 |
| Toe (positive = toe-in) | deg | -0.0000 | -28.4913 | 23.4391 | 51.9304 |
| Scrub radius (signed lateral) | mm | 0.448 | -0.053 | 0.868 | 0.921 |
| Mechanical trail | mm | 43.678 | 21.695 | 60.591 | 38.896 |
| Half track | mm | 490.000 | 461.206 | 498.541 | 37.336 |
| Track change | mm | 0.000 | -20.332 | 0.000 | 20.332 |
| Damper length | mm | 262.991 | 260.071 | 264.484 | 4.414 |
| Roll-centre height | mm | 18.188 | 9.828 | 18.188 | 8.360 |
| Roll-centre lateral position | mm | -0.000 | -310.227 | 310.227 | 620.454 |
| FVIC lateral (y) | mm | -23321.996 | -26795.573 | -18606.141 | 8189.432 |
| FVIC height (z) | mm | 883.868 | 213.067 | 1377.274 | 1164.207 |
| FVSA length | mm | 23828.395 | 19068.523 | 27328.745 | 8260.222 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 74.39 | 107.28 | 32.89 |
| Steering ratio (rack) | deg/mm | 0.6875 | 0.6641 | 1.1283 | 0.4642 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.3172 | -3.2030 | 5.5034 | 8.7065 |
| Caster | deg | 8.9546 | 8.9541 | 8.9558 | 0.0017 |
| Toe (positive = toe-in) | deg | 0.1103 | -27.2775 | 22.2484 | 49.5259 |
| Scrub radius (signed lateral) | mm | 0.450 | -0.066 | 0.859 | 0.925 |
| Mechanical trail | mm | 43.585 | 22.429 | 60.977 | 38.548 |
| Half track | mm | 484.335 | 455.129 | 493.242 | 38.113 |
| Track change | mm | -11.330 | -31.639 | -11.330 | 20.309 |
| Damper length | mm | 229.069 | 226.187 | 230.527 | 4.340 |
| Roll-centre height | mm | -81.877 | -81.877 | -81.261 | 0.617 |
| Roll-centre lateral position | mm | 0.000 | -16.390 | 16.390 | 32.780 |
| FVIC lateral (y) | mm | -5199.543 | -5442.349 | -4753.138 | 689.211 |
| FVIC height (z) | mm | -1497.682 | -1519.235 | -1482.767 | 36.467 |
| FVSA length | mm | 5890.823 | 5439.829 | 6130.386 | 690.558 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 1.42 | 118.71 | 117.29 |
| Steering ratio (rack) | deg/mm | 0.6567 | 0.6250 | 1.0875 | 0.4625 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0942 | -3.3642 | 6.6857 | 10.0499 |
| Caster | deg | 8.9498 | 8.9490 | 8.9503 | 0.0013 |
| Toe (positive = toe-in) | deg | -0.1117 | -30.2641 | 25.0909 | 55.3551 |
| Scrub radius (signed lateral) | mm | 0.446 | -0.078 | 0.893 | 0.971 |
| Mechanical trail | mm | 43.769 | 19.687 | 61.331 | 41.643 |
| Half track | mm | 478.395 | 449.339 | 486.189 | 36.850 |
| Track change | mm | -23.210 | -44.860 | -23.210 | 21.650 |
| Damper length | mm | 299.487 | 296.407 | 301.031 | 4.624 |
| Roll-centre height | mm | 133.603 | 125.368 | 133.603 | 8.234 |
| Roll-centre lateral position | mm | -0.000 | -49.592 | 49.592 | 99.184 |
| FVIC lateral (y) | mm | 7739.138 | 7117.930 | 9221.507 | 2103.577 |
| FVIC height (z) | mm | -2917.473 | -3199.900 | -2790.946 | 408.954 |
| FVSA length | mm | -7804.623 | -9319.348 | -7174.448 | 2144.900 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 76.91 | 133.10 | 56.19 |
| Steering ratio (rack) | deg/mm | 0.7267 | 0.7125 | 1.2313 | 0.5187 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 262.991 | 232.991 | 292.991 | 60.000 |
| Wheel travel (left) | mm | 0.000 | -45.172 | 44.283 | 89.454 |
| Wheel travel (right) | mm | 0.000 | -45.172 | 44.283 | 89.454 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4932 | 1.4600 | 1.5132 | 0.0532 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6697 | 0.6609 | 0.6849 | 0.0241 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 2.8222 | -0.1343 | 2.8222 | 2.9564 |
| Road camber (inner) | deg | -2.9106 | -2.9106 | 3.0509 | 5.9615 |
| Camber (left) | deg | -0.1099 | -3.0815 | -0.1099 | 2.9716 |
| Camber (right) | deg | 0.0214 | 0.0214 | 6.4238 | 6.4024 |
| Caster (left) | deg | 8.9496 | 8.9493 | 8.9496 | 0.0003 |
| Caster (right) | deg | 8.9466 | 8.9465 | 8.9466 | 0.0001 |
| Toe (left) | deg | 0.0434 | 0.0434 | 22.8503 | 22.8069 |
| Toe (right) | deg | -0.0375 | -29.1313 | -0.0375 | 29.0938 |
| Scrub radius (signed lateral) | mm | 0.445 | 0.445 | 0.773 | 0.328 |
| Mechanical trail | mm | 43.656 | 27.815 | 43.656 | 15.841 |
| Half track | mm | 489.081 | 489.081 | 499.990 | 10.910 |
| Track change | mm | -2.498 | -23.800 | -2.498 | 21.302 |
| Damper length | mm | 246.140 | 246.140 | 247.620 | 1.480 |
| Roll-centre height | mm | -176.338 | -176.338 | -146.831 | 29.507 |
| Roll-centre lateral position | mm | -1281.183 | -1281.183 | -1189.246 | 91.937 |
| Body roll | deg | 2.9333 | 2.9332 | 2.9566 | 0.0234 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 124.91 | 171.93 | 47.02 |
| Steering ratio (rack) | deg/mm | 0.6728 | 0.6454 | 0.6728 | 0.0274 |

Plots: `plots/09_steer_in_roll.png`

## 10_corner_ramp  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | -0.0000 | -0.2270 | -0.0000 | 0.2270 |
| Road camber (inner) | deg | -0.0000 | -0.0000 | 3.0509 | 3.0509 |
| Camber (left) | deg | -0.0000 | -3.0815 | -0.0000 | 3.0815 |
| Camber (right) | deg | -0.0000 | -0.0000 | 6.4238 | 6.4238 |
| Caster (left) | deg | 8.9470 | 8.9470 | 8.9493 | 0.0023 |
| Caster (right) | deg | 8.9470 | 8.9465 | 8.9470 | 0.0005 |
| Toe (left) | deg | -0.0000 | -0.0000 | 22.8503 | 22.8503 |
| Toe (right) | deg | 0.0000 | -29.1313 | 0.0000 | 29.1313 |
| Scrub radius (signed lateral) | mm | 0.448 | 0.448 | 0.773 | 0.325 |
| Half track | mm | 490.000 | 490.000 | 499.990 | 9.990 |
| Track change | mm | 0.000 | -23.800 | 0.000 | 23.800 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4932 | 1.4724 | 1.4932 | 0.0207 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6697 | 0.6697 | 0.6791 | 0.0094 |
| Roll-centre height | mm | 18.188 | -147.058 | 18.188 | 165.246 |
| Roll-centre lateral position | mm | -0.000 | -1214.917 | -0.000 | 1214.917 |
| Body roll | deg | -0.0000 | -0.0000 | 2.9566 | 2.9566 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 98.15 | 140.43 | 42.29 |
| Steering ratio (rack) | deg/mm | 0.6875 | 0.6504 | 0.6875 | 0.0371 |

Plots: `plots/10_corner_ramp.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LBJ | spherical | 21.32 | `06_steer_droop` step 64 | - | - | 0.00 | 20.21 | - |
| UBJ | spherical | - | - | - | - | - | 22.90 | - |
| Outer Tie Rod End | rod_end | - | - | - | - | - | 22.93 | - |
| Inner Tie Rod End | rod_end | 11.20 | `06_steer_droop` step 0 | 11.20 | 267.5 | 0.82 | 5.96 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/08_damper_stroke.png`
- `plots/09_steer_in_roll.png`
- `plots/10_corner_ramp.png`
