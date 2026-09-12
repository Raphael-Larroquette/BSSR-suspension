"""
Load cases: the acceleration triples a static force solve is run for.

A case is three numbers in g, and the sign of each one is a convention rather
than a derivation, so it is stated here once and referred to everywhere else.
"""

from __future__ import annotations

from dataclasses import dataclass


def format_g(value: float) -> str:
    """Render a load factor the way it was authored, without trailing zeros."""
    if value == int(value):
        return str(int(value))
    return f"{value:g}"


@dataclass(frozen=True)
class LoadCase:
    r"""
    One ``(bump, brake, corner)`` acceleration triple, in g.

    ``bump`` is the **total** vertical load factor with gravity included, so
    ``1`` is the static condition and the value must be positive. A case with
    no vertical load has no meaningful solution: every tyre normal load is
    zero, and the horizontal forces then have nothing to be distributed in
    proportion to.

    ``brake`` is positive for deceleration. The d'Alembert inertial force at
    the centre of gravity therefore points forwards (+X), load transfers to the
    front, and the contact-patch force on the vehicle points rearwards. A
    negative value is acceleration.

    ``corner`` is positive when the inertial force at the centre of gravity
    points to the left (+Y), which is a right-hand turn. Load transfers to the
    left-hand wheels and the contact-patch force points to the right.
    """

    bump: float
    brake: float
    corner: float

    def __post_init__(self) -> None:
        """Reject a case with no vertical load."""
        if not self.bump > 0.0:
            raise ValueError(
                f"Load case bump factor must be greater than zero, got "
                f"{format_g(self.bump)}. 'bump' is a total vertical load factor "
                "including gravity, so 1 is the static condition and 0 would "
                "leave every tyre unloaded."
            )

    @property
    def label(self) -> str:
        """Return the case as it is written in a case file."""
        return f"{format_g(self.bump)},{format_g(self.brake)},{format_g(self.corner)}"

    @property
    def accelerations(self) -> tuple[float, float, float]:
        """Return the case as ``(Ax, Ay, Az)`` in vehicle axes."""
        return self.brake, self.corner, self.bump
