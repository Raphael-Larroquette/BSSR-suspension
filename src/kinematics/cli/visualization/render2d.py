"""
Four-view sweep animations drawn in 2D and streamed to ffmpeg.

Each view (front, side, top, isometric) is an orthographic projection of the 3D
geometry onto an ordinary 2D matplotlib axis. The projections are the same ones the
old ``mplot3d`` views used (same elevation and azimuth), so the pictures read the
same way; drawing them in 2D skips mplot3d's per-artist Python projection, which
was most of the per-frame cost. Each wheel's 36 cross-tyre bands are one
``LineCollection`` rather than 36 separate lines.

Frames are never held in memory. Each one is drawn, copied out of the canvas as raw
RGB and written straight into an ffmpeg process, which encodes as it goes. The
ping-pong return leg is drawn again rather than buffered. Memory therefore stays at
one figure plus one ffmpeg encoder however long the sweep is.

* ``.gif``: a single 256-colour palette is built from the first, middle and last
  frames, then ffmpeg maps every frame onto it (``paletteuse``) without dithering.
  One palette for the whole animation means no per-frame quantisation, which was
  60% of the old renderer's time, and ffmpeg never has to buffer the frames.
* ``.mp4`` / ``.m4v`` / ``.mov``: H.264, full colour.

ffmpeg comes from the ``imageio-ffmpeg`` package, which ships a binary for Windows,
macOS and Linux, so ``uv sync`` installs it. An ``ffmpeg`` on PATH is used if that
package is missing.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

import numpy as np

from kinematics.cli.visualization.main import SuspensionVisualizer

Positions = Mapping[str, tuple[float, float, float]]

#: Figure size in inches. At the default dpi of 100 a frame is 1600 x 1000 px.
FIGSIZE = (16.0, 10.0)

#: Cross-tyre bands drawn on each wheel.
NUM_BANDS = 36

#: Camera (elevation, azimuth) in degrees, matching the old mplot3d views.
VIEW_ANGLES = {
    "front": (0.0, 0.0),
    "side": (0.0, 90.0),
    "top": (90.0, 0.0),
    "iso": (20.0, 45.0),
}
VIEW_TITLES = {
    "front": "Front View [Y-Z]",
    "side": "Side View [X-Z]",
    "top": "Top View [X-Y]",
    "iso": "Isometric View",
}
#: Grid placement, as before: front | side over top | iso.
VIEW_SLOTS = {"front": (0, 0), "side": (0, 1), "top": (1, 0), "iso": (1, 1)}

VIDEO_SUFFIXES = {".mp4", ".m4v", ".mov"}
GIF_SUFFIXES = {".gif"}

#: Fraction of each view's extent left as margin around the geometry.
MARGIN = 0.06


# ==========================================================================
# ffmpeg
# ==========================================================================
def ffmpeg_executable() -> str:
    """Return an ffmpeg binary: imageio-ffmpeg's bundled one, else PATH."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - missing package or missing binary
        pass
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise RuntimeError(
        "Animations need ffmpeg, and none was found. It normally comes with the "
        "project: run `uv sync` (it installs the imageio-ffmpeg package, which "
        "bundles ffmpeg). Otherwise install ffmpeg and put it on PATH."
    )


# ==========================================================================
# Projection
# ==========================================================================
def projection(elevation: float, azimuth: float) -> np.ndarray:
    """
    Return the 2x3 orthographic projection for a camera at (elevation, azimuth).

    Row 0 is the screen-right direction and row 1 screen-up, in world coordinates,
    as matplotlib's mplot3d defines them: azimuth 0 looks along -x with +y to the
    right; elevation 90 looks straight down.
    """
    el, az = np.radians(elevation), np.radians(azimuth)
    right = np.array([-np.sin(az), np.cos(az), 0.0])
    up = np.array([-np.sin(el) * np.cos(az), -np.sin(el) * np.sin(az), np.cos(el)])
    return np.vstack([right, up])


def _axis_label(direction: np.ndarray) -> tuple[str, float] | None:
    """For a screen axis along a world axis, its name and sign; else None."""
    index = int(np.argmax(np.abs(direction)))
    if abs(direction[index]) < 1.0 - 1e-9:
        return None
    return "XYZ"[index], float(np.sign(direction[index]))


