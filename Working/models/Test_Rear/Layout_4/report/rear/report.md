# Rear corner characteristic report

## Solve status

| sweep | status | steps | where it stopped | reason |
| --- | --- | --- | --- | --- |
| `01_bump` | ok | 41/41 | - | - |
| `02_damper_stroke` | ok | 41/41 | - | - |

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\Test_Rear\Layout_4\rear.yaml`
- geometry SHA-256: `949f78fcbe2caf5a...`
- format version: 3
- run configuration: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\Working\models\Test_Rear\Layout_4\report\rear\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump` | heave | 41 | True | 3.08e-08 | - |
| `02_damper_stroke` | damper_stroke | 41 | True | 3.08e-08 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |

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
| Damper length | mm | 194.102 | 166.399 | 224.075 | 57.677 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7667 | 1.6202 | 1.9041 | 0.2839 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5660 | 0.5252 | 0.6172 | 0.0920 |
| Rod transmission angle (90 square, 0 toggle) | deg | 88.0105 | 73.3886 | 89.9424 | 16.5539 |
| Shock transmission angle (90 square, 0 toggle) | deg | 82.8517 | 77.3954 | 89.9626 | 12.5672 |
| Rocker angle, relative to its mount | deg | 0.0000 | -1.8412 | 0.0376 | 1.8789 |
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
| Damper length | mm | 194.102 | 164.102 | 224.102 | 60.000 |
| Wheel travel | mm | -0.000 | -50.843 | 55.188 | 106.031 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7667 | 1.6240 | 1.9127 | 0.2887 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5660 | 0.5228 | 0.6158 | 0.0929 |
| Rod transmission angle (90 square, 0 toggle) | deg | 88.0105 | 73.3747 | 89.9633 | 16.5886 |
| Shock transmission angle (90 square, 0 toggle) | deg | 82.8517 | 77.0247 | 89.9374 | 12.9127 |
| Rocker angle, relative to its mount | deg | 0.0000 | -1.8441 | 0.0379 | 1.8820 |

Plots: `plots/02_damper_stroke.png`

## 01_bump: joint forces along travel

Constant case load, applied at the posed contact patch. |F| is the joint load (the same on both bodies it connects). Every component, including the chassis hardpoints, is in `01_bump_forces.csv`.

**Case 6,0,0** (bump, brake, corner in g)

| joint | side | at design [N] | peak [N] | peak at travel [mm] | peak / design |
| --- | --- | --- | --- | --- | --- |
| `trailing_arm_pivot_a` | centre | 10,515 | 10,855 | +50.8 | 1.03 |
| `strut_top` | centre | 9,914 | 10,685 | +50.8 | 1.08 |
| `strut_bottom` | centre | 9,914 | 10,685 | +50.8 | 1.08 |
| `pushrod_outboard` | centre | 7,070 | 7,602 | +50.8 | 1.08 |
| `pushrod_inboard` | centre | 7,070 | 7,602 | +50.8 | 1.08 |
| `rocker_axis_b` | centre | 6,835 | 7,056 | +50.8 | 1.03 |
| `rocker_axis_a` | centre | 6,835 | 7,056 | +50.8 | 1.03 |
| `trailing_arm_pivot_b` | centre | 2,458 | 2,538 | -50.8 | 1.03 |

Plot: `plots/01_bump_forces.png`

## Plots

- `plots/01_bump.png`
- `plots/02_damper_stroke.png`
- `plots/01_bump_forces.png`
