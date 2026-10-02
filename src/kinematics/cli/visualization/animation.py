"""
Animation utilities for suspension visualization.

This module provides animation functionality for suspension systems, making use of the
common plotting utilities from plots.py.

GIFs are rendered frame by frame into palette images and written with Pillow. Two
things make that much faster than matplotlib's own PillowWriter:

* The animation plays forward then back (ping-pong), so only the unique frames are
  rendered; the return leg reuses them.
* With ``workers > 1`` the unique frames are rendered in parallel worker processes,
  each holding its own copy of the figure. A frame is converted to a palette image in
  the worker, so the parent holds ~1 byte per pixel per unique frame rather than 3 per
  pixel per played frame.

Frames are drawn by the same two functions on either path, so a parallel GIF is
pixel-for-pixel the GIF a serial run writes. Video formats (ffmpeg) and live preview
keep the serial matplotlib writer.
"""

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from io import BytesIO
from multiprocessing import get_context
from pathlib import Path

import matplotlib.animation as animation
import matplotlib.pyplot as plt

from kinematics.cli.visualization.main import SuspensionVisualizer
from kinematics.cli.visualization.plots import (
    compute_bounds_from_states,
    configure_3d_axis,
    create_four_view_axes,
)

#: Cross-tyre bands drawn on each wheel.
NUM_BANDS = 36

#: Most worker processes one pool may hold on Windows (its WaitForMultipleObjects
#: limit, less headroom); ProcessPoolExecutor refuses more than 61 there.
WINDOWS_MAX_WORKERS = 60


@dataclass
class _Scene:
    """A figure with every artist created once, ready to be moved frame by frame."""

    fig: object
    axes: dict
    link_artists: dict
    wheel_artists: dict
    title_artist: object
    title_center_key: str | None
    initial_positions: dict
    visualizer: SuspensionVisualizer


def _build_scene(
    position_states: list[dict[str, tuple[float, float, float]]],
    initial_positions: dict[str, tuple[float, float, float]],
    visualizer: SuspensionVisualizer,
) -> _Scene:
    """Create the four-view figure and every artist the animation moves."""
    fig, axes = create_four_view_axes()

    # Global bounds over every state, so the axes never rescale mid-animation.
    _, _, (x_mid, y_mid, z_mid, max_range) = compute_bounds_from_states(position_states)
    for view_name, ax in axes.items():
        configure_3d_axis(ax, view_name, x_mid, y_mid, z_mid, max_range)

    link_artists = {
        view_name: visualizer.draw_links(ax, initial_positions)
        for view_name, ax in axes.items()
    }
    axes["iso"].legend(loc="upper left")
    wheel_artists = {
        view_name: visualizer.draw_wheel(ax, initial_positions, num_bands=NUM_BANDS)
        for view_name, ax in axes.items()
    }

    plt.subplots_adjust(
        left=0.0, right=1, bottom=0.025, top=0.95, wspace=0.01, hspace=0.01
    )
    title_artist = fig.suptitle("", fontsize=16)
    title_center_key = (
        visualizer.wheel_references[0].center if visualizer.wheel_references else None
    )
    return _Scene(
        fig=fig,
        axes=axes,
        link_artists=link_artists,
        wheel_artists=wheel_artists,
        title_artist=title_artist,
        title_center_key=title_center_key,
        initial_positions=initial_positions,
        visualizer=visualizer,
    )


def _draw_frame(
    scene: _Scene, positions: dict[str, tuple[float, float, float]], frame: int
) -> None:
    """Move every artist to one state and set the title."""
    for view_name in scene.axes:
        scene.visualizer.update_links(scene.link_artists[view_name], positions)
        scene.visualizer.update_wheel(
            scene.wheel_artists[view_name], positions, num_bands=NUM_BANDS
        )
    key = scene.title_center_key
    if key is None:
        scene.title_artist.set_text(f"Frame {frame}")
    else:
        dz = positions[key][2] - scene.initial_positions[key][2]
        scene.title_artist.set_text(f"Wheel Center Z: {dz:.1f} [mm]")


def _grab_palette_frame(fig, dpi: int):
    """
    Render the figure and return it as a GIF-ready palette ('P') image.

    Matches what matplotlib's PillowWriter followed by Pillow's GIF encoder does to
    an opaque frame (RGBA -> RGB -> adaptive palette), so the GIF looks the same.
    """
    from PIL import Image

    width, height = fig.get_size_inches()
    size = (int(width * dpi), int(height * dpi))
    buffer = BytesIO()
    fig.savefig(buffer, format="rgba", dpi=dpi)
    image = Image.frombuffer("RGBA", size, buffer.getbuffer(), "raw", "RGBA", 0, 1)
    return image.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE)


# Per-process state for parallel rendering: each worker builds the figure once.
_WORKER: dict = {}


def _init_worker(position_states, initial_positions, visualizer, dpi) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    _WORKER["scene"] = _build_scene(position_states, initial_positions, visualizer)
    _WORKER["states"] = position_states
    _WORKER["dpi"] = dpi


