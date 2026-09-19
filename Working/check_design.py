import optimizer
from opt.evaluate import evaluate

print("Evaluating KNOWN_DESIGN from optimizer.py...")
result = evaluate(optimizer.KNOWN_DESIGN)

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
