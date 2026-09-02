"""Bearing misalignment geometry.

The cases here are chosen so the right answer is known in closed form rather
than by comparison against the code's own output: a bore lying on the relative
rotation axis must read exactly zero, a bore perpendicular to it must read
exactly the rotation angle, and a rigid rotation must be recovered exactly.
"""

import numpy as np
import pytest

from kinematics.core.joints import (
    HousingMode,
    RigidBody,
    RotationMode,
    angle_between_deg,
    circle_directions,
    fibonacci_directions,
    kabsch_rotation,
    locked_clocking,
    misalignment_series,
    optimize_bore_axis,
    resolve_body_modes,
    rotation_from_rotvec,
    rotvec_from_rotation,
    transport_rotation,
    unit,
)

CENTRED = HousingMode.CENTRED.value
AUTHORED = HousingMode.AUTHORED.value
INDETERMINATE = HousingMode.INDETERMINATE.value


def rotation(axis, degrees):
    """Build a rotation of ``degrees`` about ``axis``."""
    return rotation_from_rotvec(unit(np.asarray(axis, float)) * np.radians(degrees))


# --------------------------------------------------------------------------
# Rotation primitives
# --------------------------------------------------------------------------
def test_rotvec_round_trips():
    """A rotation survives the rotation-vector encoding exported per joint."""
    original = rotation([0.3, -0.7, 0.4], 23.0)
    assert np.allclose(
        rotation_from_rotvec(rotvec_from_rotation(original)), original, atol=1e-12
    )


def test_kabsch_recovers_a_rigid_rotation_exactly():
    """A body's points move rigidly, so the fit is exact, not approximate."""
    expected = rotation([0.2, 0.5, -0.84], 17.0)
    cloud = np.array([[0.0, 0.0, 0.0], [120.0, 5.0, 0.0], [10.0, 90.0, 30.0]])
    moved = cloud @ expected.T + np.array([17.0, -4.0, 9.0])
    assert np.allclose(kabsch_rotation(cloud, moved), expected, atol=1e-10)


def test_kabsch_rejects_an_underdetermined_fit():
    """Two points fix an axis, not an orientation."""
    cloud = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match="at least three points"):
        kabsch_rotation(cloud, cloud)


def test_transport_adds_no_spin_about_the_link_axis():
    """The two-point convention is zero intrinsic spin, by construction."""
    start = np.array([1.0, 0.2, 0.0])
    end = np.array([0.9, 0.5, 0.3])
    carried = transport_rotation(start, end)
    assert np.allclose(unit(carried @ unit(start)), unit(end), atol=1e-12)
    assert abs(float(np.dot(rotvec_from_rotation(carried), unit(start)))) < 1e-12


# --------------------------------------------------------------------------
# The two limits that define the whole taxonomy
# --------------------------------------------------------------------------
def test_bore_on_the_rotation_axis_needs_no_misalignment():
    """A bore aligned with the relative rotation axis is a pure revolute.

    This is why a wishbone's inboard pivots can be plain bushings.
    """
    axis = unit(np.array([0.2, 0.9, -0.35]))
    stack = np.stack([rotation(axis, angle) for angle in (3.0, 11.0, 27.0)])
    assert np.allclose(misalignment_series(stack, axis, CENTRED), 0.0, atol=1e-9)


def test_bore_perpendicular_absorbs_the_whole_rotation():
    """The opposite limit: the bearing eats the full relative rotation."""
    axis = unit(np.array([0.2, 0.9, -0.35]))
    angles = [3.0, 11.0, 27.0]
    stack = np.stack([rotation(axis, angle) for angle in angles])
    perpendicular = unit(np.cross(axis, np.array([1.0, 0.0, 0.0])))
    assert np.allclose(
        misalignment_series(stack, perpendicular, CENTRED), angles, atol=1e-9
    )


# --------------------------------------------------------------------------
# Housing installed off centre
# --------------------------------------------------------------------------
def test_install_offset_appears_at_the_neutral_pose():
    """An off-centre install is already eating its cone before anything moves."""
    bore = np.array([0.0, 0.0, 1.0])
    housing = rotation([1.0, 0.0, 0.0], 6.0) @ bore
    at_neutral = misalignment_series(
        np.eye(3).reshape(1, 3, 3), bore, AUTHORED, housing_axis=housing
    )
    assert at_neutral[0] == pytest.approx(6.0, abs=1e-9)


