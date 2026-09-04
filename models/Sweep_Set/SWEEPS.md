# Writing sweeps — the complete grammar

Source of truth: `src/kinematics/core/schema/sweep.py` (the Pydantic models) and
`src/kinematics/core/targeting.py` (the coordinate resolution). Everything
below is read off those two files, not the README.

Sections 1-8 are the sweep file. Section 9 is the `joints:` block, which lives
in the *geometry* file but is documented here because this is where authoring
grammar belongs; what its numbers mean is §G of `CHARACTERISTICS.md`.

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

### Pairing by index is a feature, not only a limit

Because the targets pair by index, a sweep is a **path** through the state
space, and you get to choose the path. Two useful shapes fall out:

- **Hold an attitude and sweep one thing.** Constant `start`/`stop` on the two
  wheel-centre targets pins the axle at that attitude while another target
  sweeps. `05`/`06` do this with heave; `09_steer_in_roll` does it with roll —
  left wheel held at −25 mm, right at +25 mm, rack swept lock to lock. That is
  the mid-corner steering geometry, and the only place Ackermann is defined at
  a rolled attitude.

- **Ramp several things together.** Give every target a different start and
  stop and they interpolate in step, tracing a diagonal.
  `10_corner_ramp` ramps roll from 0 to full and the rack from centre to full
  lock at the same time, which is roughly the path a real corner entry takes.

Between a held attitude and a ramp you bracket the coupled behaviour without
needing the surface. When you do eventually want the surface, the honest way is
to generate one file per attitude from `run.yaml` and stitch the CSVs — not to
try to express it in one file.

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

---

## 9. Declaring joints for misalignment (geometry file, not sweep file)

The one block in this document that does **not** go in a sweep file. `joints:`
is top-level in the *geometry* file, next to `hardpoints:`, because a joint is
a fact about the mechanism rather than about one run. It is here because this
is where the authoring grammar lives; what the resulting numbers mean is
§G of `CHARACTERISTICS.md`.

Source of truth: `src/kinematics/core/schema/joints.py` (the Pydantic models)
and `src/kinematics/core/joints.py` (the resolution and the geometry).

### 9.1 The mental model

Two rigid bodies meet at a point. Two unit directions matter, and **each is
fixed to a different body**:

- **bore** — the bolt / ball bore axis
- **housing** — the bearing housing's centred direction

The angle the bearing must absorb is the angle between them once both bodies
have rotated:

```
theta(t) = angle( n_housing , Q(t) · n_bore )      Q(t) = R_housing(t)^T · R_bore(t)
```

`Q(t)` is what the sweep exports, and it depends on **neither** direction.
Three consequences worth holding onto:

1. **Choosing bearing axes never re-runs a sweep.** Authoring an axis,
   optimising it, or asking what the best available one would be are all
   answered by `susreport.py` from the CSVs.
2. **The two directions need not coincide at the neutral pose.** When they
   don't, the bearing is installed deliberately off centre; the report calls
   that the install offset. This is a design move — pre-tilting a housing to
   the middle of a one-sided excursion roughly halves the required rating —
   and it is also how an assembly error shows itself.
3. **Only declared joints produce anything.** An undeclared point gets no
   columns, no report entry, and no body lookup.

### 9.2 Block structure

```yaml
joints:
  upper_wishbone_outboard:        # the point the joint sits at
    label: "UBJ"                  # optional; defaults to the key
    type: spherical               # bushing | spherical | rod_end
    bore:
      part: upright
      axis: {from: lower_wishbone_outboard, to: upper_wishbone_outboard}
    housing:                      # omit entirely to install centred
      part: upper_wishbone
```

Declared once and applied to both sides of an axle, the same way `hardpoints`
mirrors.

### 9.3 `type` carries no physics

`bushing | spherical | rod_end` selects **report vocabulary and defaults
only** — a bushing's angle is called conical deflection, the others'
misalignment. It deliberately does not constrain anything, because the same
part behaves differently depending on what it is mounted to. A rod end
threaded into a wishbone has a fully determined housing; the identical rod end
on a two-point track rod does not. That difference is stated by `housing:`,
not by the part name.

### 9.4 Fields on `bore` and `housing`

