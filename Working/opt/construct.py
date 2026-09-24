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
# Spring mounts inside the UCA-LCA prism
# ==========================================================================
# The LCA's three hardpoints (inboard front, inboard rear, ball joint) and the
# UCA's three form two triangles. Joining matching vertices (front-front,
# rear-rear, ball joint-ball joint) sweeps out a triangular prism, twisted in
# general because the two triangles are not parallel. Both spring mounts must
# lie inside it, and they share one x coordinate.
#
# Rather than bound the mounts with an absolute box and reject whatever falls
# outside (about 1% of a box's volume is prism, so ~99% of samples would be
# wasted), each mount is placed with fractions that can only land inside:
#
#   h  height through the prism: 0 = on the LCA triangle, 1 = on the UCA one.
#      The cross-section at h is the triangle (1-h)*LCA + h*UCA, vertex by
#      vertex, which is exactly the "connect the vertices" volume.
#      The LCA mount takes h directly. The chassis mount is never below it:
#      its "rise" fraction spans what is left above the LCA mount, so
#      h_top = h_bottom + rise * (1 - h_bottom). An upside-down spring
#      (chassis mount under the LCA mount) extends in bump and gives a
#      negative motion ratio; before this ordering about half of all random
#      spring placements were that, and every one of them was wasted.
#   x  one shared fraction across the x span BOTH mounts' cross-sections
#      cover: 0 = rearmost x where both exist, 1 = frontmost.
#   w  across the cross-section at that x, which is a line segment:
#      0 = its most inboard end (smallest y), 1 = its most outboard end.
#
# So every candidate is geometrically valid by construction, and the five
# numbers (x, rise_top, w_top, h_bottom, w_bottom) are all 0-1.


def top_height(h_bottom, rise):
    """Chassis-mount height fraction: `rise` of the way from the LCA mount to the UCA."""
    return h_bottom + rise * (1.0 - h_bottom)


def _section(lca, uca, h):
    """The prism's cross-section at height fraction h: a triangle, 3x3."""
    return (1.0 - h) * _np.asarray(lca, float) + h * _np.asarray(uca, float)


def _cut_at_x(tri, x):
    """Where the plane at this x crosses a triangle: (inboard end, outboard end)."""
    pts = []
    for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
        da, db = a[0] - x, b[0] - x
        if abs(da) < 1e-9:
            pts.append(a)
        if abs(db) < 1e-9:
            pts.append(b)
        if da * db < 0.0:
            t = da / (da - db)
            pts.append(a + t * (b - a))
    if not pts:
        raise ValueError(f"x = {x:.3f} does not cross the prism section")
    pts = sorted(pts, key=lambda p: p[1])
    return pts[0], pts[-1]


def spring_mounts(lca, uca, x_frac, top, bottom):
    """
    Place both spring mounts inside the UCA-LCA prism.

    Args:
        lca, uca: three xyz points each, in the order
            (inboard front, inboard rear, outboard ball joint).
        x_frac: shared x fraction, 0-1.
        top, bottom: (h_frac, w_frac) for the chassis and LCA mounts.

    Returns:
        (top_xyz, bottom_xyz) as numpy arrays.
    """
    sec_top = _section(lca, uca, top[0])
    sec_bot = _section(lca, uca, bottom[0])
    x_lo = max(sec_top[:, 0].min(), sec_bot[:, 0].min())
    x_hi = min(sec_top[:, 0].max(), sec_bot[:, 0].max())
    if x_hi < x_lo:
        raise ValueError(
            "the two spring-mount sections share no x range, so no pair of "
            "mounts at one x fits inside the prism"
        )
    x = x_lo + x_frac * (x_hi - x_lo)
    out = []
    for sec, (_, w) in ((sec_top, top), (sec_bot, bottom)):
        inner, outer = _cut_at_x(sec, x)
        out.append(inner + w * (outer - inner))
    return out[0], out[1]


def spring_fractions(lca, uca, top_xyz, bottom_xyz, grid=21):
    """
    Invert spring_mounts: the fractions that best reproduce two absolute mounts.

    For seeding the search with a known design. A mount outside the prism has
    no exact fractions; the nearest in-prism pair is returned, and the miss in
    mm is reported so the caller can say so.

    Returns:
        (fractions dict, worst miss in mm)
    """
    from scipy.optimize import minimize

    top_xyz = _np.asarray(top_xyz, float)
    bottom_xyz = _np.asarray(bottom_xyz, float)

    def place(v):
        # v = (x, rise_top, w_top, h_bottom, w_bottom), as the optimiser sees them
        return spring_mounts(lca, uca, v[0], (top_height(v[3], v[1]), v[2]),
                             (v[3], v[4]))

    def miss(v):
        v = _np.clip(v, 0.0, 1.0)
        try:
            t, b = place(v)
        except ValueError:
            return 1e9
        return float(_np.sum((t - top_xyz) ** 2) + _np.sum((b - bottom_xyz) ** 2))

    best = None
    rng = _np.random.default_rng(0)
    for start in rng.uniform(0.0, 1.0, size=(grid, 5)):
        res = minimize(miss, start, method="Nelder-Mead",
                       options={"xatol": 1e-6, "fatol": 1e-6, "maxiter": 4000})
        if best is None or res.fun < best.fun:
            best = res
    v = _np.clip(best.x, 0.0, 1.0)
    t, b = place(v)
    worst = max(_np.linalg.norm(t - top_xyz), _np.linalg.norm(b - bottom_xyz))
    names = ("spring.x_frac", "strut_top.rise_frac", "strut_top.w_frac",
             "strut_bottom.h_frac", "strut_bottom.w_frac")
    return dict(zip(names, map(float, v))), float(worst)
