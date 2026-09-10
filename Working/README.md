# Working

Everything that describes a *car* rather than the solver: geometry, the sweep
sets run against it, and the force configurations. Three siblings, because a
car's hardpoints are shared by both workflows and should exist once.

```
Working/
  models/        the cars: hardpoints, vehicle configuration, joint declarations
    aurora/        front.yaml  rear.yaml
  sweep_sets/    kinematic sweeps and their reports  -> RUNNING.md
    front/  rear/
  forces/        static joint-force solves           -> force.md
    aurora/        forces.yaml  cases.csv
```

A sweep set and a force configuration both name their geometry **relative to
themselves**, so pointing either at a different car is an edit to one line, and
adding a car is a new folder rather than a change to an existing one.

Results are written beside the thing they came from — `models/<car>/outputs/`
for sweeps, `forces/<car>/outputs/` for force runs — and are git-ignored, since
all of it is reproducible from the inputs.

| I want to | Start at |
| --- | --- |
| Change a hardpoint | `models/<car>/front.yaml` |
| Run the kinematic sweeps and build a report | `sweep_sets/RUNNING.md` |
| Understand what a characteristic means | `sweep_sets/CHARACTERISTICS.md` |
| Solve joint forces for FEA | `forces/force.md` |
| Add a load case | `forces/<car>/cases.csv` |
