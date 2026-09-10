r"""
Assembly and solution of one subsystem's equilibrium equations.

Every part that is not ground and not a two-force member contributes six rows.
Writing :math:`s_{bj} = \pm 1` for Newton's third law and :math:`\mathbf c_b`
for the part's moment reference:

.. math::

    \sum_j s_{bj}\,\mathbf F_j + \mathbf F^{\text{ext}}_b = \mathbf 0

.. math::

    \sum_j s_{bj}\,(\mathbf r_j - \mathbf c_b) \times \mathbf F_j
      + (\mathbf r^{\text{ext}} - \mathbf c_b) \times \mathbf F^{\text{ext}}_b
      = \mathbf 0

The system is built rectangular and then checked, never assumed square. A model
that is short of equations, or carries a redundancy nothing has closed, stops
here with the offending part named. Falling back to a least-squares solve would
answer a badly posed question with numbers that look entirely reasonable in a
results file.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from kinematics.core.loads.structure import ForceBody
from kinematics.core.loads.unknowns import UnknownCatalog, UnknownKind

# Default relative tolerance for the rank check on the assembled system.
DEFAULT_RANK_TOLERANCE = 1e-9

# Default per-part equilibrium residual, relative to the largest force on it.
DEFAULT_RESIDUAL_TOLERANCE = 1e-8


class MomentReference(StrEnum):
    """Which point a part's moment equations are taken about."""

    CENTROID = "centroid"
    ORIGIN = "origin"
    POINT = "point"


@dataclass(frozen=True)
class SolveOptions:
    """Numerical policy for one force solve."""

    moment_reference: MomentReference = MomentReference.CENTROID
    reference_point: NDArray[np.float64] | None = None
    rank_tolerance: float = DEFAULT_RANK_TOLERANCE
    residual_tolerance: float = DEFAULT_RESIDUAL_TOLERANCE


@dataclass(frozen=True)
class ExternalLoad:
    """One externally applied force, and where on a part it acts."""

    body: str
    name: str
    position: NDArray[np.float64]
    force: NDArray[np.float64]


@dataclass(frozen=True)
class SubsystemSolution:
    """Solved joint forces for one subsystem under one case."""

    catalog: UnknownCatalog
    forces: Mapping[str, NDArray[np.float64]]
    axial: Mapping[str, float]
    condition: float
    residual: float


