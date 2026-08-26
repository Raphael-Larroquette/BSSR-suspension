# Writing sweeps — the complete grammar

Source of truth: `src/kinematics/core/schema/sweep.py` (the Pydantic models) and
`src/kinematics/core/targeting.py` (the coordinate resolution). Everything
below is read off those two files, not the README.

---

## 1. The mental model

A sweep is **not** a list of positions. It is a list of *constraints you add to
the solver*, one per degree of freedom, evaluated at N steps.

At every step the solver builds

```
r(q) = [ constraint residuals ; measured coordinate − commanded value ]
```

and drives it to zero. A sweep target contributes exactly one row to the
bottom block. That is the whole idea — everything else follows from it.

Three consequences worth holding onto:

1. **You supply exactly one target per DOF, every step.** Too few and the pose
   is underdetermined; too many and it's overdetermined. Both are rejected.
2. **Targets are commands, not measurements.** The `target_*` columns in the
   output are the *measured* values afterwards, which is why they carry ~1e-6
   of solver noise even for a target you pinned to a constant.
3. **You can drive any measurable coordinate**, not just the wheel. Damper
   length is a legal input; the solver will find the wheel position that
   produces it.

---

## 2. File structure

```yaml
version: 1          # must be 1; anything else is rejected
steps: 65           # optional; only needed if any target uses start/stop
targets:            # at least one; this is the whole sweep
  - ...
```

`steps` is file-level and shared. Omit it only if **every** target supplies an
explicit `values:` list.

---

## 3. The three target types

Discriminated on `type`. Each is a separate Pydantic model with
`extra="forbid"`, so a misspelled key is a hard error.

### 3.1 `point` — drive a point coordinate

```yaml
- type: point
  point: wheel_center          # any PointID, lowercased
  side: left                   # required for corner-owned points on an axle
  direction: {axis: z}         # or {vector: [0, 0.3, 1]}
  mode: relative               # relative | absolute
  start: -63.5
  stop: 63.5
  name: "left heave"           # optional label, appears in error messages
```

Measures the **projection of that point's position onto `direction`** and
drives it to the commanded value. `wheel_center` along `z` is heave;
`wheel_center` along `x` would be longitudinal; `lower_wishbone_outboard`
along `z` is a perfectly legal (if unusual) way to drive the same mechanism.

`wheel_contact_centre` is an output of the ground closure and **cannot** be
targeted — the error message will point you at `wheel_center` instead.

### 3.2 `actuator_position` — drive a topology-declared actuator

```yaml
- type: actuator_position
  actuator: rack               # only legal value today
  direction: {axis: y}
  mode: relative
  start: -35
  stop: 35
```

The legal set is `ACTUATOR_POSITION_TARGET_IDS = ['rack']`.

A rack is **shared** across the axle — one lateral DOF, no `side`. This is not
the same as targeting `trackrod_inboard` as a point: the actuator coordinate
is the topology's declared steering input and drives both track rods together.
A point target on `trackrod_inboard` will not satisfy the actuator
requirement, and you'll get:

```
Sweep requires exactly one target for actuator 'steering rack' along its
motion axis; found 0 at step 0.
```

### 3.3 `element_length` — drive a link length

```yaml
- type: element_length
  element: damper              # damper | heave_link
  side: left
  mode: relative
  start: -30
  stop: 30
```

`ELEMENT_LENGTH_TARGET_IDS = ['damper', 'heave_link']`. Note there is **no
`direction`** — a length is already scalar.

This inverts the usual question. Instead of "command the wheel, read the
damper", it's "command the damper, read the wheel" — which is how you sweep to
the real bump-stop and droop-stop limits set by damper hardware rather than by
a number you guessed.

**The catch, measured:** the analytic `deriv_*_wrt_hub_z` columns only exist
when a `hub_z` target is present. Drive by damper length and you lose the
analytic motion ratio, camber gain, and bump-steer rate — 22 columns go all-NaN
on your geometry. Use `element_length` to find travel limits, then run a normal
heave sweep between those limits to get the gradients.

