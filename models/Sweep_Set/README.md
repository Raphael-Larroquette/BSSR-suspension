# Aurora front-axle kinematics workspace

```
front.yaml            your geometry
sweeps/               the eight-sweep SUSProg-parity set
outputs/              raw solver CSVs (one per sweep)
susreport.py          parser: CSVs -> characteristics, gradients, plots
report/               generated: summary.csv, report.md, plots/
SWEEPS.md             complete sweep-authoring grammar
CHARACTERISTICS.md    every characteristic the set produces, with caveats
run_all.sh            run everything
```

## Run

```bash
uv run python models/Sweep_Set/run_all.py        # all eight sweeps + report
uv run python susreport.py outputs/ --out report/ --side left
```

## The eight sweeps

| # | File | Drives | Answers |
| --- | --- | --- | --- |
| 01 | `01_bump_parallel` | both wheels together, ±63.5 mm | camber curve, bump steer, motion ratio, RC height vs ride, anti-dive |
| 02 | `02_roll` | equal and opposite, ±25 mm | camber recovery, RC migration (height AND lateral), roll steer, track change |
| 03 | `03_single_wheel_bump` | left only | the real one-wheel road input — neither pure heave nor pure roll |
| 04 | `04_steer_design` | rack ±35 mm at design height | Ackermann, steering ratio, camber/caster/KPI vs steer, scrub and trail vs steer |
| 05 | `05_steer_bump` | same, at +40 mm bump | diff against 04: how much steering geometry changes when loaded |
| 06 | `06_steer_droop` | same, at −40 mm droop | the other end of that comparison |
| 07 | `07_bump_at_steer` | bump ±63.5 with rack at +20 | bump steer mid-corner, which is not bump steer straight-ahead |
| 08 | `08_damper_stroke` | damper length ±30 mm | usable wheel travel for a given damper stroke |

Targets pair by index, never as a grid — that's why 04/05/06 are three files
rather than one 2-D sweep. See `SWEEPS.md` §5.