def skew(vector: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return the matrix that applies a cross product from the left."""
    x, y, z = (float(value) for value in vector)
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def solve_subsystem(
    catalog: UnknownCatalog,
    externals: Sequence[ExternalLoad] = (),
    options: SolveOptions = SolveOptions(),
) -> SubsystemSolution:
    """
    Assemble and solve one subsystem's equilibrium equations.

    Args:
        catalog: The subsystem's unknowns, equation parts, and constraints.
        externals: Forces applied to parts from outside the linkage.
        options: Moment reference and numerical tolerances.

    Returns:
        The solved joint forces, with the condition number and worst residual.

    Raises:
        ValueError: If the system is not square, is rank deficient, or leaves a
            part out of equilibrium by more than the residual tolerance.
    """
    matrix, rhs = assemble(catalog, externals, options)
    _check_square(catalog, matrix)
    _check_rank(catalog, matrix, options.rank_tolerance)

    solution = np.linalg.solve(matrix, rhs)
    condition = float(np.linalg.cond(matrix))

    forces = {
        name: binding.force(solution) for name, binding in catalog.bindings.items()
    }
    axial = {
        unknown.name: float(solution[unknown.start])
        for unknown in catalog.unknowns
        if unknown.kind is UnknownKind.LINK
    }

    scale = max(float(np.max(np.abs(rhs))), 1.0)
    residual = float(np.max(np.abs(matrix @ solution - rhs))) / scale
    if residual > options.residual_tolerance:
        raise ValueError(
            f"Subsystem '{catalog.subsystem.name}' does not satisfy its own "
            f"equilibrium equations: relative residual {residual:.3e} exceeds "
            f"{options.residual_tolerance:.3e}. This should not be reachable and "
            "indicates a bug rather than a modelling choice."
        )

    return SubsystemSolution(
        catalog=catalog,
        forces=forces,
        axial=axial,
        condition=condition,
        residual=residual,
    )


def assemble(
    catalog: UnknownCatalog,
    externals: Sequence[ExternalLoad],
    options: SolveOptions,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Build the coefficient matrix and right-hand side for one subsystem."""
    width = catalog.width
    matrix = np.zeros((catalog.rows, width))
    rhs = np.zeros(catalog.rows)
    applied: dict[str, list[ExternalLoad]] = {}
    for load in externals:
        applied.setdefault(load.body, []).append(load)

    for index, body in enumerate(catalog.equation_bodies):
        reference = moment_reference(catalog, body, options)
        force_rows = slice(6 * index, 6 * index + 3)
        moment_rows = slice(6 * index + 3, 6 * index + 6)

        for joint in catalog.subsystem.joints_on(body.name):
            binding = catalog.bindings[joint.name]
            unknown = binding.unknown
            columns = slice(unknown.start, unknown.start + unknown.width)
            block = joint.sign_for(body.name) * binding.orientation * unknown.basis
            matrix[force_rows, columns] += block
            matrix[moment_rows, columns] += skew(joint.position - reference) @ block

        for load in applied.get(body.name, ()):
            rhs[force_rows] -= load.force
            rhs[moment_rows] -= skew(load.position - reference) @ load.force

    for offset, constraint in enumerate(catalog.constraints):
        matrix[6 * len(catalog.equation_bodies) + offset, :] = constraint.row

    return matrix, rhs


def moment_reference(
    catalog: UnknownCatalog,
    body: ForceBody,
    options: SolveOptions,
) -> NDArray[np.float64]:
    """
    Return the point one part's moment equations are taken about.

    Every choice is mathematically equivalent given the force rows, but not
    numerically: a part whose joints sit two metres from the global origin has
    moment rows three orders of magnitude larger than its force rows, and the
    assembled system is conditioned accordingly. The default puts the reference
    inside the part.
    """
    if options.moment_reference is MomentReference.ORIGIN:
        return np.zeros(3)
    if options.moment_reference is MomentReference.POINT:
        if options.reference_point is None:
            raise ValueError(
                "moment_reference 'point' needs an explicit reference_point."
            )
        return options.reference_point
    joints = catalog.subsystem.joints_on(body.name)
    return np.mean([joint.position for joint in joints], axis=0)


def _check_square(catalog: UnknownCatalog, matrix: NDArray[np.float64]) -> None:
    """Require as many equations as unknowns, naming what is out of balance."""
    rows, columns = matrix.shape
    if rows == columns:
        return
    summary = ", ".join(
        f"'{body.name}' ({len(catalog.subsystem.joints_on(body.name))} joints)"
        for body in catalog.equation_bodies
    )
    shortfall = "more unknowns than equations" if columns > rows else "over-constrained"
    raise ValueError(
        f"Subsystem '{catalog.subsystem.name}' is {shortfall}: {rows} equations "
        f"against {columns} unknowns. Parts contributing equations: {summary}. "
        f"Two-force members: "
        f"{', '.join(repr(body.name) for body in catalog.two_force_bodies) or 'none'}."
    )


def _check_rank(
    catalog: UnknownCatalog,
    matrix: NDArray[np.float64],
    tolerance: float,
) -> None:
    """Require a full-rank system, pointing at the redundancy when short."""
    singular = np.linalg.svd(matrix, compute_uv=False)
    if singular[-1] > tolerance * singular[0]:
        return
    pairs = "; ".join(pair.describe() for pair in catalog.coaxial) or "none found"
    raise ValueError(
        f"Subsystem '{catalog.subsystem.name}' is rank deficient: the equilibrium "
        "equations do not determine every unknown. Coaxial joint pairs and the "
        f"policy applied to each: {pairs}. Set 'solve.pivot_axial' in forces.yaml "
        "to close the redundancy."
    )
