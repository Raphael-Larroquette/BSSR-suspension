import sys, yaml
from pathlib import Path
from kinematics.core.input import build_suspension

data = yaml.safe_load(Path(sys.argv[1]).read_text())
susp = build_suspension(data)
print("built OK:", susp.name)