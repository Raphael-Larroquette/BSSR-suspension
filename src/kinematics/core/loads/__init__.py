"""
Static suspension force solve.

Takes a vehicle built from geometry files and a set of load cases, and returns
the force at every suspension joint. See ``docs/force.md`` for the conventions,
the method, and the assumptions the result rests on.
"""

from kinematics.core.loads.cases import LoadCase
from kinematics.core.loads.distribution import PatchLoad, solve_patch_loads
from kinematics.core.loads.main import ForceRun, solve_forces
from kinematics.core.loads.results import ForceSolution, JointLoad, PartCaseLoads
from kinematics.core.loads.structure import (
    DEFAULT_STRUCTURE,
    ForceBody,
    ForceGraph,
    ForceJoint,
    StructurePolicy,
    Subsystem,
    build_force_graph,
)
from kinematics.core.loads.unknowns import CoaxialPair, UnknownCatalog, build_unknowns
from kinematics.core.loads.vehicle import ContactPatch, VehicleModel, build_vehicle
