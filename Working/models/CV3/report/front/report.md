# Front axle characteristic report

## Solve status

| sweep | status | steps | where it stopped | reason |
| --- | --- | --- | --- | --- |
| `01_bump_parallel` | ok | 65/65 | - | - |
| `04_steer_design` | ok | 65/65 | - | - |
| `05_steer_bump` | ok | 65/65 | - | - |
| `06_steer_droop` | ok | 65/65 | - | - |
| `10_steady_corner` | ok | 33/33 | - | - |

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\CV3\front.yaml`
- geometry SHA-256: `3d2b2cf37b66dba8...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\CV3\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 65 | True | 3.66e-06 | - |
| `04_steer_design` | steer | 65 | True | 3.57e-06 | - |
| `05_steer_bump` | steer | 65 | True | 5.39e-06 | Held at +50.8 mm wheel travel, not design height. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 3.27e-06 | Held at -50.8 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a left turn, so the RIGHT wheel is outer and should be in bump, but it is at -50.8 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: left turn, so OUTER = RIGHT wheel and INNER = LEFT wheel throughout. |
| `10_steady_corner` | roll_ramp_at_steer | 33 | True | 2.93e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Camber | deg | -0.0000 | -0.2387 | 0.0046 | 0.2432 |
| Caster | deg | 9.0001 | 9.0000 | 9.0069 | 0.0069 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0036 | 0.0074 | 0.0111 |
| Scrub radius (signed lateral) | mm | -0.017 | -0.017 | -0.017 | 0.000 |
| Mechanical trail | mm | 44.110 | 44.104 | 44.114 | 0.010 |
| Half track | mm | 480.000 | 469.960 | 480.467 | 10.506 |
| Wheel travel | mm | -0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 313.585 | 277.199 | 348.566 | 71.367 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4281 | 1.3626 | 1.4711 | 0.1085 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7002 | 0.6798 | 0.7339 | 0.0541 |
| Roll-centre height | mm | 32.650 | -37.203 | 105.991 | 143.194 |
| FVIC lateral (y) | mm | -47961.378 | -1425124.208 | 293377.286 | 1718501.494 |
| FVIC height (z) | mm | 3294.992 | -33804.884 | 153167.161 | 186972.045 |
| FVSA length | mm | 48553.312 | -294841.409 | 1433808.910 | 1728650.319 |
| Track change | mm | 0.000 | -20.079 | 0.934 | 21.013 |
| Steering ratio (rack) | deg/mm | 0.8183 | 0.7778 | 0.8704 | 0.0926 |
| Camber gain | deg/mm | -0.0011 | -0.0084 | 0.0081 | 0.0166 |

