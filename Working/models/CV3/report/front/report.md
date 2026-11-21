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
- geometry SHA-256: `fc59b2fc25471eb4...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV3\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 65 | True | 2.73e-06 | - |
| `02_roll` | roll | 65 | True | 3.38e-06 | - |
| `04_steer_design` | steer | 65 | True | 5.75e-06 | - |
| `05_steer_bump` | steer | 65 | True | 4.40e-06 | Held at +50.8 mm wheel travel, not design height. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 4.31e-06 | Held at -50.8 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a right turn, so the LEFT wheel is outer and should be in bump, but it is at -50.8 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 4.56e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 4.05e-06 | Held at +25.0/-25.0 mm wheel travel (+2.99 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_steady_corner` | roll_ramp_at_steer | 33 | True | 1.23e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Camber | deg | -0.0000 | -0.2096 | 0.0001 | 0.2097 |
| Caster | deg | 8.9999 | 8.9999 | 9.0053 | 0.0054 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0088 | 0.0120 | 0.0208 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.000 | 0.000 |
| Mechanical trail | mm | 44.110 | 44.100 | 44.117 | 0.017 |
| Half track | mm | 480.000 | 471.017 | 480.032 | 9.014 |
| Wheel travel | mm | -0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 262.991 | 228.412 | 296.681 | 68.269 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4480 | 1.5175 | 0.0694 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6590 | 0.6906 | 0.0316 |
| Roll-centre height | mm | 9.528 | -89.765 | 110.389 | 200.153 |
| FVIC lateral (y) | mm | -246127.400 | -18684440.384 | 251787.786 | 18936228.170 |
| FVIC height (z) | mm | 4895.299 | -9787.127 | 549103.836 | 558890.963 |
| FVSA length | mm | 246655.983 | -251498.261 | 18692987.056 | 18944485.317 |
| Track change | mm | 0.000 | -17.965 | 0.063 | 18.028 |
| Steering ratio (rack) | deg/mm | 0.6883 | 0.6574 | 0.7246 | 0.0672 |
| Camber gain | deg/mm | -0.0002 | -0.0082 | 0.0096 | 0.0178 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.0488 | 0.0001 | 0.0489 |
| Camber (right) | deg | 0.0000 | -0.0488 | 0.0001 | 0.0489 |
| Caster (left) | deg | 8.9999 | 8.9999 | 9.0012 | 0.0013 |
| Caster (right) | deg | 8.9999 | 8.9999 | 9.0012 | 0.0013 |
| Toe (left) | deg | 0.0000 | -0.0086 | 0.0111 | 0.0197 |
| Toe (right) | deg | -0.0000 | -0.0086 | 0.0111 | 0.0197 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.000 | 0.000 |
| Half track | mm | 480.000 | 477.620 | 480.032 | 2.412 |
| Track change | mm | 0.000 | -2.466 | 0.000 | 2.466 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4693 | 1.5094 | 0.0400 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6625 | 0.6806 | 0.0181 |
| Camber recovery | deg/deg | -0.0013 | -0.0308 | 0.0308 | 0.0616 |
| Roll-centre height | mm | 9.528 | -342.935 | 9.528 | 352.463 |
| Roll-centre lateral migration vs roll | mm/deg | -794.4065 | -794.4065 | -740.8583 | 53.5482 |
| Body roll | deg | -0.0000 | -2.9946 | 2.9946 | 5.9892 |
| Steering ratio (rack) | deg/mm | 0.6883 | 0.6737 | 0.7040 | 0.0303 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0102 | -2.7006 | 4.2836 | 6.9842 |
| Caster | deg | 8.9999 | 8.9999 | 9.0000 | 0.0000 |
| Toe (positive = toe-in) | deg | 0.0645 | -21.4644 | 20.1108 | 41.5752 |
| Scrub radius (signed lateral) | mm | 0.001 | -0.410 | 0.377 | 0.788 |
| Mechanical trail | mm | 44.057 | 25.446 | 58.241 | 32.795 |
| Half track | mm | 480.049 | 458.748 | 488.674 | 29.927 |
| Track change | mm | -0.000 | -14.674 | -0.000 | 14.673 |
| Damper length | mm | 262.997 | 260.859 | 264.346 | 3.487 |
| Roll-centre height | mm | 9.528 | -0.221 | 9.528 | 9.749 |
| Roll-centre lateral position | mm | 1.232 | -451.660 | 504.091 | 955.751 |
| FVIC lateral (y) | mm | -247377.385 | -15207964.810 | 14754161.601 | 29962126.412 |
| FVIC height (z) | mm | 4932.224 | -437827.747 | 446496.455 | 884324.201 |
| FVSA length | mm | 247906.504 | -14760168.700 | 15215005.390 | 29975174.089 |
| Rack displacement | mm | 0.094 | -28.000 | 30.000 | 58.000 |
| Ackermann | % | - | 77.35 | 98.19 | 20.84 |
| Steering ratio (rack) | deg/mm | 0.6880 | 0.6650 | 0.9163 | 0.2513 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.2139 | -2.9030 | 3.8554 | 6.7583 |
| Caster | deg | 9.0051 | 9.0047 | 9.0058 | 0.0011 |
| Toe (positive = toe-in) | deg | 0.0822 | -20.6499 | 20.2646 | 40.9144 |
| Scrub radius (signed lateral) | mm | 0.002 | -0.411 | 0.385 | 0.796 |
| Mechanical trail | mm | 44.041 | 24.981 | 58.263 | 33.282 |
| Half track | mm | 473.189 | 451.671 | 482.331 | 30.661 |
| Track change | mm | -13.755 | -30.424 | -13.755 | 16.669 |
| Damper length | mm | 228.419 | 226.300 | 229.809 | 3.509 |
| Roll-centre height | mm | -89.765 | -89.765 | -89.015 | 0.749 |
| Roll-centre lateral position | mm | -0.048 | -12.089 | 10.631 | 22.720 |
| FVIC lateral (y) | mm | -6606.081 | -6961.268 | -6107.499 | 853.770 |
| FVIC height (z) | mm | -2051.968 | -2058.568 | -2038.687 | 19.881 |
| FVSA length | mm | 7384.964 | 6884.110 | 7736.791 | 852.681 |
| Rack displacement | mm | 0.125 | -28.000 | 32.000 | 60.000 |
| Ackermann | % | - | 93.51 | 123.22 | 29.71 |
| Steering ratio (rack) | deg/mm | 0.6571 | 0.6250 | 0.8868 | 0.2619 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.2240 | -3.0021 | 4.1258 | 7.1278 |
| Caster | deg | 9.0053 | 9.0045 | 9.0059 | 0.0013 |
| Toe (positive = toe-in) | deg | 0.0908 | -21.5406 | 20.7363 | 42.2769 |
| Scrub radius (signed lateral) | mm | 0.002 | -0.423 | 0.393 | 0.816 |
| Mechanical trail | mm | 44.034 | 24.423 | 58.624 | 34.201 |
| Half track | mm | 471.083 | 450.589 | 478.913 | 28.324 |
| Track change | mm | -17.966 | -32.571 | -17.966 | 14.605 |
| Damper length | mm | 296.689 | 294.571 | 298.035 | 3.464 |
| Roll-centre height | mm | 110.389 | 105.410 | 110.389 | 4.979 |
| Roll-centre lateral position | mm | 0.185 | -40.110 | 43.151 | 83.261 |
| FVIC lateral (y) | mm | 6315.050 | 5949.459 | 6948.807 | 999.348 |
| FVIC height (z) | mm | -2051.165 | -2119.875 | -2007.324 | 112.550 |
| FVSA length | mm | -6176.846 | -6819.861 | -5810.006 | 1009.854 |
| Rack displacement | mm | 0.125 | -27.000 | 29.000 | 56.000 |
| Ackermann | % | - | 59.81 | 78.07 | 18.27 |
| Steering ratio (rack) | deg/mm | 0.7243 | 0.7103 | 0.9427 | 0.2324 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 262.991 | 232.991 | 292.991 | 60.000 |
| Wheel travel (left) | mm | 0.000 | -45.201 | 44.159 | 89.360 |
| Wheel travel (right) | mm | 0.000 | -45.201 | 44.159 | 89.360 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4534 | 1.5168 | 0.0634 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6593 | 0.6880 | 0.0288 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 2.9444 | 0.1623 | 2.9444 | 2.7821 |
| Road camber (inner) | deg | -3.0368 | -3.0368 | 2.1812 | 5.2180 |
| Camber (left) | deg | -0.0488 | -2.8302 | -0.0488 | 2.7814 |
| Camber (right) | deg | -0.0436 | -0.0436 | 5.4248 | 5.4684 |
| Caster (left) | deg | 9.0012 | 9.0010 | 9.0012 | 0.0002 |
| Caster (right) | deg | 9.0010 | 9.0007 | 9.0010 | 0.0003 |
| Toe (left) | deg | -0.0086 | -0.0086 | 20.8728 | 20.8814 |
| Toe (right) | deg | 0.0111 | -25.8131 | 0.0111 | 25.8241 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.303 | 0.303 |
| Mechanical trail | mm | 44.115 | 29.905 | 44.115 | 14.210 |
| Half track | mm | 478.608 | 478.608 | 489.481 | 10.873 |
| Track change | mm | -2.466 | -19.955 | -2.466 | 17.489 |
| Damper length | mm | 246.106 | 246.106 | 247.517 | 1.411 |
| Roll-centre height | mm | -342.935 | -342.935 | -315.683 | 27.251 |
| Roll-centre lateral position | mm | -2323.123 | -2600.181 | -2258.337 | 341.843 |
| Body roll | deg | 2.9946 | 2.9945 | 3.0137 | 0.0192 |
| Rack displacement | mm | -0.000 | -0.000 | 32.000 | 32.000 |
| Ackermann | % | - | 131.39 | 181.14 | 49.75 |
| Steering ratio (rack) | deg/mm | 0.6737 | 0.6461 | 0.6737 | 0.0276 |

