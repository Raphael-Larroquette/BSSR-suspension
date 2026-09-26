import os
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


def constraint_scales(constraints):
    """
    Return the divisor that puts every constraint violation in one currency.

    pymoo ranks infeasible candidates by the SUM of their violations, so raw
    values in mixed units let whichever constraint happens to be measured in the
    largest numbers dominate the search. Roll-centre height is in mm, kingpin in
    degrees, Ackermann in percent: a design 4 mm out on roll centre and one 4%
    out on Ackermann would count the same, and a design 60% out on Ackermann
    would swamp everything else about sixty to one.

    Dividing by the width of each constraint's own window makes a violation mean
    "this fraction of the allowed band", which is comparable across units. A
    one-sided bound has no width, so its own magnitude is used instead.
    """
    scales = {}
    for name, spec in constraints.items():
        bounds = spec[2] if len(spec) > 2 else None
        low, high = bounds if bounds else (None, None)
        if low is not None and high is not None:
            width = abs(high - low)
        elif low is not None or high is not None:
            width = abs(low if low is not None else high)
        else:
            width = 0.0
        scales[name] = width if width > 0.0 else 1.0
    return scales


class SuspensionProblem(ElementwiseProblem):
    def __init__(self, **kwargs):
        import optimizer

        self.names = list(optimizer.FREE_PARAMETERS.keys())

        self.obj_names = list(optimizer.OBJECTIVES.keys())
        self.constr_names = list(optimizer.CONSTRAINTS.keys())
        self.constr_scales = constraint_scales(optimizer.CONSTRAINTS)

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
            # Constraints the candidate was measured on before it failed (the
            # pre-solve shock length) get their real violation; the rest FAIL.
            # So among candidates rejected before solving, a shock 2 mm short
            # ranks ahead of one 40 mm short, and all of them rank ahead of
            # candidates that could not be solved at all (every value FAIL).
            out["G"] = np.array(self._constraint_values(result.outcomes, FAIL))
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

        out["G"] = np.array(self._constraint_values(result.outcomes))

    def _constraint_values(self, outcomes, missing=None):
        """
        pymoo's G vector (<= 0 is satisfied), two entries per constraint.

        A constraint with no outcome is scored `missing` on both sides when
        given (FAIL for a failed candidate); otherwise its value is taken as
        FAIL, as before.
        """
        import optimizer

        G = []
        for const_name in self.constr_names:
            sweep, metric, bounds = optimizer.CONSTRAINTS[const_name]
            if const_name not in outcomes and missing is not None:
                G.extend([missing, missing])
                continue
            val = outcomes.get(const_name, FAIL)
            scale = self.constr_scales[const_name]
            if bounds:
                low, high = bounds
                # Scaled so that a violation reads as a fraction of this
                # constraint's own window - see constraint_scales().
                g1 = (low - val) / scale if low is not None else -FAIL
                g2 = (val - high) / scale if high is not None else -FAIL
            else:
                g1 = g2 = -FAIL
            G.extend([g1, g2])
        return G


def report_failures(algorithm):
    """Print how many of this generation's new candidates failed to solve.

    Replaces one printed line per failure (see evaluate._report). A failed
    candidate is scored FAIL on every objective, which is how it is counted.
    Never allowed to stop the run: this is a progress message only.
    """
    try:
        batch = getattr(algorithm, "off", None)
        if batch is None or len(batch) == 0:
            batch = algorithm.pop
        F = np.asarray(batch.get("F"))
        G = np.asarray(batch.get("G"))
        failed = F[:, 0] >= FAIL
        # Pre-solve rejects carry one real constraint value; solve failures
        # are FAIL everywhere.
        short = failed & np.any(np.abs(G) < FAIL / 2, axis=1)
        print(f"   gen {algorithm.n_gen}: {int(failed.sum())} of {len(batch)} new "
              f"candidates failed - {int(short.sum())} shock too short at design "
              f"height (not solved), {int((failed & ~short).sum())} failed to "
              "solve (lock-out / cannot assemble / too few steps)")
    except Exception:  # noqa: BLE001
        pass


class LogGeneration(Callback):
    def __init__(self, log_path):
        super().__init__()
        self.log_path = log_path

    def notify(self, algorithm):
        report_failures(algorithm)
        evals = []
        for ind in algorithm.pop:
            if False:
                evals.append(ind.get("eval"))
        if evals:
            write_log_rows(evals, algorithm.n_gen, self.log_path)


