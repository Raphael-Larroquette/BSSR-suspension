"""
Animation entry point for suspension sweeps.

Files (``.gif``, ``.mp4``) are drawn by ``render2d``: four orthographic views on 2D
axes, streamed frame by frame into ffmpeg, so memory stays flat however long the
sweep is. See that module for why.

A live preview (``show_live=True``) keeps the original interactive mplot3d figure,
drawn serially through a matplotlib writer.
"""

from dataclasses import dataclass
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


def create_animation(
    position_states: list[dict[str, tuple[float, float, float]]],
    initial_positions: dict[str, tuple[float, float, float]],
    visualizer: SuspensionVisualizer,
    output_path: Path,
    fps: int = 20,
    writer: str | None = None,
    codec: str = "libx264",
    dpi: int = 100,
    show_live: bool = True,
) -> None:
    """
    Create an animation showing suspension movement through multiple states.

    Args:
        position_states: List of position dictionaries for each frame.
        initial_positions: Initial position state for reference.
        visualizer: Suspension visualizer with links and wheel config.
        output_path: Path where the animation will be saved (.gif or .mp4).
        fps: Frames per second for the animation.
        writer: Matplotlib writer for the live preview only ('ffmpeg', 'pillow').
        codec: Video codec for the live preview's ffmpeg writer.
        dpi: Resolution. Frames are 16 x 10 inches, so dpi 100 is 1600 x 1000 px;
            render time scales with its square.
        show_live: Show an interactive 3D preview while writing (slow, serial).
    """
    output_path = Path(output_path)

    if not show_live:
        from kinematics.cli.visualization.render2d import write_animation

        write_animation(
            position_states,
            initial_positions,
            visualizer,
            output_path,
            fps=fps,
            dpi=dpi,
        )
        return

    if writer is not None:
        chosen_writer = writer
    elif output_path.suffix.lower() in {".mp4", ".m4v", ".mov"}:
        chosen_writer = "ffmpeg"
    else:
        chosen_writer = "pillow"

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