Plots: `plots/09_steer_in_roll.png`

## 10_steady_corner  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 0.0182 | 0.0182 | 0.7970 | 0.7787 |
| Road camber (inner) | deg | -0.0143 | -0.0345 | 0.1820 | 0.2165 |
| Camber (left) | deg | -0.1567 | -2.0638 | -0.1567 | 1.9071 |
| Camber (right) | deg | 0.1606 | 0.1606 | 3.0760 | 2.9154 |
| Caster (left) | deg | 8.9999 | 8.9999 | 9.0013 | 0.0014 |
| Caster (right) | deg | 8.9999 | 8.9999 | 9.0004 | 0.0005 |
| Toe (left) | deg | 0.9953 | 0.9953 | 14.3224 | 13.3271 |
| Toe (right) | deg | -1.0035 | -16.4728 | -1.0035 | 15.4694 |
| Scrub radius (signed lateral) | mm | 0.020 | 0.020 | 0.213 | 0.193 |
| Half track | mm | 480.774 | 480.774 | 487.012 | 6.239 |
| Track change | mm | -0.040 | -10.008 | -0.040 | 9.967 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4903 | 1.4662 | 1.4903 | 0.0241 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6710 | 0.6710 | 0.6820 | 0.0110 |
| Roll-centre height | mm | 8.523 | -5679.994 | 6123.238 | 11803.233 |
| Roll-centre lateral position | mm | -120.428 | -49046.732 | 50939.004 | 99985.735 |
| Body roll | deg | 0.1749 | 0.1749 | 2.8838 | 2.7089 |
| Rack displacement | mm | 1.453 | 1.453 | 21.940 | 20.487 |
| Ackermann | % | - | 113.95 | 131.31 | 17.37 |
| Steering ratio (rack) | deg/mm | 0.6837 | 0.6441 | 0.6837 | 0.0397 |

Plots: `plots/10_steady_corner.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LBJ | spherical | 19.65 | `06_steer_droop` step 64 | - | - | 0.00 | 18.67 | - |
| UBJ | spherical | - | - | - | - | - | 21.21 | - |
| Outer Tie Rod End | rod_end | - | - | - | - | - | 22.02 | - |
| Inner Tie Rod End | rod_end | 7.27 | `06_steer_droop` step 0 | 7.31 | 269.2 | 0.82 | 4.02 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/08_damper_stroke.png`
- `plots/09_steer_in_roll.png`
- `plots/10_steady_corner.png`
