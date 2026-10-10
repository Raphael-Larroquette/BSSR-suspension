#!/usr/bin/env python3
"""
Run many independent tasks on one process pool sized to the machine.

This is a LIBRARY used by `Working/run_all.py`. It knows nothing about
suspensions: a task is a picklable payload and a module-level function that
turns it into a result dict. See `tasks.py` for the tasks themselves.

HOW THE POOL IS SIZED

    workers = min(physical cores this process may use,
                  (available memory - reserve) / memory per worker,
                  number of tasks,
                  61 on Windows)

* Physical cores, not logical: the work is CPU-bound Python and numpy, so a
  second hyperthread per core adds little and doubles the memory.
* "Available memory" is the COMMIT headroom on Windows (RAM + page file - what
  is already promised to processes), because that is the limit Windows enforces:
  when it runs out, allocations and even DLL loads fail ("The paging file is too
  small"), however much RAM looks free. Elsewhere it is available RAM.
* The reserve is max(4 GB, 10% of RAM), left for the OS and everything else.
* Memory per worker starts as the caller's estimate and is replaced by what
  workers actually report (their peak, x 1.2) as tasks finish.
* 61 is the most workers ProcessPoolExecutor accepts on Windows.

HOW TASKS ARE ADMITTED

A task is submitted only while fewer than `limit` are in flight AND free memory
minus the reserve still covers one more worker. Memory is re-read before every
submission, so other programs on the machine are respected. Tasks run longest
first (by `weight`) so the slow ones do not trail at the end.

FAILURES

* A task whose worker ran out of memory reports status "resource". That is a
  property of the machine at that moment, not of the design: the task is
  retried (up to MAX_RETRIES) and the concurrency limit drops by 25%.
* A worker that dies outright breaks the whole ProcessPoolExecutor. The pool is
  rebuilt at the lower limit and every task that was in flight is retried.
* Ctrl+C terminates the workers and returns what had finished, with
  `PhaseReport.interrupted` set, so the caller can still write a summary.

THREADS

Every worker is single-threaded (OMP / OpenBLAS / MKL set to 1 thread):
parallelism comes from processes. Left alone, each numpy and scipy load would
size its BLAS thread pool and buffers for every core on the machine, in every
process, which on a 128-thread Windows box exhausts the commit limit.
`pin_threads()` must run before numpy is imported; run_all.py calls it first.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field
from multiprocessing import get_context
from typing import Callable

MB = 1024 * 1024

#: Environment variables that cap BLAS / OpenMP thread pools.
THREAD_VARS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)

#: ProcessPoolExecutor refuses more workers than this on Windows.
WINDOWS_MAX_WORKERS = 61

#: Times a task that failed for lack of memory is retried.
MAX_RETRIES = 2

#: Concurrency is multiplied by this after a resource failure.
BACKOFF = 0.75

#: Margin on a worker's measured peak when budgeting the next one.
PEAK_MARGIN = 1.2


def pin_threads() -> None:
    """Make this process and every worker it spawns single-threaded in BLAS.

    Must run before numpy is first imported. A value the user already set wins.
    """
    for name in THREAD_VARS:
        os.environ.setdefault(name, "1")


# ==========================================================================
# What the machine has
# ==========================================================================
@dataclass(frozen=True)
class Machine:
    """A snapshot of the cores and memory this process can use."""

    physical_cores: int
    logical_cores: int
    usable_cores: int
    ram_mb: float
    available_mb: float
    memory_kind: str  # "commit" (Windows) or "RAM"

    @property
    def reserve_mb(self) -> float:
        return max(4096.0, 0.10 * self.ram_mb)

    def describe(self) -> str:
        return (
            f"{self.usable_cores} usable core(s) "
            f"({self.physical_cores} physical / {self.logical_cores} logical), "
            f"{self.ram_mb / 1024:.0f} GB RAM, "
            f"{self.available_mb / 1024:.0f} GB {self.memory_kind} available, "
            f"{self.reserve_mb / 1024:.0f} GB held in reserve"
        )


def _windows_memory() -> tuple[float, float] | None:
    """(physical RAM, available commit) in MB from GlobalMemoryStatusEx."""
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
        return None
    # ullAvailPageFile is the commit headroom: what can still be promised to
    # processes before Windows starts refusing allocations.
    return status.ullTotalPhys / MB, status.ullAvailPageFile / MB


def memory_mb() -> tuple[float, float, str]:
    """(physical RAM, available, kind) in MB. Kind is "commit" or "RAM"."""
    if os.name == "nt":
        found = _windows_memory()
        if found is not None:
            return found[0], found[1], "commit"
    try:
        import psutil

        vm = psutil.virtual_memory()
        return vm.total / MB, vm.available / MB, "RAM"
    except ImportError:
        pass
    try:
        fields = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                key, value = line.split(":", 1)
                fields[key] = float(value.split()[0]) / 1024
        return fields["MemTotal"], fields["MemAvailable"], "RAM"
    except (OSError, KeyError, ValueError):
        # Unknown: assume plenty, so the pool is sized by cores alone.
        return 16384.0, float("inf"), "unknown"


def _usable_logical() -> int:
    """Logical CPUs this process may run on (respects affinity / containers)."""
    if hasattr(os, "process_cpu_count"):
        count = os.process_cpu_count()  # Python 3.13+
        if count:
            return count
    if hasattr(os, "sched_getaffinity"):
        return len(os.sched_getaffinity(0))
    return os.cpu_count() or 1


def detect_machine() -> Machine:
    """Cores and memory this process can use right now."""
    logical = os.cpu_count() or 1
    try:
        import psutil

        physical = psutil.cpu_count(logical=False) or max(1, logical // 2)
    except ImportError:
        physical = max(1, logical // 2)
    usable_logical = _usable_logical()
    # Scale physical cores by the share of logical CPUs we are allowed.
    usable = max(1, round(physical * usable_logical / logical))
    ram, available, kind = memory_mb()
    return Machine(physical, logical, usable, ram, available, kind)


def process_peak_mb() -> float:
    """Peak memory of the calling process: private commit on Windows, RSS else."""
    try:
        import psutil

        info = psutil.Process().memory_info()
        if os.name == "nt":
            return float(getattr(info, "peak_pagefile", 0) or info.peak_wset) / MB
    except Exception:  # noqa: BLE001 - best effort
        pass
    try:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / MB if sys.platform == "darwin" else peak / 1024
    except Exception:  # noqa: BLE001
        return 0.0


def plan_workers(
    n_tasks: int, worker_mb: float, machine: Machine, cap: int | None = None
) -> tuple[int, str]:
    """How many workers to start, and which limit decided it."""
    by_cores = machine.usable_cores
    headroom = machine.available_mb - machine.reserve_mb
    by_memory = max(1, int(headroom // worker_mb)) if worker_mb > 0 else by_cores
    candidates = {"cores": by_cores, "memory": by_memory, "tasks": max(1, n_tasks)}
    if cap:
        candidates["--workers"] = cap
    if os.name == "nt":
        candidates["Windows pool limit"] = WINDOWS_MAX_WORKERS
    reason = min(candidates, key=lambda k: candidates[k])
    return max(1, candidates[reason]), reason


# ==========================================================================
# Running a phase
# ==========================================================================
@dataclass
class Task:
    """One unit of work. `payload` is what the worker function receives."""

    key: str
    payload: dict
    weight: float = 1.0
    attempt: int = 0


@dataclass
class PhaseReport:
    """How a phase used the machine; printed and kept for the summary."""

    label: str
    workers: int
    limited_by: str
    final_limit: int = 0
    retries: int = 0
    rebuilds: int = 0
    worker_peak_mb: float = 0.0
    seconds: float = 0.0
    interrupted: bool = False
    notes: list[str] = field(default_factory=list)


def _worker_init() -> None:
    """Runs once in every worker process."""
    # Ctrl+C reaches every process in a Windows console. The parent handles it
    # and terminates the workers; a worker interrupted mid-task would instead
    # report a confusing failure.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    pin_threads()


def _new_pool(workers: int, max_tasks_per_child: int | None) -> ProcessPoolExecutor:
    # "spawn" everywhere: it is the only start method on Windows, and using it on
    # Linux too means the pool behaves the same on every machine.
    return ProcessPoolExecutor(
        max_workers=workers,
        mp_context=get_context("spawn"),
        initializer=_worker_init,
        max_tasks_per_child=max_tasks_per_child,
    )


def _terminate(pool: ProcessPoolExecutor) -> None:
    for process in list(getattr(pool, "_processes", {}).values()):
        try:
            process.terminate()
        except Exception:  # noqa: BLE001
            pass
    pool.shutdown(wait=False, cancel_futures=True)


def _resource_result(task: Task, message: str) -> dict:
    return {"key": task.key, "status": "resource", "message": message,
            "attempts": task.attempt + 1, **task.payload.get("identity", {})}


def run_phase(
    label: str,
    tasks: list[Task],
    execute: Callable[[dict], dict],
    *,
    worker_mb: float,
    cap: int | None = None,
    max_tasks_per_child: int | None = None,
    on_result: Callable[[dict], None] | None = None,
    log: Callable[[str], None] = print,
) -> tuple[list[dict], PhaseReport]:
    """
    Run every task on one pool and return (results in task order, report).
    On Ctrl+C the workers are stopped and the finished results are returned with
    `report.interrupted` set.

    `execute(payload)` runs in a worker and must return a dict with at least
    "status"; status "resource" means "ran out of memory, retry me". It should
    catch its own exceptions; one that escapes is recorded as status "error".
    """
    if not tasks:
        return [], PhaseReport(label, 0, "no tasks")

    machine = detect_machine()
    workers, reason = plan_workers(len(tasks), worker_mb, machine, cap)
    report = PhaseReport(label, workers, reason, final_limit=workers)
    log(f"{label}: {len(tasks)} task(s) on {workers} worker(s) "
        f"(limited by {reason}; budget {worker_mb:.0f} MB per worker)")

    pending: deque[Task] = deque(sorted(tasks, key=lambda t: -t.weight))
    inflight: dict[Future, Task] = {}
    results: dict[str, dict] = {}
    limit = workers
    budget_mb = worker_mb
    waited_on_memory = False
    started = time.perf_counter()
    pool = _new_pool(workers, max_tasks_per_child)

    def finish(task: Task, result: dict) -> None:
        results[task.key] = result
        if on_result is not None:
            on_result(result)

    def retry_or_fail(task: Task, message: str) -> None:
        if task.attempt < MAX_RETRIES:
            task.attempt += 1
            pending.appendleft(task)
            report.retries += 1
        else:
            finish(task, _resource_result(task, message))

    def back_off(message: str) -> None:
        """Lower concurrency once per round, however many tasks hit it."""
        nonlocal limit
        new_limit = max(1, int(limit * BACKOFF))
        log(f"   ! out of memory ({message[:90]}); "
            f"concurrency {limit} -> {new_limit}, retrying")
        limit = new_limit
        report.final_limit = limit

    try:
        while pending or inflight:
            # ---- admit -----------------------------------------------------
            while pending and len(inflight) < limit:
                if inflight:
                    _ram, available, _kind = memory_mb()
                    if available - machine.reserve_mb < budget_mb:
                        if not waited_on_memory:
                            report.notes.append(
                                "waited for memory before starting more tasks")
                            waited_on_memory = True
                        break
                task = pending.popleft()
                inflight[pool.submit(execute, task.payload)] = task

            # ---- collect ---------------------------------------------------
            done, _ = wait(list(inflight), timeout=2.0, return_when=FIRST_COMPLETED)
            broken = False
            resource_message = ""
            for future in done:
                task = inflight.pop(future)
                try:
                    result = future.result()
                except BrokenProcessPool:
                    broken = True
                    resource_message = "a worker process died (BrokenProcessPool)"
                    retry_or_fail(task, resource_message)
                    continue
                except Exception as error:  # noqa: BLE001 - e.g. unpicklable result
                    result = {"status": "error",
                              "message": f"{type(error).__name__}: {error}",
                              **task.payload.get("identity", {})}
                result.setdefault("key", task.key)
                result["attempts"] = task.attempt + 1
                peak = float(result.get("peak_mb") or 0.0)
                if peak:
                    report.worker_peak_mb = max(report.worker_peak_mb, peak)
                    budget_mb = max(budget_mb, peak * PEAK_MARGIN)
                if result.get("status") == "resource":
                    resource_message = str(result.get("message", "out of memory"))
                    retry_or_fail(task, resource_message)
                else:
                    finish(task, result)

            if resource_message and limit > 1:
                back_off(resource_message)
            if broken:
                # Every future still in flight died with the pool.
                for task in list(inflight.values()):
                    retry_or_fail(task, resource_message)
                inflight.clear()
                _terminate(pool)
                report.rebuilds += 1
                log(f"   ! worker pool broke; rebuilding with {limit} worker(s)")
                pool = _new_pool(limit, max_tasks_per_child)
    except KeyboardInterrupt:
        # Keep what finished: the caller still writes a summary of it.
        log(f"\n   interrupted: stopping {len(inflight)} running task(s)")
        _terminate(pool)
        report.interrupted = True
    else:
        pool.shutdown(wait=True)
    finally:
        report.seconds = time.perf_counter() - started

    ordered = [results[t.key] for t in tasks if t.key in results]
    return ordered, report