#: Thread-count variables every numeric library reads at import time.
THREAD_LIMIT_VARS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def limit_worker_threads(threads="1"):
    """
    Hold each worker's BLAS thread pool to one thread.

    numpy and scipy start a BLAS thread pool sized to the machine's core count
    in EVERY process. Run one worker per core and you get cores-squared threads
    - on a 64-core box, roughly four thousand - each reserving stack and buffer
    space. Windows counts all of that against its commit limit (physical RAM plus
    page file), and the limit is reached while a worker is still importing
    scipy, which surfaces as:

        ImportError: DLL load failed while importing _odepack:
        The paging file is too small for this operation to complete.

    The work here is per-candidate and the matrices are small, so a worker has
    nothing to gain from internal threading anyway: the parallelism that matters
    is one candidate per process.

    Set in the parent before the pool is created, because on Windows each child
    inherits this environment and reads these variables when it imports numpy.
    Anything already set in the shell is respected.
    """
    for name in THREAD_LIMIT_VARS:
        os.environ.setdefault(name, threads)


#: Hard ceiling for a single Pool on Windows. multiprocessing waits on one OS
#: handle per worker through WaitForMultipleObjects, which accepts at most 64,
#: so a larger pool dies with "need at most 63 handles". 60 leaves headroom for
#: the pool's own notifier handles. This is a Windows limit, not a tunable: to
#: use more than ~60 processes you need several independent runs, or Linux/WSL2,
#: where fork-based pools have no such cap.
WINDOWS_MAX_WORKERS = 60


def pool_size(pop_size):
    """
    Decide how many worker processes to start.

    Never more than there are candidates to evaluate. A bare ``Pool()`` starts
    one worker per CPU no matter how small the population is, and each worker
    carries its own numpy, scipy, pymoo and model - on the order of 200 MB. On a
    many-core machine that is tens of GB for a 16-candidate smoke test, which
    exhausts memory and takes the terminal down with it.

    ``POOL_WORKERS`` in optimizer.py caps it further, for leaving cores free or
    holding RAM down on a box whose core count outruns its memory. On Windows a
    further hard cap applies - see WINDOWS_MAX_WORKERS.

    Note that ``os.cpu_count()`` reports LOGICAL processors, so a 64-core machine
    with SMT says 128. This workload gains almost nothing from SMT, so the
    Windows ceiling costs little in practice.
    """
    import optimizer

    available = os.cpu_count() or 1
    requested = getattr(optimizer, "POOL_WORKERS", None)
    workers = available if requested in (None, 0) else int(requested)
    workers = min(workers, pop_size, available)
    if os.name == "nt":
        workers = min(workers, WINDOWS_MAX_WORKERS)
    return max(1, workers)


def run_pymoo():
    import optimizer

    pop_size = optimizer.POPULATION_SIZE
    n_gen = optimizer.GENERATIONS

    limit_worker_threads()
    workers = pool_size(pop_size)
    print(
        f"population {pop_size}, {n_gen} generations, {workers} worker processes "
        f"({os.cpu_count()} CPUs visible)"
    )
    pool = Pool(processes=workers)
    runner = StarmapParallelization(pool.starmap)
    problem = SuspensionProblem(elementwise_runner=runner)

    sobol = qmc.Sobol(d=problem.n_var, scramble=True, seed=0)
    initial = qmc.scale(sobol.random(pop_size), problem.xl, problem.xu)

    if hasattr(optimizer, "KNOWN_DESIGN"):
        from .evaluate import FIXED_PARAMS

        optimizer.resolve_spring_seed(FIXED_PARAMS)
        # Put known design in initial population
        known = np.array([optimizer.KNOWN_DESIGN[n] for n in problem.names])
        initial[0] = known

    # Always use NSGA-III per user request, scaling the partitions based on
    # objective count. 3 objectives at n_partitions=14 -> C(16,2) = 120
    # reference directions, which POPULATION_SIZE = 120 matches exactly.
    partitions = {2: 100, 3: 14, 4: 8, 5: 6}.get(problem.n_obj, 5)
    ref_dirs = get_reference_directions(
        "das-dennis", problem.n_obj, n_partitions=partitions
    )
    algorithm = NSGA3(pop_size=pop_size, ref_dirs=ref_dirs, sampling=initial)

    log_path = Path("Working/opt_log.csv")
    callback = LogGeneration(log_path)

    try:
        res = minimize(
            problem,
            algorithm,
            termination=("n_gen", n_gen),
            seed=1,
            save_history=False,
            verbose=True,
            callback=callback,
        )
    finally:
        # Cleanup only, no behaviour change: without this a crash or Ctrl+C
        # leaves every worker process running.
        pool.close()
        pool.join()

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