# ==========================================================================
# Geometry
# ==========================================================================
def _wheel_geometry(
    positions: Positions, references, diameter: float, num_points: int
) -> tuple[list[np.ndarray], np.ndarray]:
    """Rims (centre, inboard, outboard) and band segments for one wheel."""
    centre = np.asarray(positions[references.center], dtype=float)
    inboard = np.asarray(positions[references.inboard], dtype=float)
    outboard = np.asarray(positions[references.outboard], dtype=float)
    axle = np.asarray(positions[references.axle_outboard], dtype=float) - np.asarray(
        positions[references.axle_inboard], dtype=float
    )
    e1 = axle / np.linalg.norm(axle)
    e2 = np.array([1.0, 0.0, 0.0])
    if abs(float(e1 @ e2)) > 0.9:
        e2 = np.array([0.0, 1.0, 0.0])
    e2 = e2 - (e2 @ e1) * e1
    e2 /= np.linalg.norm(e2)
    e3 = np.cross(e1, e2)
    radius = diameter / 2.0

    theta = np.linspace(0.0, 2.0 * np.pi, num_points)
    ring = radius * (np.cos(theta)[:, None] * e2 + np.sin(theta)[:, None] * e3)
    rims = [centre + ring, inboard + ring, outboard + ring]

    phi = np.linspace(0.0, 2.0 * np.pi, NUM_BANDS, endpoint=False)
    band = radius * (np.cos(phi)[:, None] * e2 + np.sin(phi)[:, None] * e3)
    bands = np.stack([inboard + band, outboard + band], axis=1)  # (bands, 2, 3)
    return rims, bands


