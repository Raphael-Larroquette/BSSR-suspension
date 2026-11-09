# Geometry files

`front.yaml` / `rear.yaml` in a model folder. Read by the sweeps and the force solve.
Every block is `extra="forbid"`: an unknown or misspelt key is an error. Coordinates and
units: root `README.md` §3.

## File shapes

`scope:` decides the keys. Default `corner`.

| | `scope: axle` | `scope: corner` |
| --- | --- | --- |
| models | two corners | one corner |
| vehicle / axle data | `vehicle_config:` / `axle_config:` | both inside `config:` |
| mechanisms | inside `axle_config:` | top level |
| hardpoints | `hardpoints.left` / `.right` / `.center` | `hardpoints:` flat |
| `side:` | unused | `left` (default) or `center` |

```yaml
type: double_wishbone     # double_wishbone | macpherson | trailing_arm
scope: axle
name: "..."
version: "0.1.2"          # major = functional, minor = feature/test, patch = fix
units: millimeters        # only accepted value
```

- Axle: omit `hardpoints.right` to mirror `left` through `Y = 0`. `center:` holds shared
  points (ARB axis, T-bar pivot).
- Corner `side: right` is rejected; negate `y` instead. `side: center` (trailing arm only)
  suppresses camber, toe, steer, caster, KPI, scrub, trail, half track and FVIC/FVSA.

## Vehicle

| key | required | |
| --- | --- | --- |
| `cg_position` | yes | `{x, y, z}`. Identical in front and rear files |
| `wheelbase` | yes | mm. Identical in both files |
| `driven_axle` | no | `front` \| `rear` |
| `drive_torque_reaction` | with `driven_axle` | `sprung` (inboard motor) \| `unsprung` (hub motor). No default; anti-squat blank without it |
| `front_brake_bias` | no | 0-1. Anti-dive only; the force solve ignores it |
| `steering.rack_travel_per_turn` or `.pinion_radius` | no | mm. Enables `steering_ratio_unitless` |

## Axle

| key | values |
| --- | --- |
| `axle_position` | `front` \| `rear` |
| `steering.type` | `rack` (`trackrod_*`) \| `none` (`toe_link_*`) |
| `wheel.offset` | mm, ET, positive inboard |
| `wheel.tire.aspect_ratio` / `section_width` / `rim_diameter` | -, mm, **inches** |
| `wheel.tire.loaded_radius` | mm, optional: radius at design ride height |
| `anti_roll.type` | `none` \| `u_bar` \| `t_bar` (axle, pushrod-rocker only) |
| `heave_link.type` | `none` \| `rocker_to_rocker` (axle, pushrod-rocker only) |

## Mechanisms

| key | values | rule |
| --- | --- | --- |
| `actuation.type` | `direct` \| `pushrod_rocker` | double wishbone only |
| `actuation.mount` | `lower_wishbone` \| `upright` | body carrying the moving pickup |
| `spring.type` | `none` \| `coilover` \| `torsion_bar` | torsion bar needs `pushrod_rocker` (DW); trailing arm takes `coilover` or `torsion_bar` |
| `damper.type` | `none` \| `linear` | needs `pushrod_rocker`; not with a coilover |

Invalid combinations are rejected at load with the reason. Trailing arms require
`steering.type: none`.

`left_setup:` / `right_setup:` (axle): outboard camber shim (`shim_face_point_a/b`,
`shim_face_normal`, `design_thickness`, `setup_thickness`).

## Hardpoints

Fixed vocabulary; a typo is an error.

| architecture / option | points |
| --- | --- |
| double wishbone | `lower_wishbone_inboard_front/rear`, `lower_wishbone_outboard`, `upper_wishbone_*` (same), `axle_inboard`, `axle_outboard` |
| trailing arm | `trailing_arm_pivot_a/b`, `axle_inboard`, `axle_outboard`; `trailing_arm_outboard` (sided only) |
| macpherson | `lower_wishbone_*`, steering/toe link, axle points, strut (clamp on the LBJ-top-mount axis within 1 mm) |
| `steering: rack` / `none` | `trackrod_inboard/outboard` / `toe_link_inboard/outboard` |
| coilover, direct | `strut_top`, `strut_bottom` |
| `pushrod_rocker` | `pushrod_inboard/outboard`, `rocker_axis_a/b` |
| `torsion_bar` | `torsion_bar_axis_a/b` (trailing arm: plus `strut_top/bottom` damper) |
| `damper: linear` | `damper_chassis`, `damper_rocker` |
| `u_bar` | `droplink_rocker`, `droplink_u_bar`; `center:` `arb_u_bar_axis_a/b` |
| `t_bar` | `droplink_t_bar`; `center:` `arb_t_bar_pivot` |
| `rocker_to_rocker` | `heave_link_rocker` |

- `axle_outboard` is the axle axis at the hub face; `axle_inboard` any second point on
  the axis. Only the direction is used.
- Centreline trailing arm: no `trailing_arm_outboard` (`axle_inboard` is the arm point),
  pivots share an X, `axle_inboard` rearward of the pivot axis.
- Derived, never authored: `wheel_center`, `wheel_contact_centre`, `axle_midpoint`,
  `wheel_inboard`, `wheel_outboard`. Only `wheel_center` can be a sweep target.

Upstream examples: `tests/data/*geometry*.yaml` (corner, axle, explicit axle, rocker +
U-bar, T-bar, MacPherson, trailing arm).

## `joints:` (bearing misalignment)

Optional. Feeds only the report's misalignment table; no kinematics, not read by the
force solve. Undeclared points are not analysed. Re-declaring never needs a re-solve
(`--report-only --no-forces`). Declared once, applied to both sides.

```yaml
joints:
  <point name>:
    label: "LCA Front Bush"          # optional
    type: bushing                    # bushing | spherical | rod_end; vocabulary only
    bore:
      part: lower_wishbone           # optional when exactly two bodies meet here
      axis: {from: <point>, to: <point>}
    housing:                         # omit = centred
      part: chassis
      axis: centred
```

| key (on `bore` / `housing`) | value |
| --- | --- |
| `part` | body name, or `{points: [a, b, ...]}` |
| `axis` | axis spec, or `optimize` (bore) / `centred` / `indeterminate` (housing) |
| `perpendicular_to` | axis spec |
| `in_plane` | `{normal: <axis>}` or `{points: [a, b, c]}` |
| `cone_deg` | half-angle for an undetermined-spin body, default 90 |

Axis specs (neutral pose, chassis frame): `{from: a, to: b}` (preferred; follows the
geometry), `{vector: [x, y, z]}`, `{x:, y:, z:}`, `{chassis_axis: x}`.

| keyword | meaning |
| --- | --- |
| `optimize` | no axis yet; report gives the best available |
| `centred` | housing on the bore axis; install offset 0 |
| `indeterminate` | housing on a two-point member: reports a free-spin bound and a locked value. Size to the locked value |

Output: `joint_<name>_rx/ry/rz` (always), `misalign_<name>` (authored bore only),
`joints.csv`, report table. Sanity check: a wishbone inboard pivot reads 0.00°.

A wrong `part:` name is an error listing every legal body. A point needs `part:` when it
is not shared by exactly two bodies (e.g. `trackrod_inboard`, where the rack is axle-level).
