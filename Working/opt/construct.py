import numpy as _np


def expand_hardpoints(flat_params):
    """
    Takes a dictionary with dot-separated keys like 'lower_wishbone_outboard.x'
    and returns a nested dictionary of hardpoints.
    """
    hardpoints = {}
    for key, val in flat_params.items():
        parts = key.split('.')
        if len(parts) == 2:
            hp, coord = parts
            if hp not in hardpoints:
                hardpoints[hp] = {}
            hardpoints[hp][coord] = float(val)
    return hardpoints


# ==========================================================================
# Spring mounts
# ==========================================================================
# Defined at design height only; after that the LCA mount moves with the LCA
# and the chassis mount stays put.
#
# LCA mount (strut_bottom): inside the vertical prism made by extruding the
# LCA triangle (ball joint, inboard front, inboard rear) straight up in +z,
# `height` mm above the LCA plane, measured vertically. Its plan position is
# two 0-1 fractions that can only land inside the triangle:
#
#   u  0 = at the ball joint, 1 = on the inboard pivot axis. Area-uniform:
#      the distance fraction from the ball joint is sqrt(u), so every part of
#      the triangle is sampled equally often instead of crowding the ball
#      joint corner.
#   v  0 = front pivot side, 1 = rear pivot side, across the triangle at u.
#
#   P = (1 - s) BJ + s ((1 - v) FRONT + v REAR),  s = sqrt(u)
#
# The same weights applied to the vertex z values give the LCA plane's height
# at that point, and `height` is added on top.
#
# Chassis mount (strut_top): same x as the LCA mount, y and z free inside the
# FREE_PARAMETERS box. Nothing here stops it being too close to the LCA
# mount; that is the pre-solve shock length check in evaluate.py.


def _weights(u, v):
    s = _np.sqrt(u)
    return _np.array([1.0 - s, s * (1.0 - v), s * v])


def strut_bottom_point(lca, u, v, height):
    """
    LCA spring mount at design height.

    Args:
        lca: the LCA triangle as (inboard front, inboard rear, ball joint) xyz.
        u, v: plan-position fractions, see above.
        height: mm above the LCA plane, measured along +z.
    """
    front, rear, bj = (_np.asarray(p, float) for p in lca)
    point = _weights(u, v) @ _np.array([bj, front, rear])
    point[2] += height
    return point


def strut_bottom_fractions(lca, point):
    """
    Invert strut_bottom_point: (u, v, height) for an absolute LCA mount.

    For seeding the search with a known design. A mount outside the triangle
    in plan has no exact fractions; it is clamped to the nearest edge and the
    plan miss in mm is returned so the caller can say so.

    Returns:
        (u, v, height, plan miss in mm)
    """
    front, rear, bj = (_np.asarray(p, float) for p in lca)
    point = _np.asarray(point, float)
    # Solve point_xy = bj + a (front - bj) + b (rear - bj) in plan.
    m = _np.column_stack([(front - bj)[:2], (rear - bj)[:2]])
    a, b = _np.linalg.solve(m, (point - bj)[:2])
    a, b = max(a, 0.0), max(b, 0.0)
    s = a + b
    if s > 1.0:
        a, b, s = a / s, b / s, 1.0
    v = b / s if s > 1e-12 else 0.0
    u = s * s
    on_plane = _weights(u, v) @ _np.array([bj, front, rear])
    miss = float(_np.linalg.norm(on_plane[:2] - point[:2]))
    return float(u), float(v), float(point[2] - on_plane[2]), miss


# ==========================================================================
# Inner tie rod point for zero bump steer
# ==========================================================================
# Front view. The LCA and UCA pivot about axes parallel to x (front and rear
# inboard pivots share y and z), so with the steering held still the upright
# moves only in the y-z plane: a four-bar of chassis, LCA, upright and UCA,
# whose arms meet at the front-view instant centre (FVIC).
#
# The tie rod's outer joint O rides on the upright, so it traces a curve in y-z
# as the wheel moves. The tie rod's inner joint I is fixed to the chassis, so O
# can only move on a circle about I (the tie rod's x span never changes, so its
# front-view length is constant too). Zero bump steer means O's curve and
# that circle are the same curve - then the tie rod never has to push or pull
# the steering arm, and the upright never rotates about the kingpin.
#
#   1. Solve the four-bar at full droop, design height and full bump (the
#      wheel centre moved by the sweep's travel), carrying O along.
#   2. I = centre of the circle through those three positions of O.
#
# Toe is then identical at all three and very small in between. The tie rod
# line O-I also points at the FVIC to within about a millimetre: that is the
# classic "tie rod through the instant centre" rule, and it falls out of this
# automatically. What this adds is the tie rod LENGTH. The textbook rule for
# length (inner joint on the line through the inboard pivots) only holds when
# O sits on the line through the ball joints; ours sits 60-100 mm inboard of
# it, where that rule gives several degrees of toe change.