---

## 4. Fields shared by all three

From `SweepValueSpec`:

| Field | Meaning |
| --- | --- |
| `mode` | `relative` (default) = offset from the authored design condition. `absolute` = raw chassis-space coordinate (or absolute length for `element_length`). |
| `start` / `stop` | Endpoints; expanded with `np.linspace(start, stop, steps)`. Both required if `values` is absent. |
| `values` | Explicit list. Overrides `start`/`stop` and makes `steps` unnecessary. |
| `side` | `left` or `right`. **`center` is explicitly rejected.** Required for corner-owned coordinates on an axle; omit for shared ones like `rack`. |
| `name` | Cosmetic label used in validation errors. |

### `direction` (point and actuator targets only)

```yaml
direction: {axis: z}                 # principal axis
direction: {vector: [0, 0.259, 0.966]}   # arbitrary, auto-normalised
```

Exactly one of `axis` or `vector` — supplying both or neither is rejected. The
vector form is the escape hatch for driving along a non-principal direction,
e.g. straight up the kingpin axis. A zero vector is rejected.

---

## 5. The rule that catches everyone

**All target sequences must be the same length, and they pair BY INDEX.**

```yaml
targets:
  - {..., values: [-30, 0, 30]}
  - {..., values: [30, 0, -30]}
```

is three steps: `(-30, +30)`, `(0, 0)`, `(+30, -30)`. It is **not** a 3×3 grid.

There is no Cartesian product anywhere in this tool. A bump-steer *surface*
(toe as a function of both travel and steer) needs one run per steer angle,
stitched afterwards. That's why the sweep set below has three separate steer
files rather than one 2-D sweep.

---

## 6. Counting degrees of freedom

Don't reason about it — provoke it. Delete a target and run; the error names
what's missing and on which side. For your axle:

| Sweep | Targets |
| --- | --- |
| Any double-wishbone axle with a rack | left wheel Z, right wheel Z, rack Y = **3** |
| Same, but driving dampers | left damper length, right damper length, rack Y = **3** |
| Standalone corner with a rack | wheel Z, rack Y = **2** |

Adding an ARB or heave link changes this. Provoke it again rather than
guessing.

---

## 7. Errors, decoded

| Message | Cause |
| --- | --- |
| `Invalid PointID: 'wheel_centre'` | Spelling. The message lists every legal name — it's your autocomplete. |
| `Sweep requires exactly one target for actuator 'steering rack'...` | DOF mismatch, usually a forgotten rack target. |
| `Axle sweep target for 'WHEEL_CENTER' requires side left or right` | Missing `side:` on a corner-owned target. |
| `All targets must have the same length, got: [41, 65]` | Mixed `values:` lengths, or one target using `values` while another relies on a different `steps`. |
| `Specify exactly one of 'axis' or 'vector'` | Both or neither given in `direction`. |
| `Target '...': no 'steps' count available` | Used `start`/`stop` with no file-level `steps`. |
| `Unknown element-length target ID 'spring'` | Only `damper` and `heave_link` exist. |

---

## 8. Discovering what YOUR geometry can be driven by

Don't guess the legal `actuator` and `element` IDs — ask:

```python
import yaml
from pathlib import Path
from kinematics.core.input import build_suspension
from kinematics.core.analysis import initial_pose

s = build_suspension(yaml.safe_load(Path("models/aurora/front.yaml").read_text()))
for dc in initial_pose(s).drive_coordinates:
    print(dc.id, dc.type, dc.scope, dc.side, dc.unit)
```

On your current front.yaml that prints:

```
rack     actuator_position   axle     None    mm
damper   element_length      corner   left    mm
damper   element_length      corner   right   mm
```

Add an ARB or a heave link and re-run it — the list grows, and so does your
target count.