def test_pre_tilting_the_housing_halves_a_one_sided_excursion():
    """The design move that installing centred cannot express.

    A bore that swings 0 to 12 degrees one way costs 12 degrees installed
    centred, but only 6 with the housing pre-tilted to the middle of the
    excursion.
    """
    bore = np.array([0.0, 0.0, 1.0])
    housing = rotation([1.0, 0.0, 0.0], 6.0) @ bore
    stack = np.stack([rotation([1.0, 0.0, 0.0], d) for d in (0.0, 6.0, 12.0)])
    centred = misalignment_series(stack, bore, CENTRED).max()
    offset = misalignment_series(stack, bore, AUTHORED, housing_axis=housing).max()
    assert centred == pytest.approx(12.0, abs=1e-9)
    assert offset == pytest.approx(6.0, abs=1e-9)


# --------------------------------------------------------------------------
# Indeterminate housings
# --------------------------------------------------------------------------
def test_spin_about_the_member_axis_is_fully_relieved():
    """A free-spinning member absorbs rotation about its own axis for nothing."""
    link = np.array([0.0, 1.0, 0.0])
    bore = np.array([0.0, 0.0, 1.0])
    stack = np.stack([rotation(link, d) for d in (0.0, 15.0, 40.0)])
    series = misalignment_series(stack, bore, INDETERMINATE, spin_axis=link)
    assert np.allclose(series, 0.0, atol=1e-9)


def test_bore_tilting_toward_the_member_is_not_relieved():
    """The unavoidable part: no clocking or spin removes an out-of-plane tilt."""
    link = np.array([0.0, 1.0, 0.0])
    bore = np.array([0.0, 0.0, 1.0])
    stack = np.stack([rotation([1.0, 0.0, 0.0], d) for d in (0.0, 5.0, 9.0)])
    series = misalignment_series(stack, bore, INDETERMINATE, spin_axis=link)
    assert np.allclose(series, [0.0, 5.0, 9.0], atol=1e-9)


def test_locked_spin_never_undercuts_the_free_spin_bound():
    """A fixed clocking is a restriction, so it can only cost more."""
    link = np.array([0.0, 1.0, 0.0])
    bore = np.array([0.0, 0.0, 1.0])
    stack = np.stack([rotation([1.0, 0.0, 0.0], d) for d in (0.0, 5.0, 9.0)])
    free = misalignment_series(stack, bore, INDETERMINATE, spin_axis=link).max()
    _, locked = locked_clocking(stack, bore, link)
    assert locked >= free - 1e-9


# --------------------------------------------------------------------------
# Optimiser
# --------------------------------------------------------------------------
def test_optimiser_recovers_the_zero_misalignment_axis():
    """With two free degrees of freedom the exact optimum is reachable."""
    stack = np.stack(
        [rotation([1.0, 0.0, 0.0], d) for d in np.linspace(-2.0, 14.0, 40)]
    )
    axis, worst = optimize_bore_axis(stack, CENTRED, samples=8000)
    assert worst < 1e-3
    assert (
        min(
            angle_between_deg(axis, np.array([1.0, 0.0, 0.0])),
            angle_between_deg(axis, np.array([-1.0, 0.0, 0.0])),
        )
        < 0.5
    )


def test_optimiser_beats_a_dense_independent_sample():
    """Guard against an optimiser that returns a plausible non-optimum."""
    stack = np.stack(
        [rotation([0.4, 1.0, 0.2], d) for d in np.linspace(-6.0, 18.0, 30)]
    )
    _, worst = optimize_bore_axis(stack, CENTRED, samples=8000)
    sampled = min(
        misalignment_series(stack, direction, CENTRED).max()
        for direction in fibonacci_directions(4000)
    )
    assert worst <= sampled + 1e-6


