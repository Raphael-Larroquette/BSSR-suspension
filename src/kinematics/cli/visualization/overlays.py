"""
Construction-geometry overlays for the sweep animation.

The links and wheels an animation already draws are the parts you can touch.
These overlays draw the things that decide how the suspension behaves but have
no physical member: the front- and side-view instant centres, the swing arms
that run to them, and the roll centre built from the two front-view lines.

Everything here is a presentation concern. The values are read from the same
suspension API the metrics use, so an overlay can never disagree with the
report - if a channel is None in the CSV it is simply not drawn.

Clipping
--------
An instant centre routinely sits tens of metres from a car that is two metres
wide, and the front-view IC runs to infinity every time the wishbones pass
through parallel. Autoscaling to include it would shrink the suspension to a
dot, so a marker outside `frame` times the geometry bounding box is pulled back
onto the frame boundary along the same direction and drawn hollow. The true
value is printed in the animation title rather than left off-screen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Sequence

import numpy as np

from kinematics.core.enums import Axis, PointID
from kinematics.core.primitives.point_ref import Side

if TYPE_CHECKING:
    from kinematics.core.state import SuspensionState
    from kinematics.core.suspensions.base import Suspension

# Overlay names accepted in run.yaml / --animation-overlays.
KNOWN_OVERLAYS = ("fvic", "fvsa", "svic", "svsa", "roll_center")

_COLOURS = {
    "fvic": "#2f6fdb",
    "fvsa": "#2f6fdb",
    "svic": "#b07d2b",
    "svsa": "#b07d2b",
    "roll_center": "#d1495b",
}


@dataclass
class OverlayFrame:
    """One animation frame's worth of construction geometry."""

    points: dict[str, np.ndarray] = field(default_factory=dict)
    segments: dict[str, np.ndarray] = field(default_factory=dict)
    clipped: set[str] = field(default_factory=set)
    annotations: list[str] = field(default_factory=list)


@dataclass
class OverlaySeries:
    """Every frame's overlay geometry, with a stable set of artist names."""

    frames: list[OverlayFrame]
    point_names: tuple[str, ...]
    segment_names: tuple[str, ...]

    def __bool__(self) -> bool:
        return bool(self.point_names or self.segment_names)

    @staticmethod
    def colour_for(name: str) -> str:
        for key, colour in _COLOURS.items():
            if name.startswith(key):
                return colour
        return "#5c6670"


def normalise_overlays(requested: Sequence[str] | str | None) -> tuple[str, ...]:
    """Validate an overlay request, tolerating a comma-separated string."""
    if requested is None:
        return ()
    if isinstance(requested, str):
        requested = [part.strip() for part in requested.split(",")]
    wanted = [name.strip().lower() for name in requested if name and name.strip()]
    if not wanted or wanted == ["none"]:
        return ()
    unknown = [name for name in wanted if name not in KNOWN_OVERLAYS]
    if unknown:
        raise ValueError(
            f"unknown animation overlay(s): {', '.join(unknown)}. "
            f"Known overlays: {', '.join(KNOWN_OVERLAYS)}"
        )
    # Drawing a swing arm without its instant centre is meaningless, so a
    # request for one implies the other.
    if "fvsa" in wanted and "fvic" not in wanted:
        wanted.append("fvic")
    if "svsa" in wanted and "svic" not in wanted:
        wanted.append("svic")
    return tuple(dict.fromkeys(wanted))


def _corners(suspension: "Suspension") -> list[tuple[str, object]]:
    """Return [(label, corner)] for an axle or a standalone corner."""
    corners = getattr(suspension, "corners", None)
    if isinstance(corners, dict) and corners:
        return [(side.name.lower(), corner) for side, corner in corners.items()]
    return [("", suspension)]


def _corner_state(suspension: "Suspension", state: "SuspensionState", label: str):
    """Resolve the per-corner state, for an axle or a standalone corner."""
    if not label:
        return state
    corner_state = getattr(suspension, "corner_state", None)
    if corner_state is None:
        return state
    return corner_state(state, Side.LEFT if label == "left" else Side.RIGHT)


def _xyz(point) -> np.ndarray:
    return np.asarray(
        [float(point[Axis.X]), float(point[Axis.Y]), float(point[Axis.Z])],
        dtype=float,
    )


def _clip(origin: np.ndarray, target: np.ndarray, centre: np.ndarray,
          limit: float) -> tuple[np.ndarray, bool]:
    """Pull `target` back onto the frame boundary if it lies outside it."""
    if not np.isfinite(target).all():
        return target, False
    offset = target - centre
    reach = float(np.max(np.abs(offset)))
    if reach <= limit or reach == 0.0:
        return target, False
    direction = target - origin
    length = float(np.linalg.norm(direction))
    if length == 0.0:
        return target, False
    direction = direction / length
    # Walk out from the origin until the box is exceeded.
    lo, hi = 0.0, length
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if float(np.max(np.abs(origin + mid * direction - centre))) > limit:
            hi = mid
        else:
            lo = mid
    return origin + lo * direction, True


