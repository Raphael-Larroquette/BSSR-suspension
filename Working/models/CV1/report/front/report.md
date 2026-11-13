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

- geometry: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV1\front.yaml`
- geometry SHA-256: `d0141143db174f87...`
- format version: 3
- reported side: **left**
- run configuration: `C:\Users\General\Desktop\BSSR-suspension\Working\models\CV1\report\front\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 4.14e-06 | - |
| `02_roll` | roll | 65 | True | 5.42e-06 | - |
| `04_steer_design` | steer | 65 | True | 2.68e-06 | - |
| `05_steer_bump` | steer | 65 | True | 3.41e-06 | Held at +50.0 mm wheel travel, not design height. Outer/inner road camber: left turn, so OUTER = RIGHT wheel and INNER = LEFT wheel throughout. |
| `06_steer_droop` | steer | 65 | True | 4.30e-06 | Held at -55.0 mm wheel travel, not design height. **Rolled the wrong way for its steer.** This is a left turn, so the RIGHT wheel is outer and should be in bump, but it is at -55.0 mm. The frames are a transient, not a corner; flip the travel signs in run.yaml. Outer/inner road camber: left turn, so OUTER = RIGHT wheel and INNER = LEFT wheel throughout. |
| `08_damper_stroke` | damper_stroke | 65 | True | 2.74e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |
| `09_steer_in_roll` | steer_in_roll | 65 | True | 5.80e-06 | Held at +25.0/-25.0 mm wheel travel (+2.87 deg roll) - this is a ROLLED sweep. Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |
| `10_corner_ramp` | roll_ramp_at_steer | 65 | True | 3.65e-06 | Outer/inner road camber: right turn, so OUTER = LEFT wheel and INNER = RIGHT wheel throughout. |

## Notes

Conventions, formulas and the meaningful source sweep for every channel are documented in `CHARACTERISTICS.md`. The ones that bite most often:

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
| Camber | deg | -0.0000 | -0.7773 | 0.0807 | 0.8580 |
| Caster | deg | 6.9999 | 6.9982 | 7.0169 | 0.0187 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0000 | 0.0000 | 0.0001 |
| Scrub radius (signed lateral) | mm | 0.001 | 0.001 | 0.001 | 0.000 |
| Mechanical trail | mm | 34.195 | 34.195 | 34.195 | 0.000 |
| Half track | mm | 500.000 | 496.306 | 500.060 | 3.753 |
| Wheel travel | mm | -0.000 | -55.000 | 50.000 | 105.000 |
| Damper length | mm | 271.220 | 235.108 | 311.445 | 76.337 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.3762 | 1.3575 | 1.3946 | 0.0371 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7267 | 0.7171 | 0.7366 | 0.0196 |
| Roll-centre height | mm | 7.723 | 3.555 | 10.925 | 7.370 |
| FVIC lateral (y) | mm | -7303.854 | -85028.692 | 54061.973 | 139090.665 |
| FVIC height (z) | mm | 120.543 | -3382.287 | 4536.187 | 7918.474 |
| FVSA length | mm | 7804.785 | -53668.064 | 85649.275 | 139317.339 |
| Track change | mm | 0.000 | -7.387 | 0.120 | 7.507 |
| Steering ratio (rack) | deg/mm | 0.5772 | 0.5517 | 0.6072 | 0.0555 |
| Camber gain | deg/mm | -0.0073 | -0.0240 | 0.0127 | 0.0367 |

Plots: `plots/01_bump_parallel.png`

## 02_roll  (roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber (left) | deg | -0.0000 | -0.2851 | 0.0814 | 0.3665 |
| Camber (right) | deg | 0.0000 | -0.2851 | 0.0814 | 0.3665 |
| Caster (left) | deg | 6.9999 | 6.9982 | 7.0060 | 0.0078 |
| Caster (right) | deg | 6.9999 | 6.9982 | 7.0060 | 0.0078 |
| Toe (left) | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Toe (right) | deg | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Scrub radius (signed lateral) | mm | 0.001 | 0.001 | 0.001 | 0.000 |
| Half track | mm | 500.000 | 499.023 | 500.063 | 1.040 |
| Track change | mm | 0.000 | 0.000 | 0.068 | 0.068 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.3762 | 1.3684 | 1.3843 | 0.0159 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7267 | 0.7224 | 0.7308 | 0.0084 |
| Camber recovery | deg/deg | -0.0641 | -0.1335 | 0.0081 | 0.1416 |
| Roll-centre height | mm | 7.723 | 7.723 | 12.016 | 4.293 |
| Roll-centre lateral migration vs roll | mm/deg | 29.9462 | 29.9462 | 35.7502 | 5.8040 |
| Body roll | deg | -0.0000 | -2.8687 | 2.8687 | 5.7373 |
| Steering ratio (rack) | deg/mm | 0.5772 | 0.5649 | 0.5896 | 0.0247 |

Plots: `plots/02_roll.png`

