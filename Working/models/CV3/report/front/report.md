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
- geometry SHA-256: `6e8a91b79793eb80...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV3\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 65 | True | 4.04e-06 | - |
| `02_roll` | roll | 65 | True | 3.27e-06 | - |
| `04_steer_design` | steer | 65 | True | 4.51e-06 | - |
| `05_steer_bump` | steer | 65 | True | 3.53e-06 | Held at +50.8 mm wheel travel, not design height. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 4.80e-06 | Held at -50.8 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a right turn, so the LEFT wheel is outer and should be in bump, but it is at -50.8 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 2.65e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 3.62e-06 | Held at +25.0/-25.0 mm wheel travel (+3.00 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
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

## 01_bump_parallel  (heave)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0000 | -0.3766 | -0.0000 | 0.3766 |
| Caster | deg | 9.0012 | 9.0012 | 9.0096 | 0.0084 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0004 | 0.4966 | 0.4970 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.012 | 0.013 |
| Mechanical trail | mm | 44.119 | 43.661 | 44.120 | 0.459 |
| Half track | mm | 480.000 | 471.440 | 480.033 | 8.592 |
| Wheel travel | mm | -0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 262.991 | 228.014 | 297.194 | 69.180 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4722 | 1.4341 | 1.4911 | 0.0570 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6792 | 0.6706 | 0.6973 | 0.0267 |
| Roll-centre height | mm | 9.526 | -88.572 | 109.144 | 197.716 |
| FVIC lateral (y) | mm | -246896.763 | -246896.763 | 702750.007 | 949646.771 |
| FVIC height (z) | mm | 4909.400 | -20594.189 | 4909.400 | 25503.589 |
| FVSA length | mm | 247425.474 | -702571.898 | 247425.474 | 949997.372 |
| Track change | mm | 0.000 | -17.119 | 0.066 | 17.185 |
| Steering ratio (rack) | deg/mm | 0.6877 | 0.6466 | 0.7363 | 0.0898 |
| Camber gain | deg/mm | -0.0002 | -0.0137 | 0.0175 | 0.0312 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.0797 | 0.0000 | 0.0798 |
| Camber (right) | deg | 0.0000 | -0.0797 | 0.0000 | 0.0798 |
| Caster (left) | deg | 9.0012 | 9.0012 | 9.0030 | 0.0018 |
| Caster (right) | deg | 9.0012 | 9.0012 | 9.0030 | 0.0018 |
| Toe (left) | deg | 0.0000 | -0.0004 | 0.1150 | 0.1154 |
| Toe (right) | deg | -0.0000 | -0.0004 | 0.1150 | 0.1154 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.004 | 0.004 |
| Half track | mm | 480.000 | 477.710 | 480.033 | 2.323 |
| Track change | mm | 0.000 | -2.290 | 0.000 | 2.290 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4722 | 1.4525 | 1.4871 | 0.0347 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6792 | 0.6724 | 0.6885 | 0.0160 |
| Camber recovery | deg/deg | -0.0013 | -0.0510 | 0.0544 | 0.1054 |
| Roll-centre height | mm | 9.526 | -337.024 | 9.526 | 346.550 |
| Roll-centre lateral migration vs roll | mm/deg | -786.9398 | -786.9398 | -732.5496 | 54.3902 |
| Body roll | deg | -0.0000 | -2.9950 | 2.9950 | 5.9901 |
| Steering ratio (rack) | deg/mm | 0.6877 | 0.6684 | 0.7084 | 0.0399 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0102 | -2.6840 | 4.1463 | 6.8302 |
| Caster | deg | 9.0012 | 9.0012 | 9.0012 | 0.0001 |
| Toe (positive = toe-in) | deg | 0.0645 | -20.6647 | 20.4845 | 41.1492 |
| Scrub radius (signed lateral) | mm | 0.001 | -0.492 | 0.443 | 0.935 |
| Mechanical trail | mm | 44.062 | 23.578 | 59.459 | 35.881 |
| Half track | mm | 480.049 | 459.080 | 488.166 | 29.086 |
| Track change | mm | -0.000 | -14.734 | -0.000 | 14.734 |
| Damper length | mm | 262.997 | 260.691 | 264.480 | 3.789 |
| Roll-centre height | mm | 9.526 | -1.408 | 9.526 | 10.934 |
| Roll-centre lateral position | mm | 1.334 | -484.637 | 539.047 | 1023.684 |
| FVIC lateral (y) | mm | -248778.980 | -21456416.409 | 5381886.867 | 26838303.276 |
| FVIC height (z) | mm | 4959.988 | -146283.396 | 574629.768 | 720913.164 |
| FVSA length | mm | 249308.374 | -5383388.771 | 21464595.194 | 26847983.965 |
| Rack displacement | mm | 0.094 | -28.000 | 30.000 | 58.000 |
| Ackermann | % | - | 43.98 | 54.81 | 10.82 |
| Steering ratio (rack) | deg/mm | 0.6875 | 0.6789 | 0.8331 | 0.1542 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.3446 | -2.9595 | 3.4423 | 6.4018 |
| Caster | deg | 9.0087 | 9.0081 | 9.0097 | 0.0017 |
| Toe (positive = toe-in) | deg | 0.4870 | -19.0479 | 20.7702 | 39.8181 |
| Scrub radius (signed lateral) | mm | 0.012 | -0.478 | 0.454 | 0.931 |
| Mechanical trail | mm | 43.671 | 22.862 | 59.037 | 36.175 |
| Half track | mm | 473.565 | 453.000 | 481.875 | 28.875 |
| Track change | mm | -12.998 | -29.129 | -12.998 | 16.131 |
| Damper length | mm | 228.022 | 225.805 | 229.511 | 3.707 |
| Roll-centre height | mm | -88.572 | -88.572 | -87.909 | 0.662 |
| Roll-centre lateral position | mm | -0.058 | -14.516 | 12.783 | 27.300 |
| FVIC lateral (y) | mm | -4786.152 | -5069.978 | -4398.962 | 671.016 |
| FVIC height (z) | mm | -1497.010 | -1503.894 | -1484.132 | 19.763 |
| FVSA length | mm | 5482.733 | 5089.099 | 5765.514 | 676.415 |
| Rack displacement | mm | 0.125 | -28.000 | 32.000 | 60.000 |
| Ackermann | % | - | -276.69 | 42.51 | 319.21 |
| Steering ratio (rack) | deg/mm | 0.6463 | 0.6330 | 0.7808 | 0.1477 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.3912 | -3.1786 | 3.8719 | 7.0505 |
| Caster | deg | 9.0096 | 9.0083 | 9.0105 | 0.0022 |
| Toe (positive = toe-in) | deg | 0.5886 | -20.5656 | 22.0318 | 42.5974 |
| Scrub radius (signed lateral) | mm | 0.015 | -0.508 | 0.476 | 0.984 |
| Mechanical trail | mm | 43.576 | 21.307 | 59.873 | 38.566 |
| Half track | mm | 471.505 | 451.203 | 478.381 | 27.178 |
| Track change | mm | -17.119 | -32.546 | -17.119 | 15.426 |
| Damper length | mm | 297.202 | 294.886 | 298.675 | 3.788 |
| Roll-centre height | mm | 109.144 | 103.739 | 109.144 | 5.404 |
| Roll-centre lateral position | mm | 0.199 | -42.109 | 45.107 | 87.215 |
| FVIC lateral (y) | mm | 4545.762 | 4260.255 | 5043.648 | 783.393 |
| FVIC height (z) | mm | -1433.388 | -1490.641 | -1396.621 | 94.020 |
| FVSA length | mm | -4302.456 | -4813.035 | -4014.458 | 798.577 |
| Rack displacement | mm | 0.125 | -27.000 | 29.000 | 56.000 |
| Ackermann | % | - | -376.83 | 7.59 | 384.42 |
| Steering ratio (rack) | deg/mm | 0.7362 | 0.7336 | 0.8705 | 0.1369 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 262.991 | 232.991 | 292.991 | 60.000 |
| Wheel travel (left) | mm | 0.000 | -44.535 | 43.652 | 88.186 |
| Wheel travel (right) | mm | 0.000 | -44.535 | 43.652 | 88.186 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4722 | 1.4389 | 1.4911 | 0.0522 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6792 | 0.6706 | 0.6950 | 0.0243 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 2.9129 | 0.1754 | 2.9129 | 2.7375 |
| Road camber (inner) | deg | -3.0707 | -3.0707 | 1.9736 | 5.0443 |
| Camber (left) | deg | -0.0797 | -2.8192 | -0.0797 | 2.7395 |
| Camber (right) | deg | -0.0781 | -0.0781 | 5.1772 | 5.2553 |
| Caster (left) | deg | 9.0030 | 9.0027 | 9.0030 | 0.0003 |
| Caster (right) | deg | 9.0028 | 9.0023 | 9.0028 | 0.0005 |
| Toe (left) | deg | 0.0864 | 0.0864 | 21.2318 | 21.1454 |
| Toe (right) | deg | 0.1150 | -24.6387 | 0.1150 | 24.7537 |
| Scrub radius (signed lateral) | mm | 0.001 | 0.001 | 0.365 | 0.364 |
| Mechanical trail | mm | 44.064 | 28.058 | 44.064 | 16.006 |
| Half track | mm | 478.694 | 478.694 | 489.012 | 10.318 |
| Track change | mm | -2.290 | -19.627 | -2.290 | 17.337 |
| Damper length | mm | 245.897 | 245.897 | 247.434 | 1.537 |
| Roll-centre height | mm | -337.024 | -337.024 | -308.616 | 28.407 |
| Roll-centre lateral position | mm | -2299.866 | -2582.497 | -2234.960 | 347.537 |
| Body roll | deg | 2.9950 | 2.9949 | 3.0148 | 0.0199 |
| Rack displacement | mm | -0.000 | -0.000 | 32.000 | 32.000 |
| Ackermann | % | - | 90.65 | 102.90 | 12.25 |
| Steering ratio (rack) | deg/mm | 0.6684 | 0.6571 | 0.6684 | 0.0113 |

Plots: `plots/09_steer_in_roll.png`

## 10_steady_corner  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | -0.0018 | -0.0018 | 0.4657 | 0.4675 |
| Road camber (inner) | deg | 0.0056 | 0.0056 | 0.5841 | 0.5784 |
| Camber (left) | deg | -0.1567 | -2.1766 | -0.1567 | 2.0199 |
| Camber (right) | deg | 0.1605 | 0.1605 | 3.2710 | 3.1105 |
| Caster (left) | deg | 9.0012 | 9.0012 | 9.0028 | 0.0016 |
| Caster (right) | deg | 9.0012 | 9.0012 | 9.0018 | 0.0006 |
| Toe (left) | deg | 0.9966 | 0.9966 | 15.4703 | 14.4737 |
| Toe (right) | deg | -1.0022 | -17.1587 | -1.0022 | 16.1565 |
| Scrub radius (signed lateral) | mm | 0.024 | 0.024 | 0.282 | 0.258 |
| Half track | mm | 480.771 | 480.771 | 487.422 | 6.651 |
| Track change | mm | -0.040 | -10.704 | -0.040 | 10.664 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4712 | 1.4503 | 1.4712 | 0.0208 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6797 | 0.6797 | 0.6895 | 0.0098 |
| Roll-centre height | mm | 8.792 | -13697.101 | 3705.932 | 17403.033 |
| Roll-centre lateral position | mm | -101.606 | -122745.917 | 32093.394 | 154839.311 |
| Body roll | deg | 0.1549 | 0.1549 | 2.6590 | 2.5041 |
| Rack displacement | mm | 1.454 | 1.454 | 23.324 | 21.869 |
| Ackermann | % | - | 77.90 | 87.97 | 10.07 |
| Steering ratio (rack) | deg/mm | 0.6846 | 0.6596 | 0.6846 | 0.0250 |

Plots: `plots/10_steady_corner.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LBJ | spherical | 20.13 | `06_steer_droop` step 64 | - | - | 0.00 | 19.01 | - |
| UBJ | spherical | - | - | - | - | - | 21.51 | - |
| Outer Tie Rod End | rod_end | - | - | - | - | - | 22.03 | - |
| Inner Tie Rod End | rod_end | 5.70 | `04_steer_design` step 0 | 5.73 | 269.5 | 0.82 | 2.79 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/08_damper_stroke.png`
- `plots/09_steer_in_roll.png`
- `plots/10_steady_corner.png`