class FourViewRenderer:
    """One figure with every artist created once, moved frame by frame."""

    def __init__(
        self,
        visualizer: SuspensionVisualizer,
        position_states: Sequence[Positions],
        initial_positions: Positions,
        dpi: int = 100,
    ):
        import matplotlib

        matplotlib.use("Agg", force=True)
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.collections import LineCollection
        from matplotlib.figure import Figure

        self.visualizer = visualizer
        self.initial_positions = initial_positions
        self.dpi = int(dpi)
        self.figure = Figure(figsize=FIGSIZE, dpi=self.dpi)
        self.canvas = FigureCanvasAgg(self.figure)
        grid = self.figure.add_gridspec(2, 2)
        config = visualizer.wheel_config

        # Global bounds over every point in every state (wheels included), so
        # no view rescales during the animation.
        cloud = self._point_cloud(position_states)

        self.views: dict[str, dict] = {}
        for name, (elevation, azimuth) in VIEW_ANGLES.items():
            row, col = VIEW_SLOTS[name]
            ax = self.figure.add_subplot(grid[row, col])
            matrix = projection(elevation, azimuth)
            labels = [_axis_label(matrix[0]), _axis_label(matrix[1])]
            # A screen axis that is a negative world axis is drawn with that
            # world coordinate and the axis inverted, so ticks read true values.
            signs = np.array([lab[1] if lab else 1.0 for lab in labels])
            screen = cloud @ (matrix * signs[:, None]).T
            low, high = screen.min(axis=0), screen.max(axis=0)
            pad = MARGIN * float((high - low).max())
            ax.set_xlim(low[0] - pad, high[0] + pad)
            ax.set_ylim(low[1] - pad, high[1] + pad)
            if signs[0] < 0:
                ax.invert_xaxis()
            if signs[1] < 0:
                ax.invert_yaxis()
            ax.set_aspect("equal", adjustable="box")
            ax.set_title(VIEW_TITLES[name])
            ax.grid(alpha=0.3)
            if labels[0] and labels[1]:
                ax.set_xlabel(f"{labels[0][0]} [mm]")
                ax.set_ylabel(f"{labels[1][0]} [mm]")
            else:
                # An oblique view has no world axis along the screen, so
                # coordinates on it would mislead.
                ax.set_xticks([])
                ax.set_yticks([])
                ax.grid(False)

            links = []
            for link in visualizer.links:
                (line,) = ax.plot(
                    [],
                    [],
                    color=link.style.color,
                    linewidth=link.style.linewidth * 0.75,
                    linestyle=link.style.linestyle,
                    marker=link.style.marker,
                    markersize=link.style.markersize * 0.6,
                )
                links.append(line)
            rims = LineCollection(
                [],
                colors=config.color,
                linewidths=1.0,
                alpha=config.alpha * 0.6,
                linestyles=config.linestyle,
            )
            bands = LineCollection(
                [],
                colors=config.color,
                linewidths=0.6,
                alpha=config.alpha * 0.5,
                linestyles=config.linestyle,
            )
            ax.add_collection(rims)
            ax.add_collection(bands)
            self.views[name] = {
                "ax": ax,
                "matrix": matrix * signs[:, None],
                "links": links,
                "rims": rims,
                "bands": bands,
            }

        self._legend()
        self.title = self.figure.suptitle("", fontsize=15)
        self.figure.subplots_adjust(
            left=0.05, right=0.98, bottom=0.09, top=0.92, wspace=0.12, hspace=0.3
        )
        refs = visualizer.wheel_references
        self.title_key = refs[0].center if refs else None

        # Blitting: everything that never moves (axes, grid, ticks, labels,
        # legend) is rendered once into a background; each frame restores it
        # and draws only the moving artists on top. Static text and ticks were
        # most of a full redraw's cost.
        self.moving = [
            (view["ax"], artist)
            for view in self.views.values()
            for artist in (*view["links"], view["rims"], view["bands"])
        ]
        for _ax, artist in self.moving:
            artist.set_animated(True)
        self.title.set_animated(True)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.figure.bbox)

        width, height = self.canvas.get_width_height()
        # yuv420p (H.264) needs even dimensions; crop a pixel if necessary.
        self.size = (width - width % 2, height - height % 2)

    def _legend(self) -> None:
        """One entry per kind of element (wishbone, track rod, ...), not per link."""
        from matplotlib.lines import Line2D

        handles: dict[str, Line2D] = {}
        for link in self.visualizer.links:
            kind = str(getattr(link.element.type, "name", link.element.type))
            name = kind.replace("_", " ").capitalize()
            if name in handles:
                continue
            style = link.style
            handles[name] = Line2D(
                [], [], color=style.color, linewidth=style.linewidth * 0.75,
                linestyle=style.linestyle, marker=style.marker,
                markersize=style.markersize * 0.6,
            )  # fmt: skip
        handles["Wheel"] = Line2D([], [], color=self.visualizer.wheel_config.color)
        self.figure.legend(
            list(handles.values()), list(handles), loc="lower center",
            ncol=min(len(handles), 8), fontsize=9, frameon=False,
        )  # fmt: skip

    def _point_cloud(self, states: Sequence[Positions]) -> np.ndarray:
        config = self.visualizer.wheel_config
        points: list[np.ndarray] = []
        for positions in states:
            points.append(np.asarray(list(positions.values()), dtype=float))
            for refs in self.visualizer.wheel_references:
                rims, _ = _wheel_geometry(positions, refs, config.diameter, 24)
                points.extend(rims)
        return np.vstack(points)

    def draw(self, positions: Positions, label: str = "") -> None:
        """Move every artist to one state."""
        config = self.visualizer.wheel_config
        wheels = [
            _wheel_geometry(positions, refs, config.diameter, config.num_points)
            for refs in self.visualizer.wheel_references
        ]
        link_points = [
            np.asarray([positions[name] for name in link.points], dtype=float)
            for link in self.visualizer.links
        ]
        for view in self.views.values():
            matrix = view["matrix"]
            for line, points in zip(view["links"], link_points):
                screen = points @ matrix.T
                line.set_data(screen[:, 0], screen[:, 1])
            view["rims"].set_segments(
                [rim @ matrix.T for rims, _ in wheels for rim in rims]
            )
            view["bands"].set_segments(
                [band @ matrix.T for _, bands in wheels for band in bands]
            )

        key = self.title_key
        if key is None:
            text = label
        else:
            dz = positions[key][2] - self.initial_positions[key][2]
            text = f"Wheel Center Z: {dz:.1f} [mm]"
            if label:
                text += f"    {label}"
        self.title.set_text(text)

    def rgb(self) -> np.ndarray:
        """Render the current state and return it as an (H, W, 3) uint8 array."""
        self.canvas.restore_region(self.background)
        for ax, artist in self.moving:
            ax.draw_artist(artist)
        self.figure.draw_artist(self.title)
        width, height = self.size
        buffer = np.asarray(self.canvas.buffer_rgba())
        return np.ascontiguousarray(buffer[:height, :width, :3])

    def close(self) -> None:
        self.figure.clear()


