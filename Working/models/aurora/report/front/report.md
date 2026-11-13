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

- geometry: `C:\Users\General\Desktop\BSSR-suspension\Working\models\aurora\front.yaml`
- geometry SHA-256: `e594c531e67f4e0b...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\BSSR-suspension\Working\models\aurora\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 3.24e-06 | - |
| `02_roll` | roll | 65 | True | 2.51e-06 | - |
| `04_steer_design` | steer | 65 | True | 2.66e-06 | - |
| `05_steer_bump` | steer | 65 | True | 2.26e-06 | Held at +50.0 mm wheel travel, not design height. Outer/inner road camber: left turn, so OUTER = RIGHT wheel and INNER = LEFT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 4.47e-06 | Held at -55.0 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a left turn, so the RIGHT wheel is outer and should be in bump, but it is at -55.0 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: left turn, so OUTER = RIGHT wheel and INNER = LEFT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 3.15e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 4.36e-06 | Held at +25.0/-25.0 mm wheel travel (+3.39 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_corner_ramp` | roll_ramp_at_steer | 65 | True | 3.50e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Camber | deg | 0.0000 | -1.3507 | 0.1204 | 1.4711 |
| Caster | deg | 10.0000 | 9.9961 | 10.0471 | 0.0510 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0510 | 0.0002 | 0.0512 |
| Scrub radius (signed lateral) | mm | -8.057 | -8.096 | -8.054 | 0.042 |
| Mechanical trail | mm | 52.094 | 52.091 | 52.153 | 0.062 |
| Half track | mm | 424.000 | 414.509 | 424.121 | 9.612 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 242.811 | 213.393 | 271.862 | 58.469 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7990 | 1.6017 | 1.9779 | 0.3762 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5559 | 0.5056 | 0.6243 | 0.1188 |
| Roll-centre height | mm | 15.499 | -31.964 | 67.710 | 99.673 |
| FVIC lateral (y) | mm | -4535.693 | -263030.962 | 19465.260 | 282496.222 |
| FVIC height (z) | mm | 181.292 | -3098.060 | 35921.422 | 39019.482 |
| FVSA length | mm | 4963.005 | -19290.088 | 265893.572 | 285183.661 |
| Track change | mm | 0.000 | -18.983 | 0.241 | 19.224 |
| Steering ratio (rack) | deg/mm | 0.6892 | 0.6142 | 0.7900 | 0.1757 |
| Camber gain | deg/mm | -0.0115 | -0.0467 | 0.0336 | 0.0804 |

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
| Camber recovery | deg/deg | -0.0855 | -0.1880 | 0.0197 | 0.2078 |
| Roll-centre height | mm | 15.499 | -71.201 | 15.499 | 86.700 |
| Roll-centre lateral migration vs roll | mm/deg | -223.1052 | -223.1052 | -181.9601 | 41.1451 |
| Body roll | deg | -0.0000 | -3.3935 | 3.3935 | 6.7870 |
| Steering ratio (rack) | deg/mm | 0.6892 | 0.6564 | 0.7234 | 0.0671 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -3.3458 | 6.6007 | 9.9464 |
| Caster | deg | 10.0000 | 9.9991 | 10.0021 | 0.0030 |
| Toe (positive = toe-in) | deg | -0.0000 | -27.4209 | 23.4421 | 50.8630 |
| Scrub radius (signed lateral) | mm | -8.057 | -8.746 | -7.473 | 1.273 |
| Mechanical trail | mm | 52.094 | 26.517 | 71.862 | 45.345 |
| Half track | mm | 424.000 | 391.961 | 435.040 | 43.079 |
| Track change | mm | 0.000 | -20.999 | 0.000 | 20.999 |
| Damper length | mm | 242.811 | 240.093 | 244.312 | 4.219 |
| Roll-centre height | mm | 15.499 | 9.965 | 15.499 | 5.534 |
| Roll-centre lateral position | mm | -0.000 | -241.258 | 241.258 | 482.516 |
| FVIC lateral (y) | mm | -4535.693 | -5257.090 | -3612.996 | 1644.094 |
| FVIC height (z) | mm | 181.292 | 55.262 | 281.356 | 226.094 |
| FVSA length | mm | 4963.005 | 4005.318 | 5699.059 | 1693.741 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 68.45 | 100.05 | 31.60 |
| Steering ratio (rack) | deg/mm | 0.6892 | 0.6600 | 1.0036 | 0.3435 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -1.3507 | -4.2528 | 4.1591 | 8.4119 |
| Caster | deg | 10.0471 | 10.0430 | 10.0553 | 0.0122 |
| Toe (positive = toe-in) | deg | -0.0032 | -24.4874 | 20.4518 | 44.9392 |
| Scrub radius (signed lateral) | mm | -8.096 | -8.875 | -7.529 | 1.346 |
| Mechanical trail | mm | 52.131 | 28.048 | 73.928 | 45.880 |
| Half track | mm | 419.821 | 389.161 | 430.479 | 41.318 |
| Track change | mm | -8.358 | -28.359 | -8.358 | 20.002 |
| Damper length | mm | 213.393 | 210.605 | 214.894 | 4.289 |
| Roll-centre height | mm | -31.964 | -31.964 | -31.135 | 0.828 |
| Roll-centre lateral position | mm | 0.000 | -7.803 | 7.803 | 15.606 |
| FVIC lateral (y) | mm | -810.440 | -880.181 | -690.587 | 189.594 |
| FVIC height (z) | mm | -190.339 | -193.971 | -180.833 | 13.138 |
| FVSA length | mm | 1253.532 | 1104.274 | 1333.297 | 229.023 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 100.91 | 133.62 | 32.72 |
| Steering ratio (rack) | deg/mm | 0.6142 | 0.5603 | 0.8786 | 0.3183 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.3636 | -4.2738 | 8.3446 | 12.6184 |
| Caster | deg | 10.0124 | 10.0065 | 10.0161 | 0.0096 |
| Toe (positive = toe-in) | deg | -0.0510 | -32.5727 | 27.0935 | 59.6662 |
| Scrub radius (signed lateral) | mm | -8.068 | -8.843 | -7.408 | 1.436 |
| Mechanical trail | mm | 52.153 | 20.930 | 74.181 | 53.252 |
| Half track | mm | 414.509 | 377.634 | 424.552 | 46.918 |
| Track change | mm | -18.983 | -46.395 | -18.983 | 27.413 |
| Damper length | mm | 271.862 | 268.860 | 273.351 | 4.491 |
| Roll-centre height | mm | 67.710 | 61.522 | 67.710 | 6.188 |
| Roll-centre lateral position | mm | -0.000 | -49.386 | 49.386 | 98.772 |
| FVIC lateral (y) | mm | 2072.793 | 1837.698 | 2673.827 | 836.129 |
| FVIC height (z) | mm | -545.885 | -668.155 | -491.838 | 176.317 |
| FVSA length | mm | -1729.416 | -2377.193 | -1479.862 | 897.331 |
| Rack displacement | mm | 0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 64.62 | 103.38 | 38.76 |
| Steering ratio (rack) | deg/mm | 0.7900 | 0.7679 | 1.3780 | 0.6101 |

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
| Road camber (outer) | deg | 2.9237 | -0.2074 | 2.9237 | 3.1310 |
| Road camber (inner) | deg | -3.2736 | -3.2736 | 3.4207 | 6.6944 |
| Camber (left) | deg | -0.4636 | -3.6171 | -0.4636 | 3.1535 |
| Camber (right) | deg | 0.1137 | 0.1137 | 7.2945 | 7.1809 |
| Caster (left) | deg | 10.0155 | 10.0133 | 10.0155 | 0.0022 |
| Caster (right) | deg | 9.9963 | 9.9961 | 9.9963 | 0.0002 |
| Toe (left) | deg | -0.0002 | -0.0002 | 22.1347 | 22.1349 |
| Toe (right) | deg | -0.0014 | -28.9146 | -0.0014 | 28.9133 |
| Scrub radius (signed lateral) | mm | -7.989 | -7.989 | -7.535 | 0.454 |
| Mechanical trail | mm | 52.022 | 33.672 | 52.022 | 18.350 |
| Half track | mm | 423.381 | 423.381 | 436.775 | 13.394 |
| Track change | mm | -1.614 | -25.235 | -1.614 | 23.620 |
| Damper length | mm | 228.530 | 228.530 | 230.043 | 1.513 |
| Roll-centre height | mm | -71.201 | -71.201 | -49.036 | 22.165 |
| Roll-centre lateral position | mm | -707.839 | -707.839 | -575.161 | 132.678 |
| Body roll | deg | 3.3935 | 3.3933 | 3.4236 | 0.0302 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 184.83 | 316.23 | 131.41 |
| Steering ratio (rack) | deg/mm | 0.6564 | 0.6167 | 0.6564 | 0.0396 |

