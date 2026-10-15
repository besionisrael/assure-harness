"""Sandboxed evaluation runner.

Executed in a separate interpreter (python -I). Reads a pickled job, evaluates
one or more candidate programs, and writes a pickled result. Two job kinds:

  io     run the entry point on a list of inputs and compare with expected
         outputs (or return raw outputs when expected is None)
  tests  run test modules (functions named test_*) against each program

This file must stay self-contained: it is copied into a temporary directory.
"""
import contextlib
import copy
import io
import math
import os
import pickle
import signal
import sys
import types


class _Timeout(BaseException):
    """Raised by the alarm handler. Derives from BaseException so that
    ordinary `except Exception` clauses in generated code do not swallow it."""


def _alarm(signum, frame):
    raise _Timeout()


signal.signal(signal.SIGALRM, _alarm)


@contextlib.contextmanager
def time_limit(seconds):
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _short(obj, n=300):
    try:
        s = repr(obj)
    except BaseException:  # noqa: BLE001
        s = "<unrepresentable>"
    return s if len(s) <= n else s[: n - 3] + "..."


# ---------------------------------------------------------------- equality
def _is_float_like(x):
    if isinstance(x, float):
        return True
    if isinstance(x, (list, tuple)) and x and all(isinstance(v, float) for v in x):
        return True
    return False


def outputs_equal(out, exp, atol):
    """Equality in the spirit of EvalPlus: exact, except for floats, which are
    compared with an absolute tolerance (atol, or 1e-6 when atol is 0)."""
    if out is exp:
        return True
    tol = atol if atol else 1e-6
    if isinstance(exp, float) and isinstance(out, (int, float)) and not isinstance(out, bool):
        if math.isnan(exp):
            return isinstance(out, float) and math.isnan(out)
        return math.isclose(out, exp, rel_tol=1e-7, abs_tol=tol)
    if isinstance(exp, (list, tuple)) and isinstance(out, (list, tuple)):
        if type(exp) is not type(out) or len(exp) != len(out):
            return False
        return all(outputs_equal(o, e, atol) for o, e in zip(out, exp))
    if isinstance(exp, dict) and isinstance(out, dict):
        if exp.keys() != out.keys():
            return False
        return all(outputs_equal(out[k], exp[k], atol) for k in exp)
    try:
        return bool(out == exp)
    except BaseException:  # noqa: BLE001
        return False


# ---------------------------------------------------------------- loading
def load_program(code, name="solution", timeout=5.0):
    mod = types.ModuleType(name)
    mod.__file__ = name + ".py"
    with time_limit(timeout), contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        exec(compile(code, name + ".py", "exec"), mod.__dict__)
    return mod


# ---------------------------------------------------------------- io jobs
def run_io(job):
    results = []
    for code in job["programs"]:
        rec = {"load_error": None, "status": [], "failures": []}
        try:
            mod = load_program(code)
            fn = getattr(mod, job["entry_point"])
        except BaseException as e:  # noqa: BLE001
            rec["load_error"] = f"{type(e).__name__}: {_short(e)}"
            results.append(rec)
            continue
        outputs = []
        for i, inp in enumerate(job["inputs"]):
            args = copy.deepcopy(inp)
            try:
                with time_limit(job["per_item_timeout"]), \
                        contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    out = fn(*args)
                err = None
            except _Timeout:
                out, err = None, "timeout"
            except RecursionError:
                out, err = None, "RecursionError"
            except BaseException as e:  # noqa: BLE001
                out, err = None, f"{type(e).__name__}: {_short(e, 200)}"
            if job["expected"] is None:
                if err is None:
                    try:  # raw outputs travel back by pickle
                        pickle.dumps(out)
                    except Exception:  # noqa: BLE001
                        rec["unpicklable"] = type(out).__name__
                        out, err = None, f"unpicklable output: {type(out).__name__}"
                outputs.append((err, out))
                continue
            ok = err is None and outputs_equal(out, job["expected"][i], job["atol"])
            rec["status"].append(ok)
            if not ok and len(rec["failures"]) < job.get("max_failures", 5):
                rec["failures"].append({
                    "index": i,
                    "input": _short(inp),
                    "expected": _short(job["expected"][i]),
                    "observed": err if err else _short(out),
                })
            if not ok and job.get("stop_on_first_fail"):
                break
        if job["expected"] is None:
            rec["outputs"] = outputs
        results.append(rec)
    return results


# ---------------------------------------------------------------- test jobs
def _configure_hypothesis(cfg):
    try:
        from hypothesis import HealthCheck, settings
        settings.register_profile(
            "assure",
            max_examples=cfg.get("max_examples", 100),
            deadline=None,
            derandomize=True,
            database=None,
            suppress_health_check=list(HealthCheck),
            print_blob=False,
        )
        settings.load_profile("assure")
    except ImportError:
        pass


