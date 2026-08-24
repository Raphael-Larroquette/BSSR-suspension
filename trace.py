import yaml
from kinematics.cli.io.loaders import load_geometry
from kinematics.core.enums import PointID

# 1. What's actually in the YAML file, raw, before Python touches it.
with open("tests/data/geometry.yaml") as f:
    raw = yaml.safe_load(f)
print("RAW YAML VALUE:", raw["hardpoints"]["lower_wishbone_outboard"])

# 2. Load it "for real" — this is the ball joint at the bottom of the upright.
suspension = load_geometry("tests/data/geometry.yaml")
point = suspension.hardpoints[PointID.LOWER_WISHBONE_OUTBOARD]
print("SAME POINT, AS A Point3 OBJECT:", point, type(point))

# 3. Solve it. WHEEL_CENTER isn't in your YAML at all — it gets figured out.
state = suspension.initial_state()
wheel_center = state.get(PointID.WHEEL_CENTER)
print("WHEEL_CENTER, COMPUTED BY THE SOLVER:", wheel_center)