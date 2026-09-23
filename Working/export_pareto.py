import csv
import shutil
import yaml
import re
from pathlib import Path
import optimizer

def main():
    model_src = Path("Working/models") / optimizer.CAR_NAME
    models_dir = Path("Working/models")
    csv_path = Path("Working/opt_pareto.csv")

    if not csv_path.exists():
        print(f"Error: {csv_path} not found. Please run the optimizer first.")
        return

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("CSV is empty.")
        return

    for i, row in enumerate(rows):
        pareto_name = f"pareto{i+1}"
        pareto_dir = models_dir / pareto_name
        
        # Clean and copy folder
        if pareto_dir.exists():
            shutil.rmtree(pareto_dir)
        shutil.copytree(model_src, pareto_dir)
        
        # Load the front.yaml
        front_yaml_path = pareto_dir / "front.yaml"
        with open(front_yaml_path, "r", encoding="utf-8") as f:
            lines = f.read().split('\n')
            
        # Extract new hardpoints from the CSV row
        new_hps = {}
        for col_name, value_str in row.items():
            if "." in col_name and not col_name.endswith("_frac"):
                try:
                    val = round(float(value_str), 3)
                except ValueError:
                    continue
                hp_name, axis = col_name.split(".")
                if hp_name not in new_hps:
                    new_hps[hp_name] = {}
                new_hps[hp_name][axis] = val

        # Replace matching lines in front.yaml
        for idx, line in enumerate(lines):
            match = re.match(r'^(\s*)([a-zA-Z0-9_]+):\s*\{(.*)\}(.*)$', line)
            if match:
                indent = match.group(1)
                hp_name = match.group(2)
                inner_content = match.group(3)
                comment = match.group(4)
                
                if hp_name in new_hps:
                    try:
                        coords = yaml.safe_load("{" + inner_content + "}")
                        # Update the coordinates with the new optimized ones
                        for axis, val in new_hps[hp_name].items():
                            coords[axis] = val
                        
                        # Reconstruct string
                        new_inner = ", ".join(f"{k}: {v}" for k, v in coords.items())
                        lines[idx] = f"{indent}{hp_name}: {{{new_inner}}}{comment}"
                    except Exception:
                        pass
                        
            # Update the name of the car so it shows up cleanly in the solver
            if line.startswith("name: "):
                lines[idx] = f'name: "Pareto {i+1} Optimized Geometry"'

        # Save it back
        with open(front_yaml_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
            
        print(f"Successfully generated {pareto_name} (updated {len(new_hps)} hardpoints).")
        
    print("\nDone! You can now run the solver on any of these folders (e.g. models/pareto1).")

if __name__ == "__main__":
    main()
