"""
Evaluate an optimizer script's KNOWN_DESIGN seed, exactly as the search would.

    uv run python Working/check_design.py                              optimizer.py
    uv run python Working/check_design.py Working/underlegoptimizer.py another script
"""

import sys
from pathlib import Path

from opt.evaluate import evaluate, fixed_params
from opt.settings import activate, relative_to_working, template_dir

DEFAULT_SCRIPT = Path(__file__).with_name("optimizer.py")
script = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SCRIPT
settings = activate(script)

# KNOWN_DESIGN holds absolute spring mounts; the evaluator wants prism fractions.
settings.resolve_spring_seed(fixed_params())

print(f"Evaluating KNOWN_DESIGN from {script.name} "
      f"(template {relative_to_working(template_dir())})...")
result = evaluate(settings.KNOWN_DESIGN)

if not result.feasible:
    print(f"FAILED: {result.failure}")
    if result.diagnostics:
        print("\nDiagnostics:")
        for d in result.diagnostics:
            print(d)
else:
    print("SUCCESS! Outcomes:")
    for k, v in result.outcomes.items():
        print(f"  {k}: {v}")