| Field | Meaning |
| --- | --- |
| `part` | Which body the direction is fixed to. A body name, or `{points: [...]}` to declare one inline. Optional when exactly two bodies meet at the point. |
| `axis` | A direction (see 9.5), or one of the keywords in 9.6. |
| `perpendicular_to` | The direction is perpendicular to this axis. Narrows an optimised search to a clocking circle. |
| `in_plane` | The direction lies in this plane: `{normal: <axis>}` or `{points: [a, b, c]}`. Same kind of fact as `perpendicular_to`; giving both pins the direction up to sign. |
| `cone_deg` | Half-angle between the direction and the axis of the body carrying it, used when that body's spin is undetermined. Defaults to 90 — a rod end, whose bore is perpendicular to its shank. |

### 9.5 The four axis spellings

All four resolve at the **neutral pose, in chassis coordinates**:

```yaml
axis: {from: lower_wishbone_outboard, to: upper_wishbone_outboard}   # kingpin
axis: {vector: [0, 0.26, 0.97]}                                      # normalised for you
axis: {x: 0, y: 0.26, z: 0.97}                                       # same, componentwise
axis: {chassis_axis: z}                                              # principal axis
```

Exactly one spelling per axis; mixing them is rejected. **Reach for the
two-point form.** It names the kingpin axis, a wishbone pivot axis, a link's
own axis or a rocker axis without hard-coding numbers that go stale the moment
a hardpoint moves.

### 9.6 The three keywords

A string value of `axis:` is a keyword, never a direction — that is why
directions are always mappings.

| Keyword | Legal on | Meaning |
| --- | --- | --- |
| `optimize` | `bore` | Leave the direction for the report to solve, minimising the worst case over the whole sweep set. No `misalign_*` column is written, since no per-step angle exists until an axis is chosen. |
| `centred` | `housing` | Pin the housing to the authored bore axis. This is the default when `housing:` is omitted, and it means the bearing starts square in its cone. |
| `indeterminate` | `housing` | The housing rides a two-point member whose roll about its own axis nothing determines. |

**`indeterminate` is the one that needs thinking about.** A member with
spherical joints at both ends carries no axial torque, so its spin is
genuinely unknowable — the solver neither knows nor can know it. Declaring it
reports the *lower* bound, which assumes the member turns freely to the most
favourable position at every instant. The report pairs that with the locked
value, which assumes it never turns and one clocking chosen at assembly serves
the whole sweep. **Size against the locked value** unless you know the member
runs free.

Optimising the housing is not implemented; the error says so.

### 9.7 Worked declarations

A bushing on a wishbone pivot — bore on the pivot axis, housing centred. This
reads exactly zero forever, because the arm rotates about that axis and
nothing else, which makes it a free check on your hardpoints:

```yaml
  lower_wishbone_inboard_front:
    label: "LCA Front Bush"
    type: bushing
    bore:
      part: lower_wishbone
      axis: {from: lower_wishbone_inboard_front, to: lower_wishbone_inboard_rear}
```

A rod end on a two-force member, bolt direction not yet designed:

```yaml
  trackrod_outboard:
    label: "Outer Tie Rod End"
    type: rod_end
    bore: {part: upright, axis: optimize}
    housing: {part: track_rod, axis: indeterminate}
```

A joint the assembly cannot resolve on its own, using the inline escape
hatch. The rack translates without rotating, so a bolt fixed to it holds a
constant direction in the chassis frame — naming `chassis` is both correct and
simpler than listing points:

```yaml
  trackrod_inboard:
    type: rod_end
    bore: {part: chassis, axis: optimize}
    housing: {part: track_rod, axis: indeterminate}
```

### 9.8 What you get out

Per declared joint, per side:

| Column | When |
| --- | --- |
| `joint_<name>_rx/ry/rz` | Always. Rotation vector of `Q`, degrees, in the housing's neutral frame. |
| `misalign_<name>` | Only when the bore axis is authored. A bore left as `optimize` is report-only. |

Plus a `joints.csv` and a report section carrying install offset, the required
angle with the sweep and step it peaked at, the best available axis, and the
locked clocking. See `CHARACTERISTICS.md` §G.

### 9.9 Errors, decoded

