# Aurora front-axle kinematics workspace

```
../aurora/front.yaml   your geometry
run.yaml               WHAT RUNS AND WHAT IS REPORTED - start here
run_all.py             solve the set, render, build the report
sweeps/                target structure for each sweep
susreport.py           parser: CSVs -> characteristics, gradients, plots
../aurora/outputs/     raw solver CSVs (one per sweep) + animations
../aurora/report/      generated: summary.csv, report.md, joints.csv, plots/
RUNNING.md             run.yaml key reference, CLI overrides, precedence
SWEEPS.md              complete sweep-authoring grammar
CHARACTERISTICS.md     every characteristic the set produces, with caveats
```

## Run

```bash
uv run python models/Sweep_Set/run_all.py              # whatever run.yaml says
uv run python models/Sweep_Set/run_all.py --report-only  # rebuild without solving
uv run python models/Sweep_Set/run_all.py --dry-run      # show what would happen
```

Ranges, step counts, which sweeps run, which characteristics each one reports,
which get figures and which get animations are all set in **`run.yaml`**.
Command-line flags override it for one invocation. Full reference in
`RUNNING.md`.

## The sweeps

| # | File | Drives | Answers | Default |
| --- | --- | --- | --- | --- |
| 01 | `01_bump_parallel` | both wheels together | camber curve, bump steer, motion ratio, RC height vs ride | on |
| 02 | `02_roll` | equal and opposite | camber recovery, RC migration (height AND lateral), roll steer, track change | on |
| 03 | `03_single_wheel_bump` | left only | nothing 01 does not already give — see below | **off** |
| 04 | `04_steer_design` | rack lock to lock at design height | Ackermann, steering ratio, camber/caster/KPI vs steer, scrub and trail vs steer | on |
| 05 | `05_steer_bump` | same, in bump | diff against 04: how much steering geometry changes when loaded | on |
| 06 | `06_steer_droop` | same, in droop | the other end of that comparison | on |
| 07 | `07_bump_at_steer` | bump with the rack held off centre | the shape of the bump-steer curve while steered | **off** |
| 08 | `08_damper_stroke` | damper length | usable wheel travel for a given damper stroke; the honest motion ratio | on |
| 09 | `09_steer_in_roll` | rack lock to lock at a held roll attitude | mid-corner steering geometry; the only place Ackermann-in-roll is defined | on |
| 10 | `10_corner_ramp` | roll and steer ramping together | one line through corner entry | on |

**Why 03 is off.** Its left corner is numerically identical to 01 and its right
corner is held, so it never sets a bearing requirement and produces no
characteristic 01 does not. Every joint in this model is corner-local and the
only cross-axle coupling is the rack, which is centred in both sweeps. Turn it
on if the model ever gains an anti-roll bar or another element that couples the
corners.

**Why 07 is off.** It never sets a bearing requirement either — 04, 06 and 08
beat it at every joint. Its one unique output is the *shape* of the toe-vs-
travel curve while steered: bump steer is about −0.0004 deg/mm straight ahead
but ranges −0.037 to +0.031 deg/mm across lock, so a bump taken mid-corner
produces a toe input two orders of magnitude larger than the same bump in a
straight line. 04/05/06 only sample that at three ride heights. Turn 07 on when
you are specifically chasing bump steer.

Targets pair by index, never as a grid — that is why 04/05/06 are three files
rather than one 2-D sweep, and why 09 (held attitude) and 10 (ramp) are two
paths rather than one surface. See `SWEEPS.md` §5.
