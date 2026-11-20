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

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\aurora\front.yaml`
- geometry SHA-256: `e594c531e67f4e0b...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\aurora\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 65 | True | 3.84e-06 | - |
| `02_roll` | roll | 65 | True | 2.63e-06 | - |
| `04_steer_design` | steer | 65 | True | 3.47e-06 | - |
| `05_steer_bump` | steer | 65 | True | 2.81e-06 | Held at +50.8 mm wheel travel, not design height. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 3.50e-06 | Held at -50.8 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a right turn, so the LEFT wheel is outer and should be in bump, but it is at -50.8 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 2.96e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 3.88e-06 | Held at +25.0/-25.0 mm wheel travel (+3.39 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_corner_ramp` | roll_ramp_at_steer | 65 | True | 2.83e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Camber | deg | 0.0000 | -1.3885 | 0.1204 | 1.5089 |
| Caster | deg | 10.0000 | 9.9961 | 10.0485 | 0.0524 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0343 | 0.0002 | 0.0345 |
| Scrub radius (signed lateral) | mm | -8.057 | -8.097 | -8.054 | 0.043 |
| Mechanical trail | mm | 52.094 | 52.091 | 52.133 | 0.042 |
| Half track | mm | 424.000 | 415.735 | 424.134 | 8.399 |
| Wheel travel | mm | -0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 242.811 | 212.893 | 269.733 | 56.840 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7990 | 1.5985 | 1.9679 | 0.3694 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5559 | 0.5082 | 0.6256 | 0.1174 |
| Roll-centre height | mm | 15.499 | -32.435 | 66.030 | 98.465 |
| FVIC lateral (y) | mm | -4535.693 | -70901.658 | 318665.663 | 389567.321 |
| FVIC height (z) | mm | 181.292 | -44450.929 | 9372.422 | 53823.352 |
| FVSA length | mm | 4963.005 | -321329.991 | 71939.703 | 393269.694 |
| Track change | mm | 0.000 | -16.530 | 0.268 | 16.798 |
| Steering ratio (rack) | deg/mm | 0.6892 | 0.6126 | 0.7766 | 0.1640 |
| Camber gain | deg/mm | -0.0115 | -0.0476 | 0.0272 | 0.0748 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | 0.0000 | -0.4636 | 0.1204 | 0.5840 |
| Camber (right) | deg | 0.0000 | -0.4636 | 0.1204 | 0.5840 |
| Caster (left) | deg | 10.0000 | 9.9961 | 10.0155 | 0.0194 |
| Caster (right) | deg | 10.0000 | 9.9961 | 10.0155 | 0.0194 |
| Toe (left) | deg | -0.0000 | -0.0014 | 0.0002 | 0.0016 |
| Toe (right) | deg | -0.0000 | -0.0014 | 0.0002 | 0.0016 |
| Scrub radius (signed lateral) | mm | -8.057 | -8.159 | -7.989 | 0.170 |
| Half track | mm | 424.000 | 421.526 | 424.135 | 2.609 |
| Track change | mm | 0.000 | -1.614 | 0.000 | 1.614 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7990 | 1.7021 | 1.8891 | 0.1870 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5559 | 0.5293 | 0.5875 | 0.0582 |
| Camber recovery | deg/deg | -0.0854 | -0.1880 | 0.0197 | 0.2078 |
| Roll-centre height | mm | 15.499 | -71.201 | 15.499 | 86.700 |
| Roll-centre lateral migration vs roll | mm/deg | -223.1054 | -223.1054 | -181.9596 | 41.1458 |
| Body roll | deg | -0.0000 | -3.3935 | 3.3935 | 6.7870 |
| Steering ratio (rack) | deg/mm | 0.6892 | 0.6564 | 0.7234 | 0.0671 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0113 | -2.9492 | 4.6249 | 7.5741 |
| Caster | deg | 10.0000 | 9.9991 | 10.0015 | 0.0023 |
| Toe (positive = toe-in) | deg | 0.0646 | -20.9626 | 20.1374 | 41.1000 |
| Scrub radius (signed lateral) | mm | -8.055 | -8.617 | -7.539 | 1.078 |
| Mechanical trail | mm | 52.032 | 30.470 | 68.539 | 38.069 |
| Half track | mm | 424.058 | 400.126 | 434.840 | 34.714 |
| Track change | mm | -0.000 | -15.257 | -0.000 | 15.257 |
| Damper length | mm | 242.817 | 240.800 | 244.157 | 3.358 |
| Roll-centre height | mm | 15.499 | 11.625 | 15.499 | 3.873 |
| Roll-centre lateral position | mm | 0.584 | -184.254 | 199.545 | 383.799 |
| FVIC lateral (y) | mm | -4537.927 | -5172.801 | -3818.035 | 1354.766 |
| FVIC height (z) | mm | 181.601 | 82.950 | 269.630 | 186.680 |
| FVSA length | mm | 4965.308 | 4218.961 | 5614.103 | 1395.143 |
| Rack displacement | mm | 0.094 | -28.000 | 30.000 | 58.000 |
| Ackermann | % | - | 68.19 | 87.95 | 19.75 |
| Steering ratio (rack) | deg/mm | 0.6890 | 0.6618 | 0.8591 | 0.1973 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -1.4014 | -4.0770 | 2.5114 | 6.5884 |
| Caster | deg | 10.0485 | 10.0446 | 10.0546 | 0.0100 |
| Toe (positive = toe-in) | deg | 0.0729 | -18.7272 | 18.7046 | 37.4317 |
| Scrub radius (signed lateral) | mm | -8.094 | -8.711 | -7.567 | 1.144 |
| Mechanical trail | mm | 52.050 | 30.201 | 69.817 | 39.616 |
| Half track | mm | 419.734 | 397.118 | 430.113 | 32.995 |
| Track change | mm | -8.675 | -25.221 | -8.675 | 16.545 |
| Damper length | mm | 212.900 | 210.835 | 214.302 | 3.467 |
| Roll-centre height | mm | -32.435 | -32.435 | -31.734 | 0.701 |
| Roll-centre lateral position | mm | -0.031 | -6.781 | 6.194 | 12.975 |
| FVIC lateral (y) | mm | -788.377 | -852.207 | -700.020 | 152.187 |
| FVIC height (z) | mm | -188.912 | -192.669 | -181.745 | 10.924 |
| FVSA length | mm | 1231.679 | 1121.561 | 1305.346 | 183.785 |
| Rack displacement | mm | 0.125 | -28.000 | 32.000 | 60.000 |
| Ackermann | % | - | 101.96 | 126.25 | 24.29 |
| Steering ratio (rack) | deg/mm | 0.6123 | 0.5621 | 0.7634 | 0.2013 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.2538 | -3.5343 | 5.0728 | 8.6071 |
| Caster | deg | 10.0080 | 10.0047 | 10.0106 | 0.0059 |
| Toe (positive = toe-in) | deg | 0.0627 | -22.8427 | 22.1040 | 44.9468 |
| Scrub radius (signed lateral) | mm | -8.061 | -8.668 | -7.497 | 1.171 |
| Mechanical trail | mm | 52.039 | 27.521 | 69.809 | 42.288 |
| Half track | mm | 415.819 | 390.406 | 425.905 | 35.498 |
| Track change | mm | -16.530 | -34.157 | -16.530 | 17.627 |
| Damper length | mm | 269.740 | 267.709 | 271.047 | 3.338 |
| Roll-centre height | mm | 66.030 | 62.096 | 66.030 | 3.934 |
| Roll-centre lateral position | mm | 0.197 | -40.748 | 43.525 | 84.272 |
| FVIC lateral (y) | mm | 2475.924 | 2216.820 | 2967.550 | 750.730 |
| FVIC height (z) | mm | -629.873 | -722.347 | -576.976 | 145.370 |
| FVSA length | mm | -2139.944 | -2663.436 | -1866.740 | 796.696 |
| Rack displacement | mm | 0.125 | -27.000 | 29.000 | 56.000 |
| Ackermann | % | - | 62.71 | 78.75 | 16.03 |
| Steering ratio (rack) | deg/mm | 0.7764 | 0.7583 | 0.9882 | 0.2298 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 242.811 | 212.811 | 272.811 | 60.000 |
| Wheel travel (left) | mm | 0.000 | -56.880 | 50.930 | 107.810 |
| Wheel travel (right) | mm | 0.000 | -56.880 | 50.930 | 107.810 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7990 | 1.6010 | 1.9800 | 0.3790 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5559 | 0.5050 | 0.6246 | 0.1196 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 2.9237 | 0.0059 | 2.9237 | 2.9177 |
| Road camber (inner) | deg | -3.2736 | -3.2736 | 2.5671 | 5.8407 |
| Camber (left) | deg | -0.4636 | -3.3950 | -0.4636 | 2.9314 |
| Camber (right) | deg | 0.1137 | 0.1137 | 6.2498 | 6.1362 |
| Caster (left) | deg | 10.0155 | 10.0134 | 10.0155 | 0.0021 |
| Caster (right) | deg | 9.9963 | 9.9961 | 9.9963 | 0.0002 |
| Toe (left) | deg | -0.0002 | -0.0002 | 20.2812 | 20.2813 |
| Toe (right) | deg | -0.0014 | -25.8083 | -0.0014 | 25.8070 |
| Scrub radius (signed lateral) | mm | -7.989 | -7.989 | -7.570 | 0.419 |
| Mechanical trail | mm | 52.022 | 35.415 | 52.022 | 16.607 |
| Half track | mm | 423.381 | 423.381 | 436.272 | 12.890 |
| Track change | mm | -1.614 | -21.219 | -1.614 | 19.605 |
| Damper length | mm | 228.530 | 228.530 | 229.951 | 1.421 |
| Roll-centre height | mm | -71.201 | -71.201 | -50.134 | 21.067 |
| Roll-centre lateral position | mm | -707.839 | -707.839 | -580.506 | 127.333 |
| Body roll | deg | 3.3935 | 3.3933 | 3.4174 | 0.0241 |
| Rack displacement | mm | 0.000 | 0.000 | 32.000 | 32.000 |
| Ackermann | % | - | 184.83 | 324.73 | 139.90 |
| Steering ratio (rack) | deg/mm | 0.6564 | 0.6190 | 0.6564 | 0.0374 |

Plots: `plots/09_steer_in_roll.png`

## 10_corner_ramp  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 0.0000 | -0.1577 | 0.0059 | 0.1636 |
| Road camber (inner) | deg | 0.0000 | 0.0000 | 2.5671 | 2.5671 |
| Camber (left) | deg | 0.0000 | -3.3950 | 0.0000 | 3.3950 |
| Camber (right) | deg | 0.0000 | 0.0000 | 6.2498 | 6.2498 |
| Caster (left) | deg | 10.0000 | 10.0000 | 10.0134 | 0.0134 |
| Caster (right) | deg | 10.0000 | 9.9961 | 10.0000 | 0.0039 |
| Toe (left) | deg | -0.0000 | -0.0000 | 20.2812 | 20.2812 |
| Toe (right) | deg | -0.0000 | -25.8083 | -0.0000 | 25.8083 |
| Scrub radius (signed lateral) | mm | -8.057 | -8.057 | -7.570 | 0.487 |
| Half track | mm | 424.000 | 424.000 | 436.272 | 12.272 |
| Track change | mm | 0.000 | -21.219 | 0.000 | 21.219 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7990 | 1.7027 | 1.7990 | 0.0963 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5559 | 0.5559 | 0.5873 | 0.0315 |
| Roll-centre height | mm | 15.499 | -50.134 | 15.499 | 65.632 |
| Roll-centre lateral position | mm | 0.000 | -580.506 | 0.000 | 580.506 |
| Body roll | deg | 0.0000 | 0.0000 | 3.4174 | 3.4174 |
| Rack displacement | mm | 0.000 | 0.000 | 32.000 | 32.000 |
| Ackermann | % | - | 135.19 | 186.14 | 50.95 |
| Steering ratio (rack) | deg/mm | 0.6892 | 0.6190 | 0.6892 | 0.0702 |

Plots: `plots/10_corner_ramp.png`

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/08_damper_stroke.png`
- `plots/09_steer_in_roll.png`
- `plots/10_corner_ramp.png`