def build_overlays(
    suspension: "Suspension",
    states: Sequence["SuspensionState"],
    overlays: Sequence[str],
    centre: np.ndarray,
    max_range: float,
    frame: float = 3.0,
) -> OverlaySeries:
    """Compute every frame's overlay geometry.

    `centre` and `max_range` describe the view the animation has already sized
    to the links and wheels; `frame` is how many times that half-range an
    overlay marker is allowed to stray before it is clipped.
    """
    overlays = normalise_overlays(overlays)
    if not overlays:
        return OverlaySeries([], (), ())

    limit = max(1.0, 0.5 * max_range * float(frame))
    corners = _corners(suspension)
    frames: list[OverlayFrame] = []
    point_names: list[str] = []
    segment_names: list[str] = []

    for state in states:
        current = OverlayFrame()
        fvic_lines: list[tuple[np.ndarray, np.ndarray]] = []
        fvsa_values: list[str] = []

        for label, corner in corners:
            corner_state = _corner_state(suspension, state, label)
            try:
                contact = _xyz(corner_state.get(PointID.WHEEL_CONTACT_CENTRE))
            except Exception:
                continue
            suffix = f"_{label}" if label else ""

            if "fvic" in overlays:
                fvic = corner.compute_front_view_instant_center(corner_state)
                if fvic is not None:
                    # The front-view IC lives in the Y-Z plane; place it at the
                    # contact centre's X so the swing arm is drawn in the plane
                    # the front view actually shows.
                    raw = _xyz(fvic)
                    raw[0] = contact[0]
                    fvic_lines.append((contact, raw))
                    drawn, clipped = _clip(contact, raw, centre, limit)
                    name = f"fvic{suffix}"
                    current.points[name] = drawn
                    if clipped:
                        current.clipped.add(name)
                    if "fvsa" in overlays:
                        seg = f"fvsa{suffix}"
                        current.segments[seg] = np.vstack([contact, drawn])
                        fvsa_values.append(
                            f"{label or 'corner'} FVSA "
                            f"{float(np.linalg.norm(raw - contact)):.0f} mm"
                        )

            if "svic" in overlays:
                svic = corner.compute_side_view_instant_center(corner_state)
                if svic is not None:
                    raw = _xyz(svic)
                    raw[1] = contact[1]
                    drawn, clipped = _clip(contact, raw, centre, limit)
                    name = f"svic{suffix}"
                    current.points[name] = drawn
                    if clipped:
                        current.clipped.add(name)
                    if "svsa" in overlays:
                        current.segments[f"svsa{suffix}"] = np.vstack([contact, drawn])

        if "roll_center" in overlays and len(fvic_lines) == 2:
            rc = _roll_centre(fvic_lines)
            if rc is not None:
                x = float(np.mean([line[0][0] for line in fvic_lines]))
                raw = np.array([x, rc[0], rc[1]], dtype=float)
                anchor = fvic_lines[0][0]
                drawn, clipped = _clip(anchor, raw, centre, limit)
                current.points["roll_center"] = drawn
                if clipped:
                    current.clipped.add("roll_center")
                for index, (contact, _fvic) in enumerate(fvic_lines):
                    current.segments[f"roll_center_line_{index}"] = np.vstack(
                        [contact, drawn])
                current.annotations.append(f"RC z {rc[1]:.1f} mm")

        current.annotations = fvsa_values + current.annotations
        frames.append(current)
        for name in current.points:
            if name not in point_names:
                point_names.append(name)
        for name in current.segments:
            if name not in segment_names:
                segment_names.append(name)

    return OverlaySeries(frames, tuple(point_names), tuple(segment_names))


def _roll_centre(
    lines: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, float] | None:
    """Intersect the two contact-to-FVIC lines in the Y-Z plane.

    Same construction as `kinematics.core.metrics.axle_metrics._roll_center`,
    repeated here on the drawn points so the marker cannot drift from the line
    it is supposed to sit on.
    """
    (contact_a, fvic_a), (contact_b, fvic_b) = lines
    ay, az = float(contact_a[1]), float(contact_a[2])
    ady, adz = float(fvic_a[1]) - ay, float(fvic_a[2]) - az
    by, bz = float(contact_b[1]), float(contact_b[2])
    bdy, bdz = float(fvic_b[1]) - by, float(fvic_b[2]) - bz

    denominator = ady * bdz - adz * bdy
    if abs(denominator) < 1e-12:
        return None
    parameter = ((by - ay) * bdz - (bz - az) * bdy) / denominator
    return ay + parameter * ady, az + parameter * adz


def draw_overlays(ax, series: OverlaySeries) -> dict[str, object]:
    """Create the overlay artists on one axis. Returns them by name."""
    artists: dict[str, object] = {}
    for name in series.segment_names:
        colour = OverlaySeries.colour_for(name)
        line, = ax.plot([], [], [], color=colour, lw=1.1, linestyle="--",
                        label="_nolegend_")
        artists[f"seg:{name}"] = line
    for name in series.point_names:
        colour = OverlaySeries.colour_for(name)
        marker, = ax.plot([], [], [], color=colour, marker="o", markersize=6,
                          linestyle="none", label="_nolegend_")
        artists[f"pt:{name}"] = marker
    return artists


def update_overlays(artists: dict[str, object], frame: OverlayFrame) -> list:
    """Point the overlay artists at one frame. Returns the touched artists."""
    touched = []
    for key, artist in artists.items():
        kind, name = key.split(":", 1)
        if kind == "seg":
            segment = frame.segments.get(name)
            if segment is None:
                artist.set_data([], [])
                artist.set_3d_properties([])
            else:
                artist.set_data(segment[:, 0], segment[:, 1])
                artist.set_3d_properties(segment[:, 2])
        else:
            point = frame.points.get(name)
            if point is None or not np.isfinite(point).all():
                artist.set_data([], [])
                artist.set_3d_properties([])
            else:
                artist.set_data([point[0]], [point[1]])
                artist.set_3d_properties([point[2]])
                # A clipped marker is not where the instant centre really is,
                # so draw it hollow: filled means "this is the actual point".
                artist.set_markerfacecolor(
                    "none" if name in frame.clipped else artist.get_color())
        touched.append(artist)
    return touched
