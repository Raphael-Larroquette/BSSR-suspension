"""
Animation utilities for suspension visualization.

This module provides animation functionality for suspension systems, making use of the
common plotting utilities from plots.py.
"""

from pathlib import Path

import matplotlib.animation as animation
import matplotlib.pyplot as plt

from kinematics.cli.visualization.main import SuspensionVisualizer
from kinematics.cli.visualization.overlays import (
    OverlaySeries,
    draw_overlays,
    update_overlays,
)
from kinematics.cli.visualization.plots import (
    compute_bounds_from_states,
    configure_3d_axis,
    create_four_view_axes,
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
    overlays: OverlaySeries | None = None,
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
        dpi: DPI for the output animation.
        show_live: Whether to show the animation live during creation.
        overlays: Optional construction geometry (instant centres, swing arms,
            roll centre) computed by ``overlays.build_overlays``. One frame per
            entry in ``position_states``.
    """
    # Create figure with four subplots using common function.
    fig, axes = create_four_view_axes()

    # Compute global bounds for all states.
    _, _, (x_mid, y_mid, z_mid, max_range) = compute_bounds_from_states(position_states)

    # Configure axes once using common function.
    for view_name, ax in axes.items():
        configure_3d_axis(ax, view_name, x_mid, y_mid, z_mid, max_range)

    # Use unified draw_links to create link artists.
    link_artists: dict[str, list] = {k: [] for k in axes.keys()}
    for view_name, ax in axes.items():
        link_artists[view_name] = visualizer.draw_links(ax, initial_positions)

    # Add legend once on iso view.
    axes["iso"].legend(loc="upper left")

    # Use unified draw_wheel to create wheel artists.
    num_bands = 36
    wheel_artists: dict[str, list[dict]] = {k: [] for k in axes.keys()}
    for view_name, ax in axes.items():
        wheel_artists[view_name] = visualizer.draw_wheel(
            ax, initial_positions, num_bands=num_bands
        )

    # Overlay artists (instant centres, swing arms, roll centre). Created once
    # per view and repointed each frame, like the links and wheels.
    overlay_artists: dict[str, dict] = {k: {} for k in axes.keys()}
    if overlays:
        for view_name, ax in axes.items():
            overlay_artists[view_name] = draw_overlays(ax, overlays)

    # Layout.
    plt.subplots_adjust(
        left=0.0, right=1, bottom=0.025, top=0.95, wspace=0.01, hspace=0.01
    )

    # Persistent title updated each frame (cheaper than re-creating)
    title_artist = fig.suptitle("", fontsize=16)
    title_center_key = (
        visualizer.wheel_references[0].center if visualizer.wheel_references else None
    )

    # Update function that only updates artist data (no clears/plots)
    def update(frame: int):
        positions = position_states[frame]

        # Update links.
        for view_name in axes.keys():
            visualizer.update_links(link_artists[view_name], positions)

        # Update wheel geometry.
        for view_name in axes.keys():
            visualizer.update_wheel(
                wheel_artists[view_name], positions, num_bands=num_bands
            )

        # Update construction overlays.
        if overlays and frame < len(overlays.frames):
            for view_name in axes.keys():
                update_overlays(overlay_artists[view_name], overlays.frames[frame])

        # Update global title.
        if title_center_key is None:
            title_artist.set_text(f"Frame {frame}")
        else:
            wheel_center_z = positions[title_center_key][2]
            initial_wheel_center_z = initial_positions[title_center_key][2]
            title_artist.set_text(
                f"Wheel Center Z: {wheel_center_z - initial_wheel_center_z:.1f} [mm]"
            )

        artists = []
        for view_name in axes.keys():
            artists.extend(link_artists[view_name])
            artists.extend(overlay_artists[view_name].values())
            for wheel in wheel_artists[view_name]:
                artists.extend(wheel["rims"])
                artists.extend(wheel["bands"])
        return artists

    # Play forward then reverse (ping-pong).
    pingpong_states = position_states + position_states[-2:0:-1]
    # The animation plays forward then backward, so a frame index is not a
    # state index on the return leg. Keep the mapping explicitly, otherwise the
    # overlays would run forward while the suspension runs back.
    pingpong_indices = list(range(len(position_states))) + list(
        range(len(position_states) - 2, 0, -1)
    )
    frame_indices = range(0, len(pingpong_states), 1)

    # Choose writer automatically if not provided.
    out_suffix = output_path.suffix.lower()
    chosen_writer: str
    if writer is not None:
        chosen_writer = writer
    elif out_suffix in {".mp4", ".m4v", ".mov"}:
        chosen_writer = "ffmpeg"
    else:
        chosen_writer = "pillow"

    try:
        if chosen_writer == "ffmpeg":
            Writer = animation.writers["ffmpeg"]
            writer_inst = Writer(fps=fps, codec=codec)
        else:
            Writer = animation.writers[chosen_writer]
            writer_inst = Writer(fps=fps)
    except Exception:
        # Fallback to pillow.
        Writer = animation.writers["pillow"]
        writer_inst = Writer(fps=fps)

    if show_live:
        plt.ion()
        plt.show(block=False)

    try:
        with writer_inst.saving(fig, str(output_path), dpi):
            for frame in frame_indices:
                positions = pingpong_states[frame]
                # Update all artists for this frame.
                state_index = pingpong_indices[frame]
                overlay_frame = (
                    overlays.frames[state_index]
                    if overlays and state_index < len(overlays.frames)
                    else None
                )
                for view_name in axes.keys():
                    visualizer.update_links(link_artists[view_name], positions)
                    visualizer.update_wheel(
                        wheel_artists[view_name], positions, num_bands=num_bands
                    )
                    if overlay_frame is not None:
                        update_overlays(
                            overlay_artists[view_name], overlay_frame
                        )
                # Update global title. Overlay values that are clipped out of
                # frame are reported here instead of being lost off-screen.
                wheel_center_z = positions[title_center_key][2]
                initial_wheel_center_z = initial_positions[title_center_key][2]
                title_lines = [
                    f"Wheel Center Z: "
                    f"{wheel_center_z - initial_wheel_center_z:.1f} [mm]"
                ]
                if overlay_frame is not None and overlay_frame.annotations:
                    title_lines.append("   ".join(overlay_frame.annotations))
                title_artist.set_text("\n".join(title_lines))
                if show_live:
                    fig.canvas.draw()
                    fig.canvas.flush_events()
                writer_inst.grab_frame()
    finally:
        if show_live:
            plt.ioff()
        plt.close(fig)