Plots: `plots/09_steer_in_roll.png`

## 10_corner_ramp  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 0.0000 | -0.2978 | 0.0000 | 0.2978 |
| Road camber (inner) | deg | 0.0000 | 0.0000 | 3.4207 | 3.4207 |
| Camber (left) | deg | 0.0000 | -3.6171 | 0.0000 | 3.6171 |
| Camber (right) | deg | 0.0000 | 0.0000 | 7.2945 | 7.2945 |
| Caster (left) | deg | 10.0000 | 10.0000 | 10.0133 | 0.0133 |
| Caster (right) | deg | 10.0000 | 9.9961 | 10.0000 | 0.0039 |
| Toe (left) | deg | -0.0000 | -0.0000 | 22.1347 | 22.1347 |
| Toe (right) | deg | -0.0000 | -28.9146 | -0.0000 | 28.9146 |
| Scrub radius (signed lateral) | mm | -8.057 | -8.057 | -7.535 | 0.522 |
| Half track | mm | 424.000 | 424.000 | 436.775 | 12.775 |
| Track change | mm | 0.000 | -25.235 | 0.000 | 25.235 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7990 | 1.7027 | 1.7990 | 0.0963 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5559 | 0.5559 | 0.5873 | 0.0314 |
| Roll-centre height | mm | 15.499 | -49.036 | 15.499 | 64.535 |
| Roll-centre lateral position | mm | 0.000 | -575.161 | 0.000 | 575.161 |
| Body roll | deg | 0.0000 | 0.0000 | 3.4236 | 3.4236 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 129.48 | 191.32 | 61.85 |
| Steering ratio (rack) | deg/mm | 0.6892 | 0.6167 | 0.6892 | 0.0725 |

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