## 04_steer_design  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -1.8778 | 3.6077 | 5.4855 |
| Caster | deg | 6.9999 | 6.9997 | 7.0004 | 0.0007 |
| Toe (positive = toe-in) | deg | -0.0000 | -21.9582 | 19.6331 | 41.5913 |
| Scrub radius (signed lateral) | mm | 0.001 | -0.412 | 0.286 | 0.698 |
| Mechanical trail | mm | 34.195 | 15.816 | 50.262 | 34.445 |
| Half track | mm | 500.000 | 481.272 | 505.358 | 24.086 |
| Track change | mm | 0.000 | -13.455 | 0.000 | 13.455 |
| Damper length | mm | 271.220 | 269.151 | 272.313 | 3.162 |
| Roll-centre height | mm | 7.723 | 6.874 | 7.723 | 0.850 |
| Roll-centre lateral position | mm | 0.000 | -132.638 | 132.638 | 265.276 |
| FVIC lateral (y) | mm | -7303.854 | -7863.782 | -6428.407 | 1435.375 |
| FVIC height (z) | mm | 120.543 | 72.493 | 151.528 | 79.035 |
| FVSA length | mm | 7804.785 | 6910.054 | 8370.424 | 1460.370 |
| Rack displacement | mm | 0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 59.79 | 69.22 | 9.43 |
| Steering ratio (rack) | deg/mm | 0.5772 | 0.5530 | 0.7145 | 0.1616 |

Plots: `plots/04_steer_design.png`

## 05_steer_bump  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.7773 | -2.5623 | 2.5764 | 5.1387 |
| Caster | deg | 7.0169 | 7.0162 | 7.0185 | 0.0023 |
| Toe (positive = toe-in) | deg | -0.0000 | -20.9796 | 18.6890 | 39.6686 |
| Scrub radius (signed lateral) | mm | 0.001 | -0.442 | 0.289 | 0.730 |
| Mechanical trail | mm | 34.195 | 15.615 | 51.209 | 35.594 |
| Half track | mm | 498.413 | 479.922 | 503.568 | 23.646 |
| Track change | mm | -3.174 | -16.588 | -3.174 | 13.414 |
| Damper length | mm | 235.108 | 233.138 | 236.129 | 2.991 |
| Roll-centre height | mm | 10.925 | 10.925 | 11.126 | 0.201 |
| Roll-centre lateral position | mm | 0.000 | -8.990 | 8.990 | 17.980 |
| FVIC lateral (y) | mm | -1891.750 | -1942.978 | -1797.883 | 145.095 |
| FVIC height (z) | mm | -137.481 | -138.968 | -136.519 | 2.449 |
| FVSA length | mm | 2397.507 | 2285.650 | 2453.587 | 167.937 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 66.11 | 75.47 | 9.36 |
| Steering ratio (rack) | deg/mm | 0.5517 | 0.5233 | 0.6793 | 0.1560 |

Plots: `plots/05_steer_bump.png`

## 06_steer_droop  (steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.1208 | -2.1044 | 3.8241 | 5.9285 |
| Caster | deg | 7.0024 | 7.0017 | 7.0029 | 0.0012 |
| Toe (positive = toe-in) | deg | 0.0000 | -23.2006 | 20.6931 | 43.8938 |
| Scrub radius (signed lateral) | mm | 0.001 | -0.437 | 0.299 | 0.736 |
| Mechanical trail | mm | 34.195 | 14.498 | 51.097 | 36.599 |
| Half track | mm | 496.306 | 476.565 | 501.456 | 24.891 |
| Track change | mm | -7.387 | -22.213 | -7.387 | 14.826 |
| Damper length | mm | 311.445 | 309.205 | 312.584 | 3.379 |
| Roll-centre height | mm | 3.555 | 2.172 | 3.555 | 1.384 |
| Roll-centre lateral position | mm | -0.000 | -31.201 | 31.201 | 62.403 |
| FVIC lateral (y) | mm | 4998.822 | 4769.380 | 5517.579 | 748.199 |
| FVIC height (z) | mm | -586.209 | -616.862 | -572.506 | 44.355 |
| FVSA length | mm | -4533.744 | -5072.287 | -4299.437 | 772.850 |
| Rack displacement | mm | -0.000 | -35.000 | 35.000 | 70.000 |
| Ackermann | % | - | 56.39 | 67.02 | 10.63 |
| Steering ratio (rack) | deg/mm | 0.6072 | 0.5844 | 0.7640 | 0.1795 |

Plots: `plots/06_steer_droop.png`

## 08_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 271.220 | 241.220 | 301.220 | 60.000 |
| Wheel travel (left) | mm | 0.000 | -41.091 | 41.489 | 82.581 |
| Wheel travel (right) | mm | 0.000 | -41.091 | 41.489 | 82.581 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.3762 | 1.3631 | 1.3904 | 0.0273 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7267 | 0.7192 | 0.7336 | 0.0144 |

Plots: `plots/08_damper_stroke.png`