def test_optimiser_refines_past_its_own_lattice():
    """Guard the local refinement, which a timid simplex silently disables.

    The lattice alone lands within its own spacing of the optimum. On a joint
    whose best axis is nearly free of misalignment that error is the entire
    answer, so a refinement that cannot move looks like a working optimiser
    while returning a worse axis than a coarse independent sample.
    """
    spin = unit(np.array([0.0, 1.0, 0.0]))
    stack = np.stack(
        [
            rotation([1.0, 0.05, 0.0], d) @ rotation(spin, 0.4 * d)
            for d in np.linspace(-20.0, 20.0, 60)
        ]
    )
    _, worst = optimize_bore_axis(stack, INDETERMINATE, spin_axis=spin)
    sampled = min(
        misalignment_series(stack, direction, INDETERMINATE, spin_axis=spin).max()
        for direction in fibonacci_directions(30000)
    )
    assert worst <= sampled + 1e-9


def test_optimiser_honours_a_perpendicularity_constraint():
    """A rod end's bore cannot leave the circle perpendicular to its shank."""
    pole = unit(np.array([1.0, 0.0, 0.0]))
    stack = np.stack([rotation(pole, d) for d in np.linspace(-2.0, 14.0, 20)])
    axis, worst = optimize_bore_axis(
        stack, CENTRED, perpendiculars=[pole.tolist()], samples=4000
    )
    # The zero-misalignment axis is the pole itself, which the constraint
    # forbids. Every remaining candidate is perpendicular to the pole, so all
    # of them absorb the full relative rotation and the constrained optimum is
    # the largest excursion from the neutral pose -- 14 degrees, not the 16
    # degree peak-to-peak swing. Closing that gap needs an off-centre housing,
    # which is a different declaration, not a better axis.
    assert abs(float(np.dot(axis, pole))) < 1e-6
    assert worst == pytest.approx(14.0, abs=0.05)


def test_two_constraints_pin_the_axis_up_to_sign():
    """Perpendicular to two independent axes leaves only the cross product."""
    from kinematics.core.joints import candidate_axes

    axes = candidate_axes([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    assert axes.shape == (2, 3)
    assert np.allclose(np.abs(axes), np.array([[0.0, 0.0, 1.0]] * 2), atol=1e-12)


def test_circle_directions_lie_on_their_cone():
    """The clocking circle is the set a threaded bearing's bore can occupy."""
    pole = unit(np.array([0.2, -0.9, 0.4]))
    directions, clocking = circle_directions(pole, count=64)
    assert np.allclose(directions @ pole, 0.0, atol=1e-12)
    assert clocking[0] == pytest.approx(0.0)


# --------------------------------------------------------------------------
# Bodies
# --------------------------------------------------------------------------
def test_fitted_body_recovers_its_rotation():
    """Three non-collinear points fully determine an orientation."""
    expected = rotation([0.1, 0.3, 0.95], 9.0)
    neutral = {
        0: np.array([0.0, 0.0, 0.0]),
        1: np.array([100.0, 0.0, 0.0]),
        2: np.array([0.0, 80.0, 0.0]),
    }
    current = {key: expected @ value for key, value in neutral.items()}
    body = RigidBody("arm", (0, 1, 2), RotationMode.FITTED)
    assert np.allclose(body.rotation(neutral, current), expected, atol=1e-10)


def test_ground_body_never_rotates():
    """Chassis-fixed geometry is the reference frame, not a moving body."""
    neutral = {0: np.zeros(3), 1: np.array([1.0, 0.0, 0.0])}
    body = RigidBody("chassis", (0, 1), RotationMode.GROUND)
    assert np.allclose(body.rotation(neutral, neutral), np.eye(3))


def test_collinear_points_demote_to_transport():
    """Three points on one line fix an axis, so fitting them is meaningless."""
    neutral = {
        0: np.array([0.0, 0.0, 0.0]),
        1: np.array([50.0, 0.0, 0.0]),
        2: np.array([100.0, 0.0, 0.0]),
    }
    resolved = resolve_body_modes(
        (RigidBody("rod", (0, 1, 2), RotationMode.FITTED),), neutral
    )
    assert resolved[0].mode is RotationMode.TRANSPORT
    assert len(resolved[0].points) == 2
