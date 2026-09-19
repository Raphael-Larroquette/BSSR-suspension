import math
import numpy as np

def travel_integral(analysis, key: str, bump_weight: float = 1.5) -> float:
    travel = np.array([list(f.corner_metrics.values())[0]["wheel_travel"] for f in analysis.frames])
    value  = np.array([list(f.corner_metrics.values())[0][key] for f in analysis.frames])
    
    order = np.argsort(travel)
    travel, value = travel[order], value[order]

    design = float(list(analysis.references["setup"].corner_metrics.values())[0][key])
    weight = np.where(travel >= 0.0, bump_weight, 1.0)
    
    integral = float(np.trapezoid(np.abs(value - design) * weight, travel))
    span = travel[-1] - travel[0]
    return integral / span if span > 0 else 0.0

def reduce_outcomes(analyses, objectives_cfg, constraints_cfg, bump_weight):
    outcomes = {}
    
    for obj_name, (sweep_name, metric, sense) in objectives_cfg.items():
        if sweep_name not in analyses:
            continue
        analysis = analyses[sweep_name]
        
        if metric == "bump_steer":
            outcomes[obj_name] = travel_integral(analysis, "toe_angle", bump_weight)
        elif metric == "bump_scrub":
            outcomes[obj_name] = travel_integral(analysis, "half_track", bump_weight)
        else:
            try:
                outcomes[obj_name] = float(list(analysis.references["setup"].corner_metrics.values())[0][metric])
            except KeyError:
                outcomes[obj_name] = float(analysis.references["setup"].metrics[metric])
                
    for const_name, (sweep_name, metric, bounds) in constraints_cfg.items():
        if sweep_name not in analyses:
            continue
        analysis = analyses[sweep_name]
        
        if metric == "ackermann":
            try:
                f = analysis.frames[-1]
                vals = list(f.corner_metrics.values())
                steer_l = vals[0]["steer_angle"]
                steer_r = vals[1]["steer_angle"]
                wheelbase = 2240.0
                track = f.metrics.get("track", 1000.0)
                inner = max(abs(steer_l), abs(steer_r))
                outer = min(abs(steer_l), abs(steer_r))
                ideal_delta = math.degrees(math.atan(wheelbase / (wheelbase / math.tan(math.radians(outer)) - track))) - outer if outer > 0 else 0
                actual_delta = inner - outer
                pct = (actual_delta / ideal_delta * 100.0) if ideal_delta > 0.25 else 100.0
                outcomes[const_name] = abs(pct - 100.0)
            except Exception:
                outcomes[const_name] = 0.0

        elif metric == "max_turn":
            toes = [list(f.corner_metrics.values())[0]["toe_angle"] for f in analysis.frames]
            outcomes[const_name] = min(abs(max(toes)), abs(min(toes)))
            
        else:
            try:
                outcomes[const_name] = float(list(analysis.references["setup"].corner_metrics.values())[0][metric])
            except KeyError:
                outcomes[const_name] = float(analysis.references["setup"].metrics[metric])
                
    return outcomes
