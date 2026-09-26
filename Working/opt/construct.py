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
