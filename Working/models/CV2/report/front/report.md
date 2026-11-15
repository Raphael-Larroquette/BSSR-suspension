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

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\CV2\front.yaml`
- geometry SHA-256: `f38153da12a40561...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\CV2\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 65 | True | 3.24e-06 | - |
| `02_roll` | roll | 65 | True | 4.37e-06 | - |
| `04_steer_design` | steer | 65 | True | 4.88e-06 | - |
| `05_steer_bump` | steer | 65 | True | 4.50e-06 | Held at +50.8 mm wheel travel, not design height. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 3.22e-06 | Held at -50.8 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a right turn, so the LEFT wheel is outer and should be in bump, but it is at -50.8 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 2.74e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 2.84e-06 | Held at +25.0/-25.0 mm wheel travel (+2.93 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_corner_ramp` | roll_ramp_at_steer | 65 | True | 4.58e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

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
| Toe (positive = toe-in) | deg | 0.0000 | -0.0088 | 0.0120 | 0.0208 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.000 | 0.000 |
| Mechanical trail | mm | 44.110 | 44.100 | 44.117 | 0.017 |
| Half track | mm | 490.000 | 481.017 | 490.032 | 9.014 |
| Wheel travel | mm | -0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 262.991 | 228.412 | 296.681 | 68.269 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4480 | 1.5175 | 0.0694 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6590 | 0.6906 | 0.0316 |
| Roll-centre height | mm | 9.727 | -92.736 | 113.811 | 206.546 |
| FVIC lateral (y) | mm | -246117.346 | -18684517.830 | 251797.787 | 18936315.617 |
| FVIC height (z) | mm | 4895.300 | -9787.127 | 549106.366 | 558893.493 |
| FVSA length | mm | 246655.929 | -251498.262 | 18693074.539 | 18944572.801 |
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
| Half track | mm | 490.000 | 487.620 | 490.032 | 2.412 |
| Track change | mm | 0.000 | -2.493 | 0.000 | 2.493 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4693 | 1.5094 | 0.0400 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6625 | 0.6806 | 0.0181 |
| Camber recovery | deg/deg | -0.0013 | -0.0315 | 0.0314 | 0.0629 |
| Roll-centre height | mm | 9.727 | -353.984 | 9.727 | 363.710 |
| Roll-centre lateral migration vs roll | mm/deg | -836.8295 | -836.8295 | -780.5579 | 56.2716 |
| Body roll | deg | -0.0000 | -2.9333 | 2.9333 | 5.8667 |
| Steering ratio (rack) | deg/mm | 0.6883 | 0.6737 | 0.7040 | 0.0303 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0102 | -2.7006 | 4.2836 | 6.9842 |
| Caster | deg | 8.9999 | 8.9999 | 9.0000 | 0.0000 |
| Toe (positive = toe-in) | deg | 0.0645 | -21.4644 | 20.1108 | 41.5752 |
| Scrub radius (signed lateral) | mm | 0.001 | -0.410 | 0.377 | 0.788 |
| Mechanical trail | mm | 44.057 | 25.447 | 58.242 | 32.795 |
| Half track | mm | 490.049 | 468.748 | 498.675 | 29.927 |
| Track change | mm | -0.000 | -14.674 | -0.000 | 14.674 |
| Damper length | mm | 262.997 | 260.859 | 264.346 | 3.487 |
| Roll-centre height | mm | 9.727 | -0.243 | 9.727 | 9.970 |
| Roll-centre lateral position | mm | 1.256 | -461.162 | 514.788 | 975.950 |
| FVIC lateral (y) | mm | -247367.391 | -15207963.212 | 14754208.519 | 29962171.731 |
| FVIC height (z) | mm | 4932.223 | -437828.852 | 446496.698 | 884325.550 |
| FVSA length | mm | 247906.509 | -14760205.633 | 15215013.795 | 29975219.428 |
| Rack displacement | mm | 0.094 | -28.000 | 30.000 | 58.000 |
| Ackermann | % | - | 74.14 | 93.69 | 19.55 |
| Steering ratio (rack) | deg/mm | 0.6880 | 0.6650 | 0.9163 | 0.2513 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.2139 | -2.9030 | 3.8554 | 6.7583 |
| Caster | deg | 9.0051 | 9.0047 | 9.0058 | 0.0011 |
| Toe (positive = toe-in) | deg | 0.0822 | -20.6499 | 20.2646 | 40.9144 |
| Scrub radius (signed lateral) | mm | 0.002 | -0.411 | 0.385 | 0.796 |
| Mechanical trail | mm | 44.041 | 24.982 | 58.264 | 33.282 |
| Half track | mm | 483.189 | 461.671 | 492.332 | 30.661 |
| Track change | mm | -13.755 | -30.424 | -13.755 | 16.669 |
| Damper length | mm | 228.419 | 226.300 | 229.809 | 3.509 |
| Roll-centre height | mm | -92.736 | -92.736 | -92.035 | 0.701 |
| Roll-centre lateral position | mm | -0.051 | -12.744 | 11.194 | 23.938 |
| FVIC lateral (y) | mm | -6596.081 | -6951.268 | -6097.499 | 853.770 |
| FVIC height (z) | mm | -2051.968 | -2058.568 | -2038.687 | 19.881 |
| FVSA length | mm | 7384.964 | 6884.110 | 7736.792 | 852.682 |
| Rack displacement | mm | 0.125 | -28.000 | 32.000 | 60.000 |
| Ackermann | % | - | 89.63 | 117.57 | 27.94 |
| Steering ratio (rack) | deg/mm | 0.6571 | 0.6250 | 0.8868 | 0.2619 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.2240 | -3.0021 | 4.1258 | 7.1278 |
| Caster | deg | 9.0053 | 9.0045 | 9.0059 | 0.0013 |
| Toe (positive = toe-in) | deg | 0.0908 | -21.5406 | 20.7363 | 42.2769 |
| Scrub radius (signed lateral) | mm | 0.002 | -0.423 | 0.393 | 0.816 |
| Mechanical trail | mm | 44.034 | 24.424 | 58.625 | 34.201 |
| Half track | mm | 481.083 | 460.588 | 488.913 | 28.325 |
| Track change | mm | -17.966 | -32.571 | -17.966 | 14.605 |
| Damper length | mm | 296.689 | 294.571 | 298.035 | 3.464 |
| Roll-centre height | mm | 113.811 | 108.766 | 113.811 | 5.044 |
| Roll-centre lateral position | mm | 0.188 | -40.680 | 43.768 | 84.447 |
| FVIC lateral (y) | mm | 6325.050 | 5959.459 | 6958.807 | 999.348 |
| FVIC height (z) | mm | -2051.165 | -2119.875 | -2007.324 | 112.550 |
| FVSA length | mm | -6176.846 | -6819.861 | -5810.006 | 1009.855 |
| Rack displacement | mm | 0.125 | -27.000 | 29.000 | 56.000 |
| Ackermann | % | - | 57.33 | 74.48 | 17.15 |
| Steering ratio (rack) | deg/mm | 0.7243 | 0.7103 | 0.9427 | 0.2324 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 262.991 | 232.991 | 292.991 | 60.000 |
| Wheel travel (left) | mm | -0.000 | -45.201 | 44.159 | 89.360 |
| Wheel travel (right) | mm | -0.000 | -45.201 | 44.159 | 89.360 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4534 | 1.5168 | 0.0634 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6593 | 0.6880 | 0.0288 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 2.8832 | 0.1038 | 2.8832 | 2.7794 |
| Road camber (inner) | deg | -2.9756 | -2.9756 | 2.2375 | 5.2131 |
| Camber (left) | deg | -0.0488 | -2.8302 | -0.0488 | 2.7814 |
| Camber (right) | deg | -0.0436 | -0.0436 | 5.4248 | 5.4684 |
| Caster (left) | deg | 9.0012 | 9.0010 | 9.0012 | 0.0002 |
| Caster (right) | deg | 9.0010 | 9.0007 | 9.0010 | 0.0003 |
| Toe (left) | deg | -0.0086 | -0.0086 | 20.8728 | 20.8814 |
| Toe (right) | deg | 0.0111 | -25.8131 | 0.0111 | 25.8241 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.305 | 0.305 |
| Mechanical trail | mm | 44.115 | 29.795 | 44.115 | 14.319 |
| Half track | mm | 488.608 | 488.608 | 499.443 | 10.835 |
| Track change | mm | -2.493 | -19.963 | -2.493 | 17.470 |
| Damper length | mm | 246.106 | 246.106 | 247.517 | 1.411 |
| Roll-centre height | mm | -353.984 | -353.984 | -326.355 | 27.629 |
| Roll-centre lateral position | mm | -2397.260 | -2692.437 | -2332.592 | 359.845 |
| Body roll | deg | 2.9333 | 2.9332 | 2.9517 | 0.0185 |
| Rack displacement | mm | 0.000 | 0.000 | 32.000 | 32.000 |
| Ackermann | % | - | 125.53 | 179.10 | 53.57 |
| Steering ratio (rack) | deg/mm | 0.6737 | 0.6461 | 0.6737 | 0.0276 |

Plots: `plots/09_steer_in_roll.png`

## 10_corner_ramp  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | -0.0000 | -0.0955 | 0.1038 | 0.1993 |
| Road camber (inner) | deg | -0.0000 | -0.0000 | 2.2375 | 2.2375 |
| Camber (left) | deg | -0.0000 | -2.8302 | -0.0000 | 2.8302 |
| Camber (right) | deg | -0.0000 | -0.0000 | 5.4248 | 5.4248 |
| Caster (left) | deg | 8.9999 | 8.9999 | 9.0010 | 0.0011 |
| Caster (right) | deg | 8.9999 | 8.9999 | 9.0007 | 0.0007 |
| Toe (left) | deg | -0.0000 | -0.0000 | 20.8728 | 20.8728 |
| Toe (right) | deg | 0.0000 | -25.8130 | 0.0000 | 25.8130 |
| Scrub radius (signed lateral) | mm | -0.000 | -0.000 | 0.305 | 0.305 |
| Half track | mm | 490.000 | 490.000 | 499.443 | 9.443 |
| Track change | mm | 0.000 | -19.963 | 0.000 | 19.963 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.4916 | 1.4686 | 1.4916 | 0.0230 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.6704 | 0.6704 | 0.6809 | 0.0105 |
| Roll-centre height | mm | 9.727 | -353.379 | 9.727 | 363.105 |
| Roll-centre lateral position | mm | -0.000 | -2692.437 | -0.000 | 2692.437 |
| Body roll | deg | -0.0000 | -0.0000 | 2.9517 | 2.9517 |
| Rack displacement | mm | 0.000 | 0.000 | 32.000 | 32.000 |
| Ackermann | % | - | 100.58 | 132.83 | 32.25 |
| Steering ratio (rack) | deg/mm | 0.6883 | 0.6493 | 0.6883 | 0.0390 |

Plots: `plots/10_corner_ramp.png`

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
- `plots/10_corner_ramp.png`