| Message | Cause |
| --- | --- |
| `Joint 'trackrod_outbord' does not name a suspension point` | Spelling. The key must be a PointID, lowercased. |
| `...names part 'track rodd', which is not a body...  Available parts: axle, chassis, lower_wishbone, ...` | Wrong body name. The message lists every legal one — use it as your autocomplete. |
| `...needs exactly two bodies meeting at its point, but 1 carry it: 'Track Rod'` | The assembly does not group a second body at that point. Name both sides with `part`, by body name or `{points: [...]}`. |
| `...declares an indeterminate housing, but part 'Upper Wishbone' is fitted from >=3 points` | `indeterminate` only applies to a two-point member. A fully located body has no unknown spin. |
| `...needs a bore axis: give 'bore.axis' a direction, or 'optimize'` | `bore:` omitted or left without an `axis`. |
| `'centred' belongs on the housing` / `'indeterminate' belongs on the housing` | Keyword on the wrong side. |
| `Optimising the housing direction is not implemented yet` | Use `centred` or `indeterminate`. |
| `...declares a bore axis 90.000 degrees away from the perpendicularity it also declares` | `axis` and `perpendicular_to` contradict each other. Drop one. |

### 9.10 Discovering the bodies in YOUR geometry

Don't guess the `part` names or which points even have two bodies — ask:

```python
import yaml
from pathlib import Path
from kinematics.core.input import build_suspension
from kinematics.core.joints import build_bodies, resolve_body_modes

s = build_suspension(yaml.safe_load(Path("models/aurora/front.yaml").read_text()))
corner = s.corners[min(s.corners)] if s.is_axle else s
neutral = corner.initial_state().positions
asm = corner.assembly()
bodies = resolve_body_modes(
    build_bodies(asm.elements, asm.points.fixed, corner.rigid_attachments()), neutral
)
for b in bodies:
    print(f"{b.name:16s} {b.mode.value:10s} {', '.join(p.name.lower() for p in b.points)}")
print()
for point in sorted({p for b in bodies for p in b.points}, key=lambda p: p.name):
    owners = [b.name for b in bodies if point in b.points]
    if len(owners) == 2:
        print(f"{point.name.lower():30s} {owners[0]} <-> {owners[1]}")
```

On your current front.yaml that prints:

```
Upper Wishbone   fitted     upper_wishbone_inboard_front, upper_wishbone_outboard, upper_wishbone_inboard_rear
Lower Wishbone   fitted     lower_wishbone_inboard_front, lower_wishbone_outboard, lower_wishbone_inboard_rear, strut_bottom
Upright          fitted     upper_wishbone_outboard, lower_wishbone_outboard, trackrod_outboard, axle_inboard, axle_outboard
Axle             transport  axle_inboard, axle_outboard
Wheel            fitted     wheel_center, wheel_inboard, wheel_outboard, axle_inboard, axle_outboard, wheel_contact_centre
Track Rod        transport  trackrod_inboard, trackrod_outboard
Spring/Damper    transport  strut_top, strut_bottom
Chassis          ground     lower_wishbone_inboard_front, lower_wishbone_inboard_rear, strut_top, ...

lower_wishbone_inboard_front   Lower Wishbone <-> Chassis
lower_wishbone_inboard_rear    Lower Wishbone <-> Chassis
lower_wishbone_outboard        Lower Wishbone <-> Upright
strut_bottom                   Lower Wishbone <-> Spring/Damper
strut_top                      Spring/Damper <-> Chassis
trackrod_outboard              Upright <-> Track Rod
upper_wishbone_inboard_front   Upper Wishbone <-> Chassis
upper_wishbone_inboard_rear    Upper Wishbone <-> Chassis
upper_wishbone_outboard        Upper Wishbone <-> Upright
```

The second list is the set of joints you can declare without naming `part` at
all. `trackrod_inboard` is absent from it because the rack is axle-level
hardware and a corner sees only the rod — that is the one joint on this
geometry needing an explicit `part`, and 9.7 shows it.

The `mode` column is how each body's rotation is recovered, and it is chosen
from point count alone: `ground` never rotates, `fitted` is determined by
three or more non-collinear points, and `transport` is a two-point member
whose spin is undetermined — the only bodies a housing may call
`indeterminate`.

**Adding a body group.** If a weldment of yours is modelled as several
two-point links and shows up as separate bodies, tag them with the same
`body_group=` in the topology's `elements()` — that is how the four wishbone
legs become two A-arms. Rigid-body membership is declared, never inferred: two
links sharing an endpoint is a joint in general (a pushrod meeting a rocker),
not a weld.
