import copy
import yaml
from pathlib import Path
from kinematics.core.input import build_suspension, build_sweep
from kinematics.core.analysis import analyze_sweep

# Load the base template once
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "models" / "aurora" / "front.yaml"
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    TEMPLATE = yaml.safe_load(f)

def solve_stage(hardpoints_dict, required_sweeps):
    import optimizer
    data = copy.deepcopy(TEMPLATE)
    if "hardpoints" not in data:
        data["hardpoints"] = {"left": {}}
    if "left" not in data["hardpoints"]:
        data["hardpoints"]["left"] = {}
        
    for hp_name, coords in hardpoints_dict.items():
        if hp_name not in data["hardpoints"]["left"]:
            data["hardpoints"]["left"][hp_name] = {}
        data["hardpoints"]["left"][hp_name].update(coords)
        
    suspension = build_suspension(data)
    
    out = {}
    sweep_dir = Path(__file__).resolve().parent.parent / "sweep_sets" / "front" / "sweeps"
    for sweep_name in required_sweeps:
        sweep_path = sweep_dir / f"{sweep_name}.yaml"
        with open(sweep_path, "r", encoding="utf-8") as f:
            sweep_spec = yaml.safe_load(f)
            
        if hasattr(optimizer, "SWEEP_LIMITS") and sweep_name in optimizer.SWEEP_LIMITS:
            limits = optimizer.SWEEP_LIMITS[sweep_name]
            for target in sweep_spec.get("targets", []):
                if target.get("start") != target.get("stop"):
                    target["start"] = limits["start"]
                    target["stop"] = limits["stop"]
            
        out[sweep_name] = analyze_sweep(suspension, build_sweep(sweep_spec, suspension))
        
    return out
