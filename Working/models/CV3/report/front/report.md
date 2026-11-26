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
| `10_steady_corner` | ok | 33/33 | - | - |

## Provenance

- geometry: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV3\front.yaml`
- geometry SHA-256: `eb712519625aaa5a...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV3\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 65 | True | 4.06e-06 | - |
| `02_roll` | roll | 65 | True | 2.84e-06 | - |
| `04_steer_design` | steer | 65 | True | 4.50e-06 | - |
| `05_steer_bump` | steer | 65 | True | 3.59e-06 | Held at +50.8 mm wheel travel, not design height. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 3.75e-06 | Held at -50.8 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a right turn, so the LEFT wheel is outer and should be in bump, but it is at -50.8 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 3.78e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 5.71e-06 | Held at +25.0/-25.0 mm wheel travel (+2.99 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_steady_corner` | roll_ramp_at_steer | 33 | True | 2.12e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Camber | deg | -0.0000 | -0.2382 | 0.0046 | 0.2429 |
| Caster | deg | 9.0001 | 9.0000 | 9.0069 | 0.0069 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0038 | 0.0059 | 0.0096 |
| Scrub radius (signed lateral) | mm | 0.000 | 0.000 | 0.000 | 0.000 |
| Mechanical trail | mm | 44.110 | 44.105 | 44.114 | 0.009 |
| Half track | mm | 480.000 | 469.957 | 480.467 | 10.510 |
| Wheel travel | mm | -0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 313.585 | 277.199 | 348.566 | 71.367 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4281 | 1.3625 | 1.4711 | 0.1086 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7002 | 0.6798 | 0.7339 | 0.0542 |
| Roll-centre height | mm | 32.653 | -37.216 | 106.013 | 143.228 |
| FVIC lateral (y) | mm | -47852.517 | -1266087.039 | 301926.221 | 1568013.259 |
| FVIC height (z) | mm | 3287.881 | -34794.988 | 136093.507 | 170888.496 |
| FVSA length | mm | 48444.219 | -303447.488 | 1273857.883 | 1577305.371 |
| Track change | mm | 0.000 | -20.087 | 0.934 | 21.020 |
| Steering ratio (rack) | deg/mm | 0.8184 | 0.7779 | 0.8704 | 0.0925 |
| Camber gain | deg/mm | -0.0011 | -0.0084 | 0.0081 | 0.0165 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.0719 | 0.0046 | 0.0765 |
| Camber (right) | deg | 0.0000 | -0.0719 | 0.0046 | 0.0765 |
| Caster (left) | deg | 9.0001 | 9.0000 | 9.0021 | 0.0022 |
| Caster (right) | deg | 9.0001 | 9.0000 | 9.0021 | 0.0022 |
| Toe (left) | deg | 0.0000 | -0.0037 | 0.0054 | 0.0091 |
| Toe (right) | deg | -0.0000 | -0.0037 | 0.0054 | 0.0091 |
| Scrub radius (signed lateral) | mm | 0.000 | 0.000 | 0.000 | 0.000 |
| Half track | mm | 480.000 | 476.740 | 480.467 | 3.727 |
| Track change | mm | 0.000 | -1.795 | 0.000 | 1.795 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4281 | 1.3975 | 1.4533 | 0.0559 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7002 | 0.6881 | 0.7156 | 0.0275 |
| Camber recovery | deg/deg | -0.0096 | -0.0377 | 0.0218 | 0.0595 |
| Roll-centre height | mm | 32.653 | -28.655 | 32.653 | 61.308 |
| Roll-centre lateral migration vs roll | mm/deg | -168.5872 | -168.5872 | -159.9730 | 8.6142 |
| Body roll | deg | -0.0000 | -2.9925 | 2.9925 | 5.9849 |
| Steering ratio (rack) | deg/mm | 0.8184 | 0.7984 | 0.8408 | 0.0424 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0121 | -3.0376 | 5.5322 | 8.5698 |
| Caster | deg | 9.0001 | 9.0000 | 9.0003 | 0.0003 |
| Toe (positive = toe-in) | deg | 0.0767 | -25.7187 | 23.9794 | 49.6981 |
| Scrub radius (signed lateral) | mm | 0.002 | -0.602 | 0.504 | 1.107 |
| Mechanical trail | mm | 44.041 | 19.495 | 62.279 | 42.784 |
| Half track | mm | 480.058 | 453.281 | 488.002 | 34.721 |
| Track change | mm | -0.000 | -21.710 | -0.000 | 21.710 |
| Damper length | mm | 313.592 | 310.505 | 315.295 | 4.790 |
| Roll-centre height | mm | 32.653 | 27.694 | 32.653 | 4.958 |
| Roll-centre lateral position | mm | 0.429 | -134.759 | 145.952 | 280.711 |
| FVIC lateral (y) | mm | -47913.801 | -67737.046 | -31417.166 | 36319.880 |
| FVIC height (z) | mm | 3294.597 | 1483.065 | 5463.842 | 3980.777 |
| FVSA length | mm | 48505.876 | 31904.885 | 68443.158 | 36538.273 |
| Rack displacement | mm | 0.094 | -28.000 | 30.000 | 58.000 |
| Ackermann | % | - | 63.85 | 86.13 | 22.28 |
| Steering ratio (rack) | deg/mm | 0.8181 | 0.7936 | 1.1228 | 0.3292 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.2535 | -3.2675 | 4.9193 | 8.1868 |
| Caster | deg | 9.0068 | 9.0063 | 9.0079 | 0.0016 |
| Toe (positive = toe-in) | deg | 0.0973 | -24.5147 | 24.0739 | 48.5887 |
| Scrub radius (signed lateral) | mm | 0.003 | -0.603 | 0.512 | 1.115 |
| Mechanical trail | mm | 44.021 | 18.960 | 62.286 | 43.326 |
| Half track | mm | 477.162 | 450.492 | 485.500 | 35.009 |
| Track change | mm | -5.831 | -29.897 | -5.831 | 24.066 |
| Damper length | mm | 277.209 | 274.125 | 278.983 | 4.858 |
| Roll-centre height | mm | -37.216 | -37.216 | -36.662 | 0.554 |
| Roll-centre lateral position | mm | -0.105 | -24.878 | 22.145 | 47.024 |
| FVIC lateral (y) | mm | -6387.624 | -6715.489 | -5870.542 | 844.947 |
| FVIC height (z) | mm | -1215.211 | -1253.307 | -1188.838 | 64.469 |
| FVSA length | mm | 6980.550 | 6454.331 | 7306.678 | 852.348 |
| Rack displacement | mm | 0.125 | -28.000 | 32.000 | 60.000 |
| Ackermann | % | - | 75.43 | 104.67 | 29.23 |
| Steering ratio (rack) | deg/mm | 0.7775 | 0.7444 | 1.0668 | 0.3224 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.1695 | -3.3019 | 5.5749 | 8.8768 |
| Caster | deg | 9.0044 | 9.0034 | 9.0050 | 0.0016 |
| Toe (positive = toe-in) | deg | 0.1087 | -26.2351 | 24.8706 | 51.1057 |
| Scrub radius (signed lateral) | mm | 0.003 | -0.622 | 0.521 | 1.143 |
| Mechanical trail | mm | 44.011 | 18.142 | 62.785 | 44.642 |
| Half track | mm | 470.035 | 443.715 | 477.287 | 33.573 |
| Track change | mm | -20.087 | -42.330 | -20.087 | 22.243 |
| Damper length | mm | 348.576 | 345.502 | 350.253 | 4.752 |
| Roll-centre height | mm | 106.013 | 99.129 | 106.013 | 6.883 |
| Roll-centre lateral position | mm | 0.210 | -44.613 | 47.884 | 92.497 |
| FVIC lateral (y) | mm | 7433.465 | 6895.312 | 8587.584 | 1692.272 |
| FVIC height (z) | mm | -2374.948 | -2548.392 | -2288.976 | 259.416 |
| FVSA length | mm | -7341.050 | -8518.561 | -6797.788 | 1720.773 |
| Rack displacement | mm | 0.125 | -27.000 | 29.000 | 56.000 |
| Ackermann | % | - | 53.62 | 75.32 | 21.69 |
| Steering ratio (rack) | deg/mm | 0.8700 | 0.8519 | 1.1866 | 0.3347 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 313.585 | 283.585 | 343.585 | 60.000 |
| Wheel travel (left) | mm | 0.000 | -43.482 | 42.060 | 85.543 |
| Wheel travel (right) | mm | 0.000 | -43.482 | 42.060 | 85.543 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4281 | 1.3755 | 1.4667 | 0.0912 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7002 | 0.6818 | 0.7270 | 0.0452 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 2.9192 | -0.1766 | 2.9192 | 3.0958 |
| Road camber (inner) | deg | -3.0088 | -3.0088 | 3.7196 | 6.7284 |
| Camber (left) | deg | -0.0719 | -3.1867 | -0.0719 | 3.1148 |
| Camber (right) | deg | -0.0177 | -0.0177 | 7.3404 | 7.3581 |
| Caster (left) | deg | 9.0021 | 9.0018 | 9.0021 | 0.0003 |
| Caster (right) | deg | 9.0006 | 9.0002 | 9.0006 | 0.0003 |
| Toe (left) | deg | -0.0037 | -0.0037 | 24.8357 | 24.8394 |
| Toe (right) | deg | 0.0054 | -31.3779 | 0.0054 | 31.3833 |
| Scrub radius (signed lateral) | mm | 0.000 | 0.000 | 0.426 | 0.426 |
| Mechanical trail | mm | 44.113 | 24.674 | 44.113 | 19.439 |
| Half track | mm | 480.159 | 480.159 | 490.578 | 10.418 |
| Track change | mm | -1.795 | -28.014 | -1.795 | 26.219 |
| Damper length | mm | 295.893 | 295.893 | 297.674 | 1.781 |
| Roll-centre height | mm | -28.655 | -28.655 | -11.446 | 17.209 |
| Roll-centre lateral position | mm | -495.572 | -495.572 | -368.907 | 126.665 |
| Body roll | deg | 2.9925 | 2.9924 | 3.0239 | 0.0315 |
| Rack displacement | mm | 0.000 | 0.000 | 32.000 | 32.000 |
| Ackermann | % | - | 118.83 | 187.16 | 68.33 |
| Steering ratio (rack) | deg/mm | 0.7984 | 0.7698 | 0.7984 | 0.0286 |

Plots: `plots/09_steer_in_roll.png`

## 10_steady_corner  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | -0.0293 | -0.1268 | -0.0065 | 0.1204 |
| Road camber (inner) | deg | 0.0335 | 0.0335 | 1.3141 | 1.2807 |
| Camber (left) | deg | -0.1573 | -2.2540 | -0.1573 | 2.0967 |
| Camber (right) | deg | 0.1615 | 0.1615 | 3.6332 | 3.4717 |
| Caster (left) | deg | 9.0001 | 9.0001 | 9.0014 | 0.0013 |
| Caster (right) | deg | 9.0001 | 9.0000 | 9.0001 | 0.0001 |
| Toe (left) | deg | 0.9960 | 0.9960 | 16.2745 | 15.2786 |
| Toe (right) | deg | -1.0028 | -18.5579 | -1.0028 | 17.5550 |
| Scrub radius (signed lateral) | mm | 0.025 | 0.025 | 0.313 | 0.288 |
| Half track | mm | 480.813 | 480.813 | 489.079 | 8.266 |
| Track change | mm | -0.038 | -11.278 | -0.038 | 11.240 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4268 | 1.4031 | 1.4268 | 0.0237 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7009 | 0.7009 | 0.7127 | 0.0118 |
| Roll-centre height | mm | 32.563 | 0.770 | 32.563 | 31.793 |
| Roll-centre lateral position | mm | -16.000 | -333.936 | -16.000 | 317.936 |
| Body roll | deg | 0.1280 | 0.1280 | 2.2506 | 2.1225 |
| Rack displacement | mm | 1.221 | 1.221 | 20.808 | 19.587 |
| Ackermann | % | - | 94.84 | 107.18 | 12.34 |
| Steering ratio (rack) | deg/mm | 0.8138 | 0.7739 | 0.8138 | 0.0399 |

Plots: `plots/10_steady_corner.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LBJ | spherical | 16.39 | `06_steer_droop` step 64 | - | - | 0.00 | 15.46 | - |
| UBJ | spherical | - | - | - | - | - | 18.08 | - |
| Outer Tie Rod End | rod_end | - | - | - | - | - | 18.73 | - |
| Inner Tie Rod End | rod_end | 13.32 | `06_steer_droop` step 0 | 13.60 | 269.1 | 8.71 | 2.63 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/08_damper_stroke.png`
- `plots/09_steer_in_roll.png`
- `plots/10_steady_corner.png`