Plots: `plots/01_bump_parallel.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -2.8739 | 5.5296 | 8.4035 |
| Caster | deg | 9.0001 | 9.0000 | 9.0003 | 0.0002 |
| Toe (positive = toe-in) | deg | -0.0000 | -25.7068 | 22.3799 | 48.0867 |
| Scrub radius (signed lateral) | mm | -0.017 | -0.620 | 0.464 | 1.084 |
| Mechanical trail | mm | 44.110 | 21.284 | 62.290 | 41.006 |
| Half track | mm | 480.000 | 453.289 | 487.999 | 34.710 |
| Track change | mm | 0.000 | -18.813 | 0.000 | 18.813 |
| Damper length | mm | 313.585 | 310.505 | 315.223 | 4.718 |
| Roll-centre height | mm | 32.650 | 28.396 | 32.650 | 4.253 |
| Roll-centre lateral position | mm | 0.000 | -134.760 | 134.760 | 269.521 |
| FVIC lateral (y) | mm | -47961.378 | -66830.912 | -31442.348 | 35388.564 |
| FVIC height (z) | mm | 3294.992 | 1484.126 | 5356.441 | 3872.316 |
| FVSA length | mm | 48553.312 | 31930.098 | 67531.550 | 35601.452 |
| Rack displacement | mm | 0.000 | -28.000 | 28.000 | 56.000 |
| Ackermann | % | - | 63.74 | 81.37 | 17.63 |
| Steering ratio (rack) | deg/mm | 0.8183 | 0.7936 | 1.1216 | 0.3279 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.2387 | -2.9609 | 4.9154 | 7.8764 |
| Caster | deg | 9.0069 | 9.0063 | 9.0079 | 0.0016 |
| Toe (positive = toe-in) | deg | 0.0014 | -24.4992 | 21.0905 | 45.5897 |
| Scrub radius (signed lateral) | mm | -0.017 | -0.621 | 0.449 | 1.070 |
| Mechanical trail | mm | 44.109 | 22.343 | 62.294 | 39.951 |
| Half track | mm | 477.086 | 450.506 | 485.499 | 34.993 |
| Track change | mm | -5.827 | -24.008 | -5.827 | 18.181 |
| Damper length | mm | 277.199 | 274.125 | 278.840 | 4.715 |
| Roll-centre height | mm | -37.203 | -37.203 | -36.768 | 0.435 |
| Roll-centre lateral position | mm | 0.000 | -22.154 | 22.154 | 44.309 |
| FVIC lateral (y) | mm | -6376.864 | -6678.938 | -5862.074 | 816.864 |
| FVIC height (z) | mm | -1213.501 | -1251.345 | -1189.310 | 62.035 |
| FVSA length | mm | 6969.584 | 6445.654 | 7271.014 | 825.360 |
| Rack displacement | mm | -0.000 | -28.000 | 28.000 | 56.000 |
| Ackermann | % | - | 74.32 | 94.06 | 19.74 |
| Steering ratio (rack) | deg/mm | 0.7778 | 0.7444 | 1.0655 | 0.3210 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.1533 | -3.2158 | 5.9375 | 9.1533 |
| Caster | deg | 9.0044 | 9.0034 | 9.0050 | 0.0016 |
| Toe (positive = toe-in) | deg | 0.0034 | -27.4238 | 24.0107 | 51.4345 |
| Scrub radius (signed lateral) | mm | -0.017 | -0.661 | 0.492 | 1.153 |
| Mechanical trail | mm | 44.107 | 19.115 | 63.344 | 44.229 |
| Half track | mm | 469.960 | 442.378 | 477.285 | 34.907 |
| Track change | mm | -20.079 | -40.764 | -20.079 | 20.685 |
| Damper length | mm | 348.566 | 345.340 | 350.219 | 4.879 |
| Roll-centre height | mm | 105.991 | 99.597 | 105.991 | 6.394 |
| Roll-centre lateral position | mm | -0.000 | -46.243 | 46.243 | 92.486 |
| FVIC lateral (y) | mm | 7416.084 | 6886.769 | 8630.600 | 1743.831 |
| FVIC height (z) | mm | -2368.193 | -2550.193 | -2283.728 | 266.465 |
| FVSA length | mm | -7322.496 | -8561.532 | -6787.825 | 1773.707 |
| Rack displacement | mm | -0.000 | -28.000 | 28.000 | 56.000 |
| Ackermann | % | - | 50.86 | 72.43 | 21.56 |
| Steering ratio (rack) | deg/mm | 0.8704 | 0.8521 | 1.2201 | 0.3680 |

Plots: `plots/06_steer_droop.png`

## 10_steady_corner  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | -0.0108 | -0.0202 | 0.2972 | 0.3174 |
| Road camber (inner) | deg | 0.0150 | 0.0150 | 0.8550 | 0.8400 |
| Camber (left) | deg | -0.1575 | -2.1470 | -0.1575 | 1.9894 |
| Camber (right) | deg | 0.1617 | 0.1617 | 3.3508 | 3.1891 |
| Caster (left) | deg | 9.0001 | 9.0001 | 9.0016 | 0.0015 |
| Caster (right) | deg | 9.0001 | 9.0000 | 9.0001 | 0.0001 |
| Toe (left) | deg | 0.9958 | 0.9958 | 15.2942 | 14.2984 |
| Toe (right) | deg | -1.0030 | -17.3786 | -1.0030 | 16.3757 |
| Scrub radius (signed lateral) | mm | 0.008 | 0.008 | 0.273 | 0.265 |
| Half track | mm | 480.823 | 480.823 | 488.805 | 7.982 |
| Track change | mm | -0.038 | -10.251 | -0.038 | 10.212 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4266 | 1.4006 | 1.4266 | 0.0260 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7010 | 0.7010 | 0.7140 | 0.0130 |
| Roll-centre height | mm | 32.528 | -7.319 | 32.528 | 39.847 |
| Roll-centre lateral position | mm | -19.138 | -387.275 | -19.138 | 368.137 |
| Body roll | deg | 0.1467 | 0.1467 | 2.4556 | 2.3089 |
| Rack displacement | mm | 1.222 | 1.222 | 19.584 | 18.363 |
| Ackermann | % | - | 99.37 | 111.19 | 11.82 |
| Steering ratio (rack) | deg/mm | 0.8136 | 0.7721 | 0.8136 | 0.0415 |

Plots: `plots/10_steady_corner.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LBJ | spherical | 16.38 | `06_steer_droop` step 64 | - | - | 0.00 | 15.46 | - |
| UBJ | spherical | - | - | - | - | - | 18.09 | - |
| Outer Tie Rod End | rod_end | - | - | - | - | - | 18.75 | - |
| Inner Tie Rod End | rod_end | 13.65 | `06_steer_droop` step 0 | 13.81 | 268.4 | 8.71 | 2.70 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/10_steady_corner.png`