def _render_in_worker(frame: int):
    scene = _WORKER["scene"]
    _draw_frame(scene, _WORKER["states"][frame], frame)
    return _grab_palette_frame(scene.fig, _WORKER["dpi"])


def resolve_workers(workers: int | None, frames: int) -> int:
    """
    Turn a requested worker count into one this machine and this GIF can use.

    None or 0 means one per logical CPU. Never more than there are frames, and never
    more than one Windows process pool allows.
    """
    available = os.cpu_count() or 1
    count = available if not workers else int(workers)
    if os.name == "nt":
        count = min(count, WINDOWS_MAX_WORKERS)
    return max(1, min(count, frames))


def render_gif_frames(
    position_states: list[dict[str, tuple[float, float, float]]],
    initial_positions: dict[str, tuple[float, float, float]],
    visualizer: SuspensionVisualizer,
    dpi: int = 200,
    workers: int | None = 1,
) -> list:
    """Render one palette image per state, in order, on ``workers`` processes."""
    count = resolve_workers(workers, len(position_states))
    if count == 1:
        scene = _build_scene(position_states, initial_positions, visualizer)
        try:
            frames = []
            for index, positions in enumerate(position_states):
                _draw_frame(scene, positions, index)
                frames.append(_grab_palette_frame(scene.fig, dpi))
            return frames
        finally:
            plt.close(scene.fig)

    # "spawn" on every platform: it is the only start method Windows has, and on
    # Linux it keeps a forked copy of the parent's matplotlib state out of workers.
    with ProcessPoolExecutor(
        max_workers=count,
        mp_context=get_context("spawn"),
        initializer=_init_worker,
        initargs=(position_states, initial_positions, visualizer, dpi),
    ) as pool:
        return list(pool.map(_render_in_worker, range(len(position_states))))


def write_pingpong_gif(frames: list, output_path: Path, fps: int) -> None:
    """Write frames forward then back, reusing each image on the return leg."""
    played = frames + frames[-2:0:-1]
    played[0].save(
        str(output_path),
        save_all=True,
        append_images=played[1:],
        duration=int(1000 / fps),
        loop=0,
    )


def create_animation(
    position_states: list[dict[str, tuple[float, float, float]]],
    initial_positions: dict[str, tuple[float, float, float]],
    visualizer: SuspensionVisualizer,
    output_path: Path,
    fps: int = 20,
    writer: str | None = None,
    codec: str = "libx264",
    dpi: int = 200,
    show_live: bool = True,
    workers: int | None = 1,
) -> None:
    """
    Create an animation showing suspension movement through multiple states.

    Args:
        position_states: List of position dictionaries for each frame.
        initial_positions: Initial position state for reference.
        visualizer: Suspension visualizer with links and wheel config.
        output_path: Path where the animation will be saved.
        fps: Frames per second for the animation.
        writer: Animation writer to use ('ffmpeg', 'pillow', etc.).
        codec: Video codec to use (for ffmpeg writer).
        dpi: DPI for the output animation. Render time and file size scale with
            its square.
        show_live: Whether to show the animation live during creation.
        workers: Processes rendering GIF frames. 1 renders in this process; None
            or 0 uses every logical CPU. Ignored for video and live preview.
    """
    output_path = Path(output_path)

    # Choose writer automatically if not provided.
    if writer is not None:
        chosen_writer = writer
    elif output_path.suffix.lower() in {".mp4", ".m4v", ".mov"}:
        chosen_writer = "ffmpeg"
    else:
        chosen_writer = "pillow"

    if chosen_writer == "pillow" and not show_live:
        frames = render_gif_frames(
            position_states, initial_positions, visualizer, dpi=dpi, workers=workers
        )
        write_pingpong_gif(frames, output_path, fps)
        return

    _create_animation_serial(
        position_states,
        initial_positions,
        visualizer,
        output_path,
        fps=fps,
        chosen_writer=chosen_writer,
        codec=codec,
        dpi=dpi,
        show_live=show_live,
    )


def _create_animation_serial(
    position_states,
    initial_positions,
    visualizer,
    output_path: Path,
    fps: int,
    chosen_writer: str,
    codec: str,
    dpi: int,
    show_live: bool,
) -> None:
    """Render through a matplotlib writer: video output, or a live preview."""
    scene = _build_scene(position_states, initial_positions, visualizer)

    # Play forward then reverse (ping-pong).
    pingpong_states = position_states + position_states[-2:0:-1]

    try:
        if chosen_writer == "ffmpeg":
            writer_inst = animation.writers["ffmpeg"](fps=fps, codec=codec)
        else:
            writer_inst = animation.writers[chosen_writer](fps=fps)
    except Exception:
        # Fallback to pillow.
        writer_inst = animation.writers["pillow"](fps=fps)

    if show_live:
        plt.ion()
        plt.show(block=False)

    try:
        with writer_inst.saving(scene.fig, str(output_path), dpi):
            for frame, positions in enumerate(pingpong_states):
                _draw_frame(scene, positions, frame)
                if show_live:
                    scene.fig.canvas.draw()
                    scene.fig.canvas.flush_events()
                writer_inst.grab_frame()
    finally:
        if show_live:
            plt.ioff()
        plt.close(scene.fig)
