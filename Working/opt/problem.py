from multiprocessing.pool import Pool
from pathlib import Path

import numpy as np
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.core.callback import Callback
from pymoo.core.problem import ElementwiseProblem, StarmapParallelization
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions
from scipy.stats import qmc

from .evaluate import evaluate, write_log_rows

FAIL = 1.0e6


class SuspensionProblem(ElementwiseProblem):
    def __init__(self, **kwargs):
        import optimizer

        self.names = list(optimizer.FREE_PARAMETERS.keys())

        self.obj_names = list(optimizer.OBJECTIVES.keys())
        self.constr_names = list(optimizer.CONSTRAINTS.keys())

        xl = np.array([optimizer.FREE_PARAMETERS[n][0] for n in self.names])
        xu = np.array([optimizer.FREE_PARAMETERS[n][1] for n in self.names])

        super().__init__(
            n_var=len(self.names),
            n_obj=len(self.obj_names),
            n_ieq_constr=len(self.constr_names) * 2,
            xl=xl,
            xu=xu,
            **kwargs,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        import optimizer

        params = dict(zip(self.names, map(float, x)))
        result = evaluate(params)

        if not result.feasible:
            out["F"] = np.full(self.n_obj, FAIL)
            out["G"] = np.full(self.n_ieq_constr, FAIL)
            return

        F = []
        for obj_name in self.obj_names:
            sweep, metric, sense = optimizer.OBJECTIVES[obj_name]
            val = result.outcomes.get(obj_name, FAIL)
            if sense == "maximize":
                F.append(-val)
            else:
                F.append(val)
        out["F"] = np.array(F)

        G = []
        for const_name in self.constr_names:
            sweep, metric, bounds = optimizer.CONSTRAINTS[const_name]
            val = result.outcomes.get(const_name, FAIL)
            if bounds:
                low, high = bounds
                g1 = low - val if low is not None else -FAIL
                g2 = val - high if high is not None else -FAIL
            else:
                g1 = g2 = -FAIL
            G.extend([g1, g2])

        out["G"] = np.array(G)


class LogGeneration(Callback):
    def __init__(self, log_path):
        super().__init__()
        self.log_path = log_path

    def notify(self, algorithm):
        evals = []
        for ind in algorithm.pop:
            if False:
                evals.append(ind.get("eval"))
        if evals:
            write_log_rows(evals, algorithm.n_gen, self.log_path)


def run_pymoo():
    import optimizer

    pool = Pool()
    runner = StarmapParallelization(pool.starmap)
    problem = SuspensionProblem(elementwise_runner=runner)

    pop_size = optimizer.POPULATION_SIZE
    n_gen = optimizer.GENERATIONS

    sobol = qmc.Sobol(d=problem.n_var, scramble=True, seed=0)
    initial = qmc.scale(sobol.random(pop_size), problem.xl, problem.xu)

    if hasattr(optimizer, "KNOWN_DESIGN"):
        # Put known design in initial population
        known = np.array([optimizer.KNOWN_DESIGN[n] for n in problem.names])
        initial[0] = known

    # Always use NSGA-III per user request, scaling the partitions based on objective count
    partitions = {2: 100, 3: 12, 4: 8, 5: 6}.get(problem.n_obj, 5)
    ref_dirs = get_reference_directions(
        "das-dennis", problem.n_obj, n_partitions=partitions
    )
    algorithm = NSGA3(pop_size=pop_size, ref_dirs=ref_dirs, sampling=initial)

    log_path = Path("Working/opt_log.csv")
    callback = LogGeneration(log_path)

    res = minimize(
        problem,
        algorithm,
        termination=("n_gen", n_gen),
        seed=1,
        save_history=False,
        verbose=True,
        callback=callback,
    )

    pool.close()

    print("Pareto Front found:")
    print(res.F)

    if res.F is not None:
        import csv

        from .evaluate import FIXED_PARAMS

        csv_path = Path(__file__).resolve().parent.parent / "opt_pareto.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)

            F_array = res.F if len(res.F.shape) > 1 else [res.F]
            X_array = res.X if len(res.X.shape) > 1 else [res.X]

            # Use the first solution to figure out the column names of the full geometry
            sample_derived = optimizer.derive_parameters(
                dict(zip(problem.names, X_array[0])), FIXED_PARAMS
            )
            derived_names = list(sample_derived.keys())

            # Header
            header = list(optimizer.OBJECTIVES.keys()) + derived_names
            writer.writerow(header)

            # Data
            for f_val, x_val in zip(F_array, X_array):
                # Reverse negative scores back to positive if it was a maximization objective
                f_real = []
                for i, obj_name in enumerate(optimizer.OBJECTIVES.keys()):
                    sense = optimizer.OBJECTIVES[obj_name][2]
                    f_real.append(-f_val[i] if sense == "maximize" else f_val[i])

                derived = optimizer.derive_parameters(
                    dict(zip(problem.names, x_val)), FIXED_PARAMS
                )
                writer.writerow(list(f_real) + [derived[k] for k in derived_names])

        print(f"Saved Pareto front to {csv_path}")
