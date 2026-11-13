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

- geometry: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV2\front.yaml`
- geometry SHA-256: `f38153da12a40561...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV2\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 9.95e-07 | - |
| `02_roll` | roll | 65 | True | 2.65e-06 | - |
| `04_steer_design` | steer | 65 | True | 2.70e-06 | - |
| `05_steer_bump` | steer | 65 | True | 4.29e-06 | Held at +50.0 mm wheel travel, not design height. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 4.30e-06 | Held at -55.0 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a left turn, so the RIGHT wheel is outer and should be in bump, but it is at -55.0 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: left turn, so OUTER = RIGHT wheel and INNER = LEFT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 2.14e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 3.89e-06 | Held at +25.0/-25.0 mm wheel travel (+2.93 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_corner_ramp` | roll_ramp_at_steer | 65 | True | 2.27e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Camber | deg | -0.0000 | -0.2524 | -0.0000 | 0.2524 |
| Caster | deg | 8.9999 | 8.9999 | 9.0065 | 0.0065 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0088 | 0.0119 | 0.0207 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.000 | 0.000 |
| Mechanical trail | mm | 44.110 | 44.100 | 44.117 | 0.017 |
| Half track | mm | 490.000 | 479.512 | 490.022 | 10.510 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 262.991 | 228.965 | 299.449 | 70.484 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4486 | 1.5174 | 0.0689 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6590 | 0.6903 | 0.0313 |
| Roll-centre height | mm | 9.727 | -90.986 | 123.404 | 214.389 |
| FVIC lateral (y) | mm | -246117.399 | -246117.399 | 115968.058 | 362085.458 |
| FVIC height (z) | mm | 4895.299 | -5769.333 | 4895.299 | 10664.633 |
| FVSA length | mm | 246655.982 | -115622.010 | 246655.982 | 362277.992 |
| Track change | mm | 0.000 | -20.975 | 0.045 | 21.020 |
| Steering ratio (rack) | deg/mm | 0.6883 | 0.6580 | 0.7288 | 0.0709 |
| Camber gain | deg/mm | -0.0002 | -0.0081 | 0.0108 | 0.0189 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.0488 | 0.0001 | 0.0489 |
| Camber (right) | deg | -0.0000 | -0.0488 | 0.0001 | 0.0489 |
| Caster (left) | deg | 8.9999 | 8.9999 | 9.0012 | 0.0013 |
| Caster (right) | deg | 8.9999 | 8.9999 | 9.0012 | 0.0013 |
| Toe (left) | deg | -0.0000 | -0.0086 | 0.0111 | 0.0197 |
| Toe (right) | deg | 0.0000 | -0.0086 | 0.0111 | 0.0197 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.000 | 0.000 |
| Half track | mm | 490.000 | 487.620 | 490.032 | 2.412 |
| Track change | mm | 0.000 | -2.493 | 0.000 | 2.493 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4693 | 1.5094 | 0.0400 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6625 | 0.6806 | 0.0181 |
| Camber recovery | deg/deg | -0.0013 | -0.0315 | 0.0314 | 0.0629 |
| Roll-centre height | mm | 9.727 | -353.984 | 9.727 | 363.711 |
| Roll-centre lateral migration vs roll | mm/deg | -836.8300 | -836.8300 | -780.5607 | 56.2692 |
| Body roll | deg | -0.0000 | -2.9333 | 2.9333 | 5.8667 |
| Steering ratio (rack) | deg/mm | 0.6883 | 0.6737 | 0.7040 | 0.0303 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -3.0770 | 6.2520 | 9.3291 |
| Caster | deg | 8.9999 | 8.9999 | 9.0000 | 0.0001 |
| Toe (positive = toe-in) | deg | -0.0000 | -28.5220 | 23.4711 | 51.9931 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.506 | 0.426 | 0.932 |
| Mechanical trail | mm | 44.110 | 21.949 | 61.112 | 39.163 |
| Half track | mm | 490.000 | 460.905 | 498.716 | 37.811 |
| Track change | mm | 0.000 | -20.446 | 0.000 | 20.446 |
| Damper length | mm | 262.991 | 260.052 | 264.499 | 4.447 |
| Roll-centre height | mm | 9.727 | -6.084 | 9.727 | 15.811 |
| Roll-centre lateral position | mm | -0.000 | -691.077 | 691.077 | 1382.154 |
| FVIC lateral (y) | mm | -246117.414 | -16364340.066 | 10036886.523 | 26401226.589 |
| FVIC height (z) | mm | 4895.299 | -298598.250 | 480626.854 | 779225.104 |
| FVSA length | mm | 246655.997 | -10040829.461 | 16371894.203 | 26412723.664 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 74.09 | 106.96 | 32.87 |
| Steering ratio (rack) | deg/mm | 0.6883 | 0.6650 | 1.1299 | 0.4649 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.1944 | -3.1106 | 5.7223 | 8.8328 |
| Caster | deg | 9.0049 | 9.0045 | 9.0058 | 0.0013 |
| Toe (positive = toe-in) | deg | -0.0007 | -27.5147 | 22.1663 | 49.6810 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.513 | 0.413 | 0.926 |
| Mechanical trail | mm | 44.111 | 22.995 | 61.320 | 38.325 |
| Half track | mm | 483.357 | 453.802 | 492.609 | 38.807 |
| Track change | mm | -13.285 | -33.588 | -13.285 | 20.303 |
| Damper length | mm | 228.965 | 226.043 | 230.451 | 4.408 |
| Roll-centre height | mm | -90.986 | -90.986 | -90.189 | 0.797 |
| Roll-centre lateral position | mm | 0.000 | -14.373 | 14.373 | 28.747 |
| FVIC lateral (y) | mm | -6732.572 | -7123.927 | -6040.242 | 1083.685 |
| FVIC height (z) | mm | -2054.763 | -2061.027 | -2036.823 | 24.204 |
| FVSA length | mm | 7516.626 | 6821.437 | 7903.768 | 1082.331 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 89.77 | 127.20 | 37.43 |
| Steering ratio (rack) | deg/mm | 0.6580 | 0.6257 | 1.0995 | 0.4738 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.2524 | -3.5553 | 6.5771 | 10.1324 |
| Caster | deg | 9.0065 | 9.0052 | 9.0072 | 0.0020 |
| Toe (positive = toe-in) | deg | -0.0075 | -30.1863 | 25.3028 | 55.4891 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.543 | 0.457 | 1.000 |
| Mechanical trail | mm | 44.116 | 19.454 | 62.187 | 42.733 |
| Half track | mm | 479.512 | 449.997 | 487.323 | 37.326 |
| Track change | mm | -20.975 | -43.116 | -20.975 | 22.141 |
| Damper length | mm | 299.449 | 296.356 | 300.991 | 4.636 |
| Roll-centre height | mm | 123.404 | 115.214 | 123.404 | 8.190 |
| Roll-centre lateral position | mm | -0.000 | -51.873 | 51.873 | 103.745 |
| FVIC lateral (y) | mm | 5602.641 | 5241.462 | 6419.711 | 1178.249 |
| FVIC height (z) | mm | -1961.040 | -2061.983 | -1910.160 | 151.823 |
| FVSA length | mm | -5466.209 | -6298.490 | -5103.845 | 1194.646 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 59.43 | 88.89 | 29.46 |
| Steering ratio (rack) | deg/mm | 0.7288 | 0.7154 | 1.2286 | 0.5132 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 262.991 | 232.991 | 292.991 | 60.000 |
| Wheel travel (left) | mm | -0.000 | -45.201 | 44.159 | 89.360 |
| Wheel travel (right) | mm | 0.000 | -45.201 | 44.159 | 89.360 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4534 | 1.5168 | 0.0634 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6593 | 0.6880 | 0.0288 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 2.8832 | -0.1034 | 2.8832 | 2.9866 |
| Road camber (inner) | deg | -2.9756 | -2.9756 | 3.0358 | 6.0114 |
| Camber (left) | deg | -0.0488 | -3.0481 | -0.0488 | 2.9993 |
| Camber (right) | deg | -0.0436 | -0.0436 | 6.4055 | 6.4491 |
| Caster (left) | deg | 9.0012 | 9.0010 | 9.0012 | 0.0002 |
| Caster (right) | deg | 9.0010 | 9.0006 | 9.0010 | 0.0004 |
| Toe (left) | deg | -0.0086 | -0.0086 | 22.8241 | 22.8327 |
| Toe (right) | deg | 0.0111 | -29.0950 | 0.0111 | 29.1061 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.331 | 0.331 |
| Mechanical trail | mm | 44.115 | 28.229 | 44.115 | 15.886 |
| Half track | mm | 488.608 | 488.608 | 499.784 | 11.176 |
| Track change | mm | -2.493 | -23.855 | -2.493 | 21.362 |
| Damper length | mm | 246.106 | 246.106 | 247.607 | 1.501 |
| Roll-centre height | mm | -353.984 | -373.659 | -326.355 | 47.304 |
| Roll-centre lateral position | mm | -2397.260 | -2886.225 | -2332.594 | 553.631 |
| Body roll | deg | 2.9333 | 2.9332 | 2.9565 | 0.0233 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 125.53 | 176.28 | 50.75 |
| Steering ratio (rack) | deg/mm | 0.6737 | 0.6461 | 0.6737 | 0.0276 |

Plots: `plots/09_steer_in_roll.png`

## 10_corner_ramp  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | -0.0000 | -0.2104 | -0.0000 | 0.2104 |
| Road camber (inner) | deg | -0.0000 | -0.0000 | 3.0358 | 3.0358 |
| Camber (left) | deg | -0.0000 | -3.0481 | -0.0000 | 3.0481 |
| Camber (right) | deg | -0.0000 | -0.0000 | 6.4055 | 6.4055 |
| Caster (left) | deg | 8.9999 | 8.9999 | 9.0010 | 0.0011 |
| Caster (right) | deg | 8.9999 | 8.9999 | 9.0006 | 0.0007 |
| Toe (left) | deg | -0.0000 | -0.0000 | 22.8241 | 22.8241 |
| Toe (right) | deg | 0.0000 | -29.0950 | 0.0000 | 29.0950 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.331 | 0.331 |
| Half track | mm | 490.000 | 490.000 | 499.784 | 9.784 |
| Track change | mm | 0.000 | -23.855 | 0.000 | 23.855 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4686 | 1.4916 | 0.0230 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6704 | 0.6809 | 0.0105 |
| Roll-centre height | mm | 9.727 | -373.659 | 9.727 | 383.386 |
| Roll-centre lateral position | mm | -0.000 | -2886.226 | -0.000 | 2886.226 |
| Body roll | deg | -0.0000 | -0.0000 | 2.9565 | 2.9565 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 98.37 | 140.54 | 42.17 |
| Steering ratio (rack) | deg/mm | 0.6883 | 0.6511 | 0.6883 | 0.0371 |

Plots: `plots/10_corner_ramp.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LBJ | spherical | 21.44 | `06_steer_droop` step 64 | - | - | 0.00 | 20.32 | - |
| UBJ | spherical | - | - | - | - | - | 23.11 | - |
| Outer Tie Rod End | rod_end | - | - | - | - | - | 23.16 | - |
| Inner Tie Rod End | rod_end | 11.14 | `06_steer_droop` step 0 | 11.14 | 267.5 | 0.82 | 5.93 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/08_damper_stroke.png`
- `plots/09_steer_in_roll.png`
- `plots/10_corner_ramp.png`