def _rotate2(v, angle):
    c, s = _np.cos(angle), _np.sin(angle)
    return _np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


def _circle_centre(p1, p2, p3):
    (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
    m = _np.array([[x2 - x1, y2 - y1], [x3 - x1, y3 - y1]])
    rhs = 0.5 * _np.array([x2**2 - x1**2 + y2**2 - y1**2,
                           x3**2 - x1**2 + y3**2 - y1**2])
    if abs(_np.linalg.det(m)) < 1e-9:
        raise ValueError("outer tie rod point moves in a straight line; no finite tie rod fits")
    return _np.linalg.solve(m, rhs)


def trackrod_inboard_yz(lca_inboard, lca_outboard, uca_inboard, uca_outboard,
                        trackrod_outboard, wheel_centre, travel):
    """
    Inner tie rod (y, z) for zero toe at droop, design and bump.

    Args:
        *_inboard, *_outboard: 3D hardpoints; only y and z are used.
        wheel_centre: 3D wheel centre at design height.
        travel: (droop, bump) wheel-centre z change in mm, e.g. (-50.8, 50.8).

    Raises:
        ValueError: if the linkage cannot reach the travel, or O's path is
            straight. The candidate is then reported as a construct failure.
    """
    from scipy.optimize import brentq

    yz = lambda p: _np.asarray(p, float)[1:3]
    a, b = yz(lca_inboard), yz(uca_inboard)
    p0, q0, o0, w0 = (yz(p) for p in (lca_outboard, uca_outboard,
                                      trackrod_outboard, wheel_centre))
    r_lca, r_uca = _np.linalg.norm(p0 - a), _np.linalg.norm(q0 - b)
    upright = _np.linalg.norm(q0 - p0)
    theta0 = _np.arctan2(*(p0 - a)[::-1])

    def pose(theta):
        """Upright at LCA angle theta: returns (O, wheel centre) in y-z."""
        p = a + r_lca * _np.array([_np.cos(theta), _np.sin(theta)])
        d = _np.linalg.norm(b - p)
        along = (upright**2 - r_uca**2 + d**2) / (2 * d)
        across = upright**2 - along**2
        if across < 0:
            raise ValueError("four-bar cannot assemble")
        mid = p + along * (b - p) / d
        n = _np.array([-(b - p)[1], (b - p)[0]]) / d
        q = min((mid + _np.sqrt(across) * n, mid - _np.sqrt(across) * n),
                key=lambda c: _np.linalg.norm(c - q0))      # same branch as design
        turn = _np.arctan2(*(q - p)[::-1]) - _np.arctan2(*(q0 - p0)[::-1])
        return (p + _rotate2(o0 - p0, turn), p + _rotate2(w0 - p0, turn))

    def o_at(dz):
        """O when the wheel centre has moved dz in z. Walks the LCA angle out
        in small steps until the target is bracketed, so it never asks the
        four-bar for a pose it cannot assemble."""
        f = lambda t: pose(t)[1][1] - w0[1] - dz
        step = 0.005 if pose(theta0 + 1e-4)[1][1] > w0[1] else -0.005
        if dz < 0:
            step = -step
        lo, f_lo = theta0, -dz
        for _ in range(400):                      # up to 2 rad of arm rotation
            hi = lo + step
            try:
                f_hi = f(hi)
            except ValueError:
                break
            if f_lo * f_hi <= 0:
                return pose(brentq(f, min(lo, hi), max(lo, hi)))[0]
            lo, f_lo = hi, f_hi
        raise ValueError(f"linkage cannot reach {dz:+.1f} mm of travel")

    droop, bump = travel
    return _circle_centre(o_at(droop), o0, o_at(bump))
