r"""
Load case to tyre contact-patch forces.

With three contact patches the vertical distribution is statically
determinate: three unknown normal loads against vertical force equilibrium and
the two ground-plane moment equations. No roll-stiffness split is needed or
assumed, and the result reproduces the classical transfer formulas
:math:`\Delta W_x = hWA_x/l` and :math:`\Delta W_y = hWA_y/t` exactly while
also picking up a laterally offset centre of gravity, which those formulas
cannot express.

Horizontal force is then shared out in proportion to normal load, which is the
same statement as one friction coefficient for every tyre.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from kinematics.core.loads.cases import LoadCase
from kinematics.core.loads.vehicle import ContactPatch, VehicleModel

# Singular-value ratio below which the contact patches are treated as
# collinear, leaving the ground-plane moment equations degenerate.
PATCH_CONDITION_LIMIT = 1e-9


@dataclass(frozen=True)
class PatchLoad:
    """
    The force the road applies to one tyre for one case, in vehicle axes.

    ``lifted`` marks a normal load that has gone negative, meaning the vehicle
    is past its tip-over threshold for this case. The value is kept rather than
    clamped: it leaves a conservative load on the corners that are still
    down, and the flag is what says the lifted corner's own numbers describe a
    tyre pulling on the road and must not be used.
    """

    patch: ContactPatch
    force: NDArray[np.float64]

    @property
    def normal(self) -> float:
        """Return the vertical component of the contact force."""
        return float(self.force[2])

    @property
    def lifted(self) -> bool:
        """Whether this wheel has left the road under this case."""
        return self.normal < 0.0


def solve_patch_loads(
    vehicle: VehicleModel,
    case: LoadCase,
) -> tuple[PatchLoad, ...]:
    """
    Solve the contact-patch force at every wheel for one load case.

    Args:
        vehicle: The composed vehicle.
        case: The load case to solve.

    Returns:
        One patch load per contact patch, in vehicle contact-patch order.

    Raises:
        ValueError: If the vehicle does not have exactly three contact patches,
            or if those patches are collinear.
    """
    patches = vehicle.patches
    if len(patches) != 3:
        raise ValueError(
            f"The vertical load distribution is implemented for three contact "
            f"patches and this vehicle has {len(patches)}. With four the split is "
            "indeterminate by one and needs a roll-stiffness distribution between "
            "the axles, which needs spring and anti-roll rates this solver does "
            "not model. See 'Limitations' in docs/force.md."
        )

    longitudinal, lateral, vertical = case.accelerations
    weight = vehicle.weight
    total_normal = vertical * weight
    height = float(vehicle.cg[2])

    # Each patch's horizontal force is a fixed multiple of its own normal load,
    # so the moment equations stay linear in the three unknowns even though the
    # contact patches do not sit exactly on z = 0.
    longitudinal_share = -longitudinal / vertical
    lateral_share = -lateral / vertical

    # Moment of one patch force about the origin, per unit of its normal load:
    #   (r x F)_x = y N - z F_y = N (y - z * lateral_share)
    #   (r x F)_y = z F_x - x N = -N (x - z * longitudinal_share)
    matrix = np.zeros((3, 3))
    for column, patch in enumerate(patches):
        x, y, z = (float(value) for value in patch.position)
        matrix[0, column] = 1.0
        matrix[1, column] = y - z * lateral_share
        matrix[2, column] = -(x - z * longitudinal_share)

    singular = np.linalg.svd(matrix, compute_uv=False)
    if singular[-1] <= PATCH_CONDITION_LIMIT * singular[0]:
        names = ", ".join(patch.name for patch in patches)
        raise ValueError(
            f"The contact patches ({names}) are collinear, so the ground-plane "
            "moment equations do not determine the normal loads."
        )

    rhs = np.array(
        [
            total_normal,
            float(vehicle.cg[1]) * total_normal + height * lateral * weight,
            -float(vehicle.cg[0]) * total_normal - height * longitudinal * weight,
        ]
    )
    normals = np.linalg.solve(matrix, rhs)

    return tuple(
        PatchLoad(
            patch=patch,
            force=np.array(
                [
                    normal * longitudinal_share,
                    normal * lateral_share,
                    normal,
                ]
            ),
        )
        for patch, normal in zip(patches, normals)
    )
