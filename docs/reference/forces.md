# Static force solve

Force at every joint, per load case, at neutral ride height (no steer, roll, pitch;
springs and dampers rigid). Front and rear solve together.

```bash
uv run python Working/run_all.py --no-sweeps
uv run kinematics forces --config Working/models/<model>/forces.yaml --cases Working/cases.csv [flags]
```

| flag | |
| --- | --- |
| `--front` / `--rear` / `--cases` / `--mass` | override inputs |
| `--out PATH` | `.csv` or `.xlsx` |
| `--per-part-files DIR` | one flat CSV per part |
| `--describe` | parts, joints, coaxial pairs, system size; run first on a new model |
| `--check` | per-part equilibrium residuals |
| `--dry-run` | solve, write nothing |

## `cases.csv`

Shared by every model: `Working/cases.csv`. `#` lines ignored. Columns in g:

| | |
| --- | --- |
| `bump` | total vertical factor incl. gravity; `1` = static; > 0 |
| `brake` | `+1` = 1 g deceleration (load forward); negative = traction |
| `corner` | `+1` = CG inertial force toward +Y (left), i.e. a right turn |

## `forces.yaml`

All keys required except `cases` (supplied by `--cases`). Paths relative to the file.

| key | values |
| --- | --- |
| `vehicle.mass`, `vehicle.g` | kg, m/s² (point mass at `cg_position`) |
| `geometry.front` / `.rear` | paths |
| `cases` | optional path |
| `solve.moment_reference` | `centroid` \| `origin` \| `{x,y,z}` (equivalent; centroid best conditioned) |
| `solve.pivot_axial.default` / `.overrides` | `even` \| point name taking all axial load; overrides by part name |
| `solve.rack` | `grounded` |
| `solve.brake_torque_reaction` | `unsprung` (outboard brake) |
| `solve.on_wheel_lift` | `report` \| `fail` |
| `solve.tolerances.rank` / `.residual` | float |
| `structure.weld` | groups merged into one part; first entry names it and must exist |
| `structure.attach` | `{point, anchors}`: fold a loose point into the part carrying the anchors |
| `structure.ground` / `.ignore` | body names merged into the chassis / dropped |
| `output.frame` | `vehicle` (ISO 8855) \| `part` (right-side parts Y-mirrored) |
| `output.moments` | `auto` \| `always` \| `never` |
| `output.per_part_files` | bool |
| `output.chassis` | bool, default `true`: append the chassis blocks |

## How it solves

1. **Normal loads**: three contact patches are statically determinate (ΣFz, ΣMx, ΣMy).
   Four patches are refused (needs roll stiffness).
2. **Horizontal loads**: proportional to normal load (one μ, ideal brake bias).
3. **Body graph**: kinematic bodies → `structure` policy → joints where two parts share a
   point. Delete ground, connected components = independent corners (an ARB would merge
   them). A part with two joints and no external load is a two-force member.
4. **Per corner**: 6 equations per part, checked square and full rank, never
   least-squares. Coaxial pivot pairs are closed by `pivot_axial`.

Negative normal load: `WHEEL_LIFT` flag. Other corners stay valid (conservative); the
flagged corner's numbers are not physical.

## Output (`<model>/forces/`)

`forces.csv`: one block per part, then one **chassis** block per axle.

```
PART:,Lower Wishbone
Case,,,,lower_wishbone_inboard_front,,,,...,flags
bump,brake,corner,side,x,y,z,mag,...
```

- Part blocks: force **on the named part at that joint**. The wheel-carrying part has a
  `wheel_contact_centre (applied)` group; every part block sums to zero.
- `Front Chassis` / `Rear Chassis`: force **on the chassis** at every chassis hardpoint
  (negative of the part-side load). Do not sum to zero. Never mirrored by `frame: part`.
  The grounded rack counts as chassis: `trackrod_inboard` is the tie-rod load into the
  rack, not the rack mount loads.
- No moment columns today: every joint is force-only.

`load_transfer.csv`: per wheel per case: `normal_load_N`, `effective_mass_kg`,
`percent_of_case` (sums to 100), `percent_of_static_weight` (sums to 100 × bump),
`transfer_from_baseline_N` (vs the same case with brake and corner zeroed).

## Not modelled

| | |
| --- | --- |
| four contact patches | refused |
| inboard brakes (`sprung`), floating rack | error |
| ARB / heave link forces | no torsional model |
| `front_brake_bias`, `driven_axle` | ignored |
| joint moments, compliance, dynamics, aero | none |
| rack mount loads, hub bearing loads, caliper loads | not resolved |