def _describe_exception(e):
    notes = list(getattr(e, "__notes__", []) or [])
    if isinstance(e, BaseExceptionGroup):  # hypothesis may group failures
        inner = e.exceptions[0]
        notes += list(getattr(inner, "__notes__", []) or [])
        e = inner
    msg = f"{type(e).__name__}: {_short(str(e), 500)}" if str(e) else type(e).__name__
    return msg, [n for n in notes if n.strip()][:4]


def _install_support(job):
    """Make the task's extra modules (e.g. `gateway`) importable by programs and tests."""
    for name, src in job.get("support", {}).items():
        sys.modules[name] = load_program(src, name)


def _param_cases(fn):
    """Keyword arguments of each call of a test: [{}] without pytest.mark.parametrize,
    otherwise the cartesian product of its parametrize marks (pytest.param unwrapped).
    Only used when the job sets expand_parametrize (exploratory rescoring)."""
    cases = [{}]
    for mark in getattr(fn, "pytestmark", None) or []:
        if getattr(mark, "name", "") != "parametrize":
            continue
        argnames = mark.args[0] if mark.args else mark.kwargs["argnames"]
        argvalues = mark.args[1] if len(mark.args) > 1 else mark.kwargs["argvalues"]
        if isinstance(argnames, str):
            argnames = [a.strip() for a in argnames.split(",") if a.strip()]
        rows = []
        for v in list(argvalues):
            if type(v).__name__ == "ParameterSet":
                v = v.values if len(argnames) > 1 else v.values[0]
            rows.append(dict(zip(argnames, v)) if len(argnames) > 1 else {argnames[0]: v})
        cases = [dict(c, **r) for c in cases for r in rows]
    return cases


def run_tests(job):
    _configure_hypothesis(job.get("hypothesis", {}))
    _install_support(job)
    results = []
    for code in job["programs"]:
        per_program = {"load_error": None, "modules": {}}
        try:
            prog = load_program(code)
        except BaseException as e:  # noqa: BLE001
            per_program["load_error"] = f"{type(e).__name__}: {_short(e)}"
            results.append(per_program)
            continue
        for mod_name, src in job["test_modules"].items():
            sys.modules["solution"] = prog
            mres = {"collect_error": None, "tests": {}}
            tmod = types.ModuleType(mod_name)
            try:
                with time_limit(10.0), contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(src, mod_name + ".py", "exec"), tmod.__dict__)
            except BaseException as e:  # noqa: BLE001
                mres["collect_error"] = f"{type(e).__name__}: {_short(e)}"
                per_program["modules"][mod_name] = mres
                continue
            names = [n for n, v in vars(tmod).items()
                     if n.startswith("test") and callable(v)]
            only = job.get("only_tests", {}).get(mod_name)
            if only is not None:
                names = [n for n in names if n in only]
            stop = False
            for n in names:
                fn = getattr(tmod, n)
                doc = (getattr(fn, "__doc__", None) or "").strip()
                cases = _param_cases(fn) if job.get("expand_parametrize") else [{}]
                kw = {}
                try:
                    with time_limit(min(120.0, job["per_item_timeout"] * max(1, len(cases)))), \
                            contextlib.redirect_stdout(io.StringIO()), \
                            contextlib.redirect_stderr(io.StringIO()):
                        for kw in cases:
                            fn(**kw)
                    status, msg, notes = "pass", "", []
                except _Timeout:
                    status, msg, notes = "timeout", "test exceeded time limit", []
                except AssertionError as e:
                    status = "fail"
                    msg, notes = _describe_exception(e)
                except BaseException as e:  # noqa: BLE001
                    status = "error"
                    msg, notes = _describe_exception(e)
                if status != "pass" and kw:
                    msg = f"[parameters {_short(kw, 200)}] {msg}"
                mres["tests"][n] = {"status": status, "message": msg,
                                    "notes": notes, "doc": doc[:300]}
                if status != "pass" and job.get("stop_on_first_fail"):
                    stop = True
                    break
            per_program["modules"][mod_name] = mres
            if stop:
                break
        results.append(per_program)
    return results


def main():
    with open(sys.argv[1], "rb") as f:
        job = pickle.load(f)
    sys.setrecursionlimit(5000)
    if job["kind"] == "io":
        out = run_io(job)
    else:
        out = run_tests(job)
    payload = pickle.dumps(out)  # serialize fully before creating the output file
    tmp = sys.argv[2] + ".part"
    with open(tmp, "wb") as f:
        f.write(payload)
    os.replace(tmp, sys.argv[2])
    os._exit(0)  # skip interpreter teardown of possibly corrupted state


if __name__ == "__main__":
    main()
