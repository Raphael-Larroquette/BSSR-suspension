# Rear corner characteristic report

## Solve status

| sweep | status | steps | where it stopped | reason |
| --- | --- | --- | --- | --- |
| `01_bump` | ok | 41/41 | - | - |
| `02_damper_stroke` | ok | 41/41 | - | - |

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\Test_Rear\Layout_3\rear.yaml`
- geometry SHA-256: `0d049207efb830f7...`
- format version: 3
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\Test_Rear\Layout_3\report\rear\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump` | heave | 41 | True | 2.66e-08 | - |
| `02_damper_stroke` | damper_stroke | 41 | True | 2.66e-08 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |

## Notes

Conventions and formulas: `docs/reference/characteristics.md`. What is specific to a single-corner model:

- **This is one corner, not an axle.** Track, body roll, roll-centre height and lateral migration, Ackermann and rack displacement are all two-wheel constructions and are absent by definition, not by omission. On a three-wheel car the rear has no roll centre at all, so there is no roll axis and the front roll-centre height carries essentially the whole geometric lateral load transfer.
- **The wheel is on the vehicle centreline, so it has no inboard or outboard.** Camber, toe, caster, KPI, scrub radius, mechanical trail, half track and the front-view swing arm all measure against a lateral datum that a centreline wheel does not have, so the solver emits none of them: those columns are absent from the CSV rather than blank or signed by an arbitrary convention. Naming them in run.yaml will not bring them back.
- **The arm pivot is transverse, so the carrier does not tilt.** Both arm mounts share an X, the wheel swings in a plane, and the spin axis keeps its design orientation through the whole travel. Camber and toe change are what arm-axis obliquity in plan buys you, and this geometry deliberately has none.
- **The side-view family is the reason this model earns its own report.** A trailing arm's SVIC is its pivot axis, so SVSA, its angle and the anti percentages are all well defined here, unlike on the front. Anti-squat additionally needs the driven axle declared, and anti-lift needs `front_brake_bias`.
- **The anti percentages are reported at the design pose only.** Each is `(z_P/x_P) / (h/L)`, where `z_P` and `x_P` place the side-view instant centre relative to the tyre contact patch. The first ratio is pure suspension geometry and this model gets it right everywhere. The second is not: `h` is the CG height above the road, and a single-corner model puts the road plane through this wheel's own contact patch, so `h` falls by the full wheel travel as though the whole car were sinking on one corner. `L` meanwhile is held at the authored wheelbase. Both terms are exact at design and progressively wrong away from it, so min, max and range are left blank rather than printed as an envelope. A real anti-geometry envelope needs a whole-vehicle pitch and heave case, not a single-corner sweep.
- **Anti-squat depends on where the drive torque is reacted**, which the geometry declares as `drive_torque_reaction`. A hub motor (`unsprung`) reacts it through the arm, so the force line runs from the contact patch; an inboard motor through halfshafts (`sprung`) leaves only the longitudinal force at the wheel centre. The two differ by a tyre radius of leverage and can be hundreds of percent apart on the same geometry. The column is blank if the setting is absent, rather than guessing one.
- **Rocker linkage.** Transmission angles are measured in the plane normal to the lever's pivot: 90 deg pushes square on the lever, 0 is toggle (no leverage; joint forces grow without bound). Watch the minimum over travel, not the design value. The rocker angle is relative to whatever carries the rocker (chassis or arm).
- **The SVIC and SVSA length are tabulated but not plotted.** On a trailing arm the instant centre is the fixed pivot axis, so both plot as flat lines. SVSA angle carries the same information in a bounded form and is plotted instead.

## 01_bump  (heave)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Wheel travel | mm | 0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 215.423 | 191.808 | 239.606 | 47.798 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 2.1251 | 2.0757 | 2.1807 | 0.1050 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.4706 | 0.4586 | 0.4818 | 0.0232 |
| Rod transmission angle (90 square, 0 toggle) | deg | 82.3003 | 73.3356 | 89.7900 | 16.4544 |
| Shock transmission angle (90 square, 0 toggle) | deg | 88.4458 | 87.7405 | 88.4458 | 0.7054 |
| Rocker angle, relative to its mount | deg | 0.0000 | -7.9092 | 7.4915 | 15.4007 |
| Wheel-centre recession rate | mm/mm | -0.0000 | -0.1367 | 0.1367 | 0.2735 |
| SVIC longitudinal (x) | mm | -1865.000 | -1865.000 | -1865.000 | 0.000 |
| SVIC height (z) | mm | 278.500 | 278.500 | 278.500 | 0.000 |
| SVSA length | mm | 375.000 | 371.543 | 375.000 | 3.457 |
| SVSA angle | deg | 36.6000 | 31.5020 | 41.5507 | 10.0487 |
| Anti-squat | % | 452.23 | - | - | - |
| Anti-lift | % | 135.67 | - | - | - |

Plots: `plots/01_bump.png`

## 02_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 215.423 | 185.423 | 245.423 | 60.000 |
| Wheel travel | mm | -0.000 | -62.837 | 64.787 | 127.624 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 2.1251 | 2.0643 | 2.1985 | 0.1342 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.4706 | 0.4549 | 0.4844 | 0.0296 |
| Rod transmission angle (90 square, 0 toggle) | deg | 82.3003 | 70.9090 | 89.8126 | 18.9036 |
| Shock transmission angle (90 square, 0 toggle) | deg | 88.4458 | 87.2684 | 88.4458 | 1.1774 |
| Rocker angle, relative to its mount | deg | 0.0000 | -9.8598 | 9.4921 | 19.3519 |

Plots: `plots/02_damper_stroke.png`

## 01_bump: joint forces along travel

Constant case load, applied at the posed contact patch. |F| is the joint load (the same on both bodies it connects). Every component, including the chassis hardpoints, is in `01_bump_forces.csv`.

**Case 6,0,0** (bump, brake, corner in g)

| joint | side | at design [N] | peak [N] | peak at travel [mm] | peak / design |
| --- | --- | --- | --- | --- | --- |
| `trailing_arm_pivot_a` | centre | 12,726 | 13,282 | -50.8 | 1.04 |
| `strut_top` | centre | 11,925 | 12,237 | +50.8 | 1.03 |
| `strut_bottom` | centre | 11,925 | 12,237 | +50.8 | 1.03 |
| `pushrod_outboard` | centre | 11,404 | 12,101 | +50.8 | 1.06 |
| `pushrod_inboard` | centre | 11,404 | 12,101 | +50.8 | 1.06 |
| `rocker_axis_b` | centre | 8,272 | 8,633 | -50.8 | 1.04 |
| `rocker_axis_a` | centre | 8,272 | 8,633 | -50.8 | 1.04 |
| `trailing_arm_pivot_b` | centre | 3,064 | 3,275 | +50.8 | 1.07 |

Plot: `plots/01_bump_forces.png`

## Plots

- `plots/01_bump.png`
- `plots/02_damper_stroke.png`
- `plots/01_bump_forces.png`
