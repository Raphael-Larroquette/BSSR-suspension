# New model

A model is a folder in `Working/models/` holding `front.yaml`, `rear.yaml` and
`forces.yaml`. Nothing is registered; results are written inside the folder.

1. **Copy** an existing model (YAMLs only) and edit the hardpoints:
   `Working/models/aurora` → `Working/models/<name>`. Syntax: [`geometry.md`](../reference/geometry.md).
2. **Check** it (files present, geometry builds, forces solve):
   ```bash
   uv run python Working/check.py <name>
   uv run kinematics visualize --geometry Working/models/<name>/front.yaml --output front.png
   ```
   The second must report every wheel contact centre on the road plane; fix that before
   reading any characteristic.
3. **Forces**: set `vehicle.mass` in `forces.yaml`; run `--describe` for part and joint
   names ([`forces.md`](../reference/forces.md)).
4. **Run**: `uv run python Working/run_all.py --model <name>`.

New sweep set: copy `Working/sweep_sets/front/run.yaml` to a new folder, set `name`,
`geometry`, `reporter` (`susreport` axle, `susreport_rear` corner) and its `sweeps`
([`sweeps.md`](../reference/sweeps.md)).
