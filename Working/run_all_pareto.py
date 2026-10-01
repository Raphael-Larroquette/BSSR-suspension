import subprocess

for i in range(1, 88):  # Loops from pareto1 to pareto87
    geometry_path = f"Working\\models\\pareto{i}\\front.yaml"

    cmd = [
        "uv",
        "run",
        "python",
        "Working/run_all.py",
        "--sets",
        "front",
        "--geometry",
        geometry_path,
        "--only",
        "01, 02",  # Change to "01" if you only want 01
        "--no-forces",
    ]

    print(f"\n--- Running Pareto {i}/87 ---")
    print("Executing:", " ".join(cmd))

    # Run the command and wait for it to finish
    subprocess.run(cmd, check=True)

print("\nAll Pareto runs completed successfully!")