"""Parent side of the sandbox: launches _runner.py in a fresh interpreter with
resource limits, and falls back to one process per program when a batch dies.

Generated code is executed here. Run the harness inside a container (see
README) and never on a machine holding credentials beyond the API keys.
"""
import os
import pickle
import resource
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RUNNER = Path(__file__).with_name("_runner.py")
MEMORY_LIMIT_BYTES = 2 * 1024 ** 3


def _limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.setsid()


def _crash_record(kind, reason):
    if kind == "io":
        return {"load_error": f"crash: {reason}", "status": [], "failures": []}
    return {"load_error": f"crash: {reason}", "modules": {}}


def _launch(job, timeout):
    tmp = tempfile.mkdtemp(prefix="assure-")
    try:
        shutil.copy(RUNNER, Path(tmp) / "_runner.py")
        jp, op = Path(tmp) / "job.pkl", Path(tmp) / "out.pkl"
        with open(jp, "wb") as f:
            pickle.dump(job, f)
        env = {"PATH": os.environ.get("PATH", "/usr/bin"), "PYTHONHASHSEED": "0",
               "HOME": tmp}
        proc = subprocess.run(
            [sys.executable, "-I", str(Path(tmp) / "_runner.py"), str(jp), str(op)],
            cwd=tmp, env=env, timeout=timeout, preexec_fn=_limits,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        if not op.exists():
            tail = proc.stderr.decode(errors="replace")[-300:]
            raise RuntimeError(f"runner exited {proc.returncode}: {tail}")
        try:
            with open(op, "rb") as f:
                return pickle.load(f)
        except (EOFError, pickle.UnpicklingError) as e:
            raise RuntimeError(f"unreadable runner output: {e}") from e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(job, timeout=None):
    """Run a job; returns one record per program in job['programs']."""
    n_items = len(job.get("inputs", ())) or 20
    if timeout is None:
        per_prog = min(600, 10 + n_items * job["per_item_timeout"] * 0.25)
        timeout = 30 + per_prog * len(job["programs"])
    try:
        return _launch(job, timeout)
    except (subprocess.TimeoutExpired, RuntimeError) as e:
        if len(job["programs"]) == 1:
            return [_crash_record(job["kind"], type(e).__name__)]
        out = []
        for code in job["programs"]:  # isolate the offending program
            single = dict(job, programs=[code])
            out.extend(run(single, timeout=max(60, timeout / len(job["programs"]) * 2)))
        return out


# ---------------------------------------------------------------- helpers
def eval_io(programs, entry_point, inputs, expected, atol=0.0, per_item_timeout=4.0,
            stop_on_first_fail=False, max_failures=5):
    return run({"kind": "io", "programs": programs, "entry_point": entry_point,
                "inputs": inputs, "expected": expected, "atol": atol,
                "per_item_timeout": per_item_timeout,
                "stop_on_first_fail": stop_on_first_fail,
                "max_failures": max_failures})


def run_tests(programs, test_modules, per_item_timeout=10.0, only_tests=None,
              stop_on_first_fail=False, max_examples=100, support=None,
              expand_parametrize=False):
    return run({"kind": "tests", "programs": programs, "test_modules": test_modules,
                "per_item_timeout": per_item_timeout, "only_tests": only_tests or {},
                "stop_on_first_fail": stop_on_first_fail,
                "hypothesis": {"max_examples": max_examples}, "support": support or {},
                "expand_parametrize": expand_parametrize},
               timeout=60 + 120 * len(programs) * max(1, len(test_modules)))