# ==========================================================================
# Writing
# ==========================================================================
def _pingpong_order(count: int) -> list[int]:
    """Forward then back, without repeating either end: 0..n-1, n-2..1."""
    return list(range(count)) + list(range(count - 2, 0, -1))


def _frames(
    renderer: FourViewRenderer, states: Sequence[Positions]
) -> Iterator[np.ndarray]:
    total = len(states)
    for index in _pingpong_order(total):
        renderer.draw(states[index], f"step {index + 1}/{total}")
        yield renderer.rgb()


def _palette_png(
    renderer: FourViewRenderer, states: Sequence[Positions], path: Path
) -> None:
    """One 256-colour palette from the first, middle and last frames."""
    from PIL import Image

    picks = sorted({0, len(states) // 2, len(states) - 1})
    tiles = []
    for index in picks:
        renderer.draw(states[index], f"step {index + 1}/{len(states)}")
        tiles.append(renderer.rgb())
    sample = Image.fromarray(np.vstack(tiles))
    quantised = sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    palette = quantised.getpalette() or []
    palette = (palette + [0, 0, 0] * 256)[: 256 * 3]
    swatch = Image.new("RGB", (16, 16))
    swatch.putdata([tuple(palette[i * 3 : i * 3 + 3]) for i in range(256)])
    swatch.save(path)


def _encode(cmd: list[str], frames: Iterator[np.ndarray]) -> None:
    """Pipe raw RGB frames into ffmpeg and fail loudly if it does."""
    process = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    assert process.stdin is not None
    try:
        for frame in frames:
            process.stdin.write(frame.tobytes())
        process.stdin.close()
    except BrokenPipeError:
        pass
    finally:
        if not process.stdin.closed:
            process.stdin.close()
        stderr = (
            process.stderr.read().decode(errors="replace") if process.stderr else ""
        )
        code = process.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg failed (exit {code}): {stderr.strip()[-2000:]}")


def write_animation(
    position_states: Sequence[Positions],
    initial_positions: Positions,
    visualizer: SuspensionVisualizer,
    output_path: Path,
    fps: int = 20,
    dpi: int = 100,
) -> Path:
    """
    Draw a ping-pong animation of the states and write it as .gif or .mp4.

    Memory stays at one figure plus one ffmpeg process regardless of length.
    """
    output_path = Path(output_path)
    suffix = output_path.suffix.lower()
    if suffix not in GIF_SUFFIXES | VIDEO_SUFFIXES:
        raise ValueError(f"unsupported animation format '{suffix}': use .gif or .mp4")
    if not position_states:
        raise ValueError("no states to animate")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = ffmpeg_executable()
    renderer = FourViewRenderer(visualizer, position_states, initial_positions, dpi)
    width, height = renderer.size
    raw_input = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
        "-r", str(int(fps)), "-i", "-",
    ]  # fmt: skip
    # Write beside the target and rename at the end, so an interrupted run never
    # leaves a truncated file that looks finished.
    partial = output_path.with_name(output_path.stem + ".partial" + suffix)
    try:
        if suffix in GIF_SUFFIXES:
            with tempfile.TemporaryDirectory() as scratch:
                palette = Path(scratch) / "palette.png"
                _palette_png(renderer, position_states, palette)
                cmd = [
                    *raw_input, "-i", str(palette),
                    "-lavfi", "paletteuse=dither=none:diff_mode=rectangle",
                    "-loop", "0", "-threads", "1", "-f", "gif", str(partial),
                ]  # fmt: skip
                _encode(cmd, _frames(renderer, position_states))
        else:
            cmd = [
                *raw_input,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-threads", "1", "-f", "mp4", str(partial),
            ]  # fmt: skip
            _encode(cmd, _frames(renderer, position_states))
        partial.replace(output_path)
    finally:
        renderer.close()
        if partial.exists():
            partial.unlink()
    return output_path
