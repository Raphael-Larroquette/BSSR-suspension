# Sweep files

> **You do not normally write one.** A sweep's targets are generated from its `travel` /
> `damper` / `rack` keys in `run.yaml` — start at [`RUNNING.md`](RUNNING.md). This page is
> the grammar, which you need for two things: reading a generated file in
> `_resolved_sweeps/`, and hand-writing a sweep the vocabulary cannot express and naming
> it with `file:`.

The vocabulary cannot express `mode: absolute`, an explicit `values:` list (non-linear
spacing), a point driven along a non-principal direction, or any drive coordinate other
than the wheel centre, the damper and the rack. Those need a `file:` sweep, which is used
verbatim — `run.yaml` overrides nothing in it. The fastest start is to copy a generated
file out of `outputs/<set>/_resolved_sweeps/` and edit it.

Source of truth: `src/kinematics/core/schema/sweep.py` and
`src/kinematics/core/targeting.py`. Declaring bearing joints is in
`../models/MODELS.md` §5.

1. [The mental model](#1-the-mental-model)
2. [File structure](#2-file-structure)
3. [The three target types](#3-the-three-target-types)
4. [Shared fields](#4-shared-fields)
5. [Targets pair by index](#5-targets-pair-by-index)
6. [Counting degrees of freedom](#6-counting-degrees-of-freedom)
7. [Errors](#7-errors)
8. [Discovering what your geometry exposes](#8-discovering-what-your-geometry-exposes)
9. [The Aurora sweep catalogue](#9-the-aurora-sweep-catalogue)

---

## 1. The mental model

A sweep is not a list of positions. It is a list of **constraints added to the solver**,
one per degree of freedom, evaluated at N steps. At each step the solver drives

```
r(q) = [ constraint residuals ; measured coordinate − commanded value ]
```

to zero. Each target contributes one row to the bottom block. Consequences:

1. **Exactly one target per DOF, every step.** Too few is underdetermined, too many
   overdetermined; both are rejected.
2. **Targets are commands, not measurements.** The `target_*` output columns are the
   measured values afterwards, so they carry ~1e-6 of solver noise even for a constant.
3. **Any measurable coordinate can be driven**, not just the wheel.

---

## 2. File structure

```yaml
version: 1          # must be 1
steps: 65           # file-level; only needed if any target uses start/stop
targets:            # at least one
  - ...
```

Omit `steps` only if **every** target supplies an explicit `values:` list.

---

## 3. The three target types

Discriminated on `type`, each `extra="forbid"` — a misspelt key is a hard error.

### `point` — drive a point coordinate

```yaml
- type: point
  point: wheel_center          # any PointID, lowercased
  side: left                   # required for corner-owned points on an axle
  direction: {axis: z}         # or {vector: [0, 0.3, 1]}
  mode: relative               # relative | absolute
  start: -55
  stop: 50
  name: "left heave"           # optional label, appears in error messages
```

Measures the projection of the point's position onto `direction` and drives it to the
commanded value. `wheel_contact_centre` **cannot** be targeted — use `wheel_center`.

### `actuator_position` — drive a topology-declared actuator

```yaml
- type: actuator_position
  actuator: rack               # only legal value today
  direction: {axis: y}
  mode: relative
  start: -35
  stop: 35
```

A rack is **shared** across the axle — one lateral DOF, no `side`. Targeting
`trackrod_inboard` as a point does **not** satisfy it; you get
`Sweep requires exactly one target for actuator 'steering rack'...`.

### `element_length` — drive a link length

```yaml
- type: element_length
  element: damper              # damper | heave_link
  side: left
  mode: relative
  start: -30
  stop: 30
```

No `direction` — a length is scalar. This commands the damper and reads the wheel, which
is how you find travel limits set by real damper hardware.

**The catch:** the analytic `deriv_*_wrt_hub_z` columns exist only when a `hub_z` target
is present. Drive by damper length and 22 columns go all-NaN — no analytic motion ratio,
camber gain or bump-steer rate. Use `element_length` to find the limits, then run a normal
heave sweep between them for the gradients.

---

## 4. Shared fields

| Field | Meaning |
| --- | --- |
| `mode` | `relative` (default) = offset from the authored design condition. `absolute` = raw chassis-space coordinate (or absolute length) |
| `start` / `stop` | endpoints, expanded with `np.linspace(start, stop, steps)`. Both required if `values` is absent |
| `values` | explicit list; overrides `start`/`stop` and makes `steps` unnecessary |
| `side` | `left` / `right` on an axle (required for corner-owned coordinates); `center` for a centreline corner. Omit for shared coordinates like `rack` |
| `name` | cosmetic label used in validation errors |

`direction` (point and actuator targets only) takes exactly one of `axis` or `vector`:

```yaml
direction: {axis: z}
direction: {vector: [0, 0.259, 0.966]}   # auto-normalised; zero vector rejected
```

---

## 5. Targets pair by index

**All target sequences must be the same length, and they pair by index.**

```yaml
targets:
  - {..., values: [-30, 0, 30]}
  - {..., values: [30, 0, -30]}
```

is three steps — `(-30, +30)`, `(0, 0)`, `(+30, -30)` — **not** a 3×3 grid. There is no
Cartesian product anywhere in this tool. A bump-steer *surface* needs one run per steer
angle, stitched afterwards; that is why 04/05/06 are three files.

Two useful path shapes fall out:

- **Hold an attitude and sweep one thing.** Constant `start`/`stop` on the wheel-centre
  targets pins the axle while another target sweeps. 05/06 do this with heave, 09 with
  roll. In `run.yaml` that is `travel: {left: [-25, -25], right: [25, 25]}`.
- **Ramp several things together.** Different start and stop on every target traces a
  diagonal — 10 ramps roll and rack together.

---

## 6. Counting degrees of freedom

Don't reason about it — delete a target and run; the error names what's missing and on
which side.

| Sweep | Targets |
| --- | --- |
| Double-wishbone axle with a rack | left wheel Z, right wheel Z, rack Y = **3** |
| Same, driving dampers | left damper length, right damper length, rack Y = **3** |
| Standalone corner with a rack | wheel Z, rack Y = **2** |
| Centreline trailing-arm corner | wheel Z = **1** |

Adding an ARB or heave link changes this.

---

## 7. Errors

| Message | Cause |
| --- | --- |
| `Invalid PointID: 'wheel_centre'` | spelling — the message lists every legal name |
| `Sweep requires exactly one target for actuator 'steering rack'...` | DOF mismatch, usually a forgotten rack target |
| `Axle sweep target for 'WHEEL_CENTER' requires side left or right` | missing `side:` on a corner-owned target |
| `All targets must have the same length, got: [41, 65]` | mixed `values:` lengths, or one target using `values` while another relies on `steps` |
| `Specify exactly one of 'axis' or 'vector'` | both or neither given in `direction` |
| `Target '...': no 'steps' count available` | `start`/`stop` with no file-level `steps` |
| `Unknown element-length target ID 'spring'` | only `damper` and `heave_link` exist |

---

## 8. Discovering what your geometry exposes

**Drive coordinates** — the legal `actuator` and `element` IDs:

```python
import yaml
from pathlib import Path
from kinematics.core.input import build_suspension
from kinematics.core.analysis import initial_pose

s = build_suspension(yaml.safe_load(Path("Working/models/aurora/front.yaml").read_text()))
for dc in initial_pose(s).drive_coordinates:
    print(dc.id, dc.type, dc.scope, dc.side, dc.unit)
```

On Aurora's front: `rack` (actuator_position, axle) and `damper` (element_length, corner,
left and right).

**Bodies and joint points** — the `part` names for a `joints:` block, and which points
already have exactly two bodies:

```python
import yaml
from pathlib import Path
from kinematics.core.input import build_suspension
from kinematics.core.bodies import build_bodies, resolve_body_modes

s = build_suspension(yaml.safe_load(Path("Working/models/aurora/front.yaml").read_text()))
corner = s.corners[min(s.corners)] if s.is_axle else s
neutral = corner.initial_state().positions
asm = corner.assembly()
bodies = resolve_body_modes(
    build_bodies(asm.elements, asm.points.fixed, corner.rigid_attachments()), neutral
)
for b in bodies:
    print(f"{b.name:16s} {b.mode.value:10s} {', '.join(p.name.lower() for p in b.points)}")
for point in sorted({p for b in bodies for p in b.points}, key=lambda p: p.name):
    owners = [b.name for b in bodies if point in b.points]
    if len(owners) == 2:
        print(f"{point.name.lower():30s} {owners[0]} <-> {owners[1]}")
```

On Aurora's front the bodies are Upper Wishbone, Lower Wishbone, Upright, Axle, Wheel,
Track Rod, Spring/Damper and Chassis. The second list is the set of joints you can declare
without naming `part`; `trackrod_inboard` is absent from it because the rack is axle-level
hardware, so that one joint needs an explicit `part`.

The `mode` column is how each body's rotation is recovered, chosen from point count alone:

- `ground` — never rotates
- `fitted` — determined by three or more non-collinear points
- `transport` — a two-point member whose spin is undetermined. **Only these may have a
  housing declared `indeterminate`.**

Rigid-body membership is declared, never inferred: two links sharing an endpoint is a
joint in general, not a weld. If a weldment shows up as separate bodies, tag them with the
same `body_group=` in the topology's `elements()`.

---

## 9. The Aurora sweep catalogue

All of these are defined in each set's `run.yaml`, not in files.

### Front — `sweep_sets/front/run.yaml`

| # | Sweep | Drives | Answers | Default |
| --- | --- | --- | --- | --- |
| 01 | `01_bump_parallel` | both wheels together | camber curve, bump steer, motion ratio, RC height vs ride | on |
| 02 | `02_roll` | equal and opposite | camber recovery, RC migration (height and lateral), roll steer, track change | on |
| 03 | `03_single_wheel_bump` | left only | nothing 01 does not already give | **off** |
| 04 | `04_steer_design` | rack lock to lock at design height | Ackermann, steering ratio, camber/caster/KPI vs steer, scrub and trail vs steer | on |
| 05 | `05_steer_bump` | the same, in bump | how much steering geometry changes when loaded | on |
| 06 | `06_steer_droop` | the same, in droop | the other end of that comparison | on |
| 07 | `07_bump_at_steer` | bump with the rack held off centre | the shape of the bump-steer curve while steered | **off** |
| 08 | `08_damper_stroke` | damper length | usable wheel travel for a given damper stroke; the honest motion ratio | on |
| 09 | `09_steer_in_roll` | rack lock to lock at a held roll attitude | mid-corner steering geometry; the only place Ackermann-in-roll is defined | on |
| 10 | `10_corner_ramp` | roll and steer ramping together | one line through corner entry | on |

**Why 03 is off.** Its left corner is numerically identical to 01 and its right corner is
held, so it sets no bearing requirement and produces nothing new. Every joint in this
model is corner-local and the only cross-axle coupling is the rack, centred in both
sweeps. Turn it on if the model gains an anti-roll bar or another coupling element.

**Why 07 is off.** It also sets no bearing requirement (04, 06 and 08 beat it everywhere).
Its one unique output is the *shape* of the toe-vs-travel curve while steered: bump steer
is ≈ −0.0004 deg/mm straight ahead but ranges −0.037 to +0.031 deg/mm across lock. Turn it
on when specifically chasing bump steer.

**Sweep 09 caveat.** Roll is held one way while the rack sweeps both, so only half of it
is a real cornering state; the other half is rolled one way and steered the other. On
Aurora that reads as ≈110% Ackermann turning into the roll and negative (anti-Ackermann)
turning out of it. For the physical half only, set `rack: [0, 35]` to match the roll sign.

### Rear — `sweep_sets/rear/run.yaml`

Aurora's rear is a single centreline trailing-arm corner with **one degree of freedom**,
so each sweep has exactly one target. Roll, Ackermann and steer sweeps have no meaning on
one wheel; the set is small on purpose.

| # | Sweep | Drives | Answers |
| --- | --- | --- | --- |
| 01 | `01_bump` | wheel centre | camber/toe curves, motion ratio, recession, the side-view family |
| 02 | `02_damper_stroke` | damper length | usable wheel travel; the honest motion ratio |

The side-view family is why the rear gets its own reporter: a trailing arm's side-view
instant centre **is its pivot axis**, so SVIC, SVSA, SVSA angle and anti-squat are all
defined. On the front they are undefined — its wishbone axes are exactly parallel in side
view.
