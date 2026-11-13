# Rear corner characteristic report

## Solve status

| sweep | status | steps | where it stopped | reason |
| --- | --- | --- | --- | --- |
| `01_bump` | ok | 41/41 | - | - |
| `02_damper_stroke` | ok | 41/41 | - | - |

## Provenance

- geometry: `C:\Users\General\Desktop\BSSR-suspension\Working\models\aurora\rear.yaml`
- geometry SHA-256: `7e074efb00d45349...`
- format version: 3
- run configuration: `C:\Users\General\Desktop\BSSR-suspension\Working\models\aurora\report\rear\_resolved_run.json`

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump` | heave | 41 | True | 2.84e-13 | - |
| `02_damper_stroke` | damper_stroke | 41 | True | 3.98e-13 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |

## Notes

Conventions and formulas: `docs/reference/characteristics.md`. What is specific to a single-corner model:

- **This is one corner, not an axle.** Track, body roll, roll-centre height and lateral migration, Ackermann and rack displacement are all two-wheel constructions and are absent by definition, not by omission. On a three-wheel car the rear has no roll centre at all, so there is no roll axis and the front roll-centre height carries essentially the whole geometric lateral load transfer.
- **The wheel is on the vehicle centreline, so it has no inboard or outboard.** Camber, toe, caster, KPI, scrub radius, mechanical trail, half track and the front-view swing arm all measure against a lateral datum that a centreline wheel does not have, so the solver emits none of them: those columns are absent from the CSV rather than blank or signed by an arbitrary convention. Naming them in run.yaml will not bring them back.
- **The arm pivot is transverse, so the carrier does not tilt.** Both arm mounts share an X, the wheel swings in a plane, and the spin axis keeps its design orientation through the whole travel. Camber and toe change are what arm-axis obliquity in plan buys you, and this geometry deliberately has none.
- **The side-view family is the reason this model earns its own report.** A trailing arm's SVIC is its pivot axis, so SVSA, its angle and the anti percentages are all well defined here, unlike on the front. Anti-squat additionally needs the driven axle declared, and anti-lift needs `front_brake_bias`.
- **The anti percentages are reported at the design pose only.** Each is `(z_P/x_P) / (h/L)`, where `z_P` and `x_P` place the side-view instant centre relative to the tyre contact patch. The first ratio is pure suspension geometry and this model gets it right everywhere. The second is not: `h` is the CG height above the road, and a single-corner model puts the road plane through this wheel's own contact patch, so `h` falls by the full wheel travel as though the whole car were sinking on one corner. `L` meanwhile is held at the authored wheelbase. Both terms are exact at design and progressively wrong away from it, so min, max and range are left blank rather than printed as an envelope. A real anti-geometry envelope needs a whole-vehicle pitch and heave case, not a single-corner sweep.
- **Anti-squat depends on where the drive torque is reacted**, which the geometry declares as `drive_torque_reaction`. A hub motor (`unsprung`) reacts it through the arm, so the force line runs from the contact patch; an inboard motor through halfshafts (`sprung`) leaves only the longitudinal force at the wheel centre. The two differ by a tyre radius of leverage and can be hundreds of percent apart on the same geometry. The column is blank if the setting is absent, rather than guessing one.
- **The SVIC and SVSA length are tabulated but not plotted.** On a trailing arm the instant centre is the fixed pivot axis, so both plot as flat lines. SVSA angle carries the same information in a bounded form and is plotted instead.

## 01_bump  (heave)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Wheel travel | mm | 0.000 | -50.800 | 50.800 | 101.600 |
| Damper length | mm | 335.280 | 305.224 | 363.791 | 58.567 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7388 | 1.6401 | 1.8231 | 0.1831 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5751 | 0.5485 | 0.6097 | 0.0612 |
| Shock transmission angle (90 square, 0 toggle) | deg | 51.4549 | 47.6517 | 55.2410 | 7.5894 |
| Wheel-centre recession rate | mm/mm | 0.0000 | -0.1367 | 0.1367 | 0.2735 |
| SVIC longitudinal (x) | mm | -1865.000 | -1865.000 | -1865.000 | 0.000 |
| SVIC height (z) | mm | 278.500 | 278.500 | 278.500 | 0.000 |
| SVSA length | mm | 375.000 | 371.543 | 375.000 | 3.457 |
| SVSA angle | deg | 36.6000 | 31.5020 | 41.5507 | 10.0487 |
| Anti-squat | % | 475.31 | - | - | - |
| Anti-lift | % | 142.59 | - | - | - |

Plots: `plots/01_bump.png`

## 02_damper_stroke  (damper_stroke)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Damper length | mm | 335.280 | 305.280 | 365.280 | 60.000 |
| Wheel travel | mm | 0.000 | -53.519 | 50.708 | 104.227 |
| Motion ratio, instantaneous (wheel/damper) | mm/mm | 1.7388 | 1.6428 | 1.8252 | 0.1823 |
| Installation ratio, instantaneous (damper/wheel) | mm/mm | 0.5751 | 0.5479 | 0.6087 | 0.0608 |
| Shock transmission angle (90 square, 0 toggle) | deg | 51.4549 | 47.4463 | 55.2341 | 7.7878 |

Plots: `plots/02_damper_stroke.png`

## 01_bump: joint forces along travel

Constant case load, applied at the posed contact patch. |F| is the joint load (the same on both bodies it connects). Every component, including the chassis hardpoints, is in `01_bump_forces.csv`.

**Case 6,0,0** (bump, brake, corner in g)

| joint | side | at design [N] | peak [N] | peak at travel [mm] | peak / design |
| --- | --- | --- | --- | --- | --- |
| `strut_top` | centre | 9,027 | 9,465 | -50.8 | 1.05 |
| `strut_bottom` | centre | 9,027 | 9,465 | -50.8 | 1.05 |
| `trailing_arm_pivot_a` | centre | 6,944 | 7,281 | -50.8 | 1.05 |
| `trailing_arm_pivot_b` | centre | 4,000 | 4,175 | +50.8 | 1.04 |

Plot: `plots/01_bump_forces.png`

## Plots

- `plots/01_bump.png`
- `plots/02_damper_stroke.png`
- `plots/01_bump_forces.png`