## 09_steer_in_roll  (steer_in_roll)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | 2.5808 | 0.7250 | 2.5808 | 1.8558 |
| Road camber (inner) | deg | -2.7862 | -2.7862 | 0.8650 | 3.6512 |
| Camber (left) | deg | -0.2851 | -2.1183 | -0.2851 | 1.8331 |
| Camber (right) | deg | 0.0797 | 0.0797 | 3.8215 | 3.7418 |
| Caster (left) | deg | 7.0060 | 7.0055 | 7.0060 | 0.0005 |
| Caster (right) | deg | 6.9982 | 6.9982 | 6.9982 | 0.0000 |
| Toe (left) | deg | -0.0000 | -0.0000 | 19.1822 | 19.1822 |
| Toe (right) | deg | 0.0000 | -22.4589 | 0.0000 | 22.4589 |
| Scrub radius (signed lateral) | mm | 0.001 | 0.001 | 0.231 | 0.231 |
| Mechanical trail | mm | 34.195 | 20.489 | 34.195 | 13.705 |
| Half track | mm | 499.795 | 499.795 | 506.540 | 6.746 |
| Track change | mm | 0.068 | -14.278 | 0.068 | 14.347 |
| Damper length | mm | 253.105 | 253.105 | 254.167 | 1.062 |
| Roll-centre height | mm | 12.016 | 12.016 | 18.130 | 6.114 |
| Roll-centre lateral position | mm | 91.542 | 91.542 | 266.051 | 174.509 |
| Body roll | deg | 2.8687 | 2.8686 | 2.8847 | 0.0160 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 102.19 | 157.37 | 55.17 |
| Steering ratio (rack) | deg/mm | 0.5649 | 0.5389 | 0.5649 | 0.0260 |

Plots: `plots/09_steer_in_roll.png`

## 10_corner_ramp  (roll_ramp_at_steer)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Road camber (outer) | deg | -0.0000 | -0.0000 | 0.7250 | 0.7250 |
| Road camber (inner) | deg | -0.0000 | -0.0157 | 0.8650 | 0.8807 |
| Camber (left) | deg | -0.0000 | -2.1183 | -0.0000 | 2.1183 |
| Camber (right) | deg | -0.0000 | -0.0000 | 3.8215 | 3.8215 |
| Caster (left) | deg | 6.9999 | 6.9999 | 7.0055 | 0.0056 |
| Caster (right) | deg | 6.9999 | 6.9982 | 6.9999 | 0.0017 |
| Toe (left) | deg | -0.0000 | -0.0000 | 19.1822 | 19.1822 |
| Toe (right) | deg | 0.0000 | -22.4589 | 0.0000 | 22.4589 |
| Scrub radius (signed lateral) | mm | 0.001 | 0.001 | 0.231 | 0.231 |
| Half track | mm | 500.000 | 500.000 | 506.540 | 6.540 |
| Track change | mm | 0.000 | -14.278 | 0.000 | 14.278 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.3762 | 1.3762 | 1.3815 | 0.0054 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.7267 | 0.7238 | 0.7267 | 0.0028 |
| Roll-centre height | mm | 7.723 | 7.723 | 18.130 | 10.407 |
| Roll-centre lateral position | mm | -0.000 | -0.000 | 266.051 | 266.051 |
| Body roll | deg | 0.0000 | 0.0000 | 2.8847 | 2.8847 |
| Rack displacement | mm | 0.000 | 0.000 | 35.000 | 35.000 |
| Ackermann | % | - | 87.28 | 102.33 | 15.05 |
| Steering ratio (rack) | deg/mm | 0.5772 | 0.5389 | 0.5772 | 0.0382 |

Plots: `plots/10_corner_ramp.png`

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep, and only over the sweeps that actually ran. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. Best available is what the joint would need if its bore axis were chosen to minimise the worst case.

**Size against `required (locked)` where it is populated.** Those housings ride a two-point member whose roll about its own axis no kinematic model can determine. The plain `required` column is a lower bound that assumes the member turns freely to the best position at every instant; the locked column assumes it never turns, so one clocking chosen at assembly serves the whole sweep.

| joint | part | required (deg) | at | required (locked) (deg) | locked clocking (deg) | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | - | - | 0.00 | 0.00 | - |
| LBJ | spherical | 8.84 | `06_steer_droop` step 64 | - | - | 0.00 | 8.56 | - |
| UBJ | spherical | 25.22 | `06_steer_droop` step 0 | - | - | 0.00 | 15.87 | - |
| Outer Tie Rod End | rod_end | 24.05 | `05_steer_bump` step 0 | 24.05 | 83.9 | 1.28 | 14.31 | - |
| Inner Tie Rod End | rod_end | 18.70 | `06_steer_droop` step 0 | 19.05 | 268.6 | 16.32 | 1.38 | - |
| Damper Lower Mount | spherical | 0.00 | `06_steer_droop` step 26 | 0.00 | 270.0 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `08_damper_stroke` step 1 | 0.00 | 270.0 | 0.00 | 0.00 | - |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/08_damper_stroke.png`
- `plots/09_steer_in_roll.png`
- `plots/10_corner_ramp.png`
