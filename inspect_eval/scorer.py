"""Scorer of the evaluation: executes the suite in the sandbox and measures it.

Same semantics as the study (study/assure/scoring.py, TaskScorer.score_part):
  1. run every test of the suite on the REFERENCE implementation;
  2. a test that passes there is VALID; the others are not used for detection;
  3. a seeded fault is DETECTED when at least one valid test does not pass on
     the faulty program (assertion failure, exception, or timeout).

Tests that do not pass on the reference are split in two classes:
  ERROR         the test could not be executed at all: its module does not load,
                or it requires arguments that the runner never passes (a pytest
                fixture, or parametrize in frozen mode). Same rule as the paper's
                decomposition (study/scripts/runner_artifact.py).
  FALSE ORACLE  any other test that does not pass on the reference: the test
                asserts something the reference does not do.
ERRORS count neither as detections nor as false oracles; they are reported.

Execution uses the study's frozen runner (study/assure/_runner.py), unchanged.
mode="expanded" (default) runs pytest.mark.parametrize cases, as in the paper's
exploratory rescoring; mode="frozen" calls every test without arguments, as in
the confirmatory campaign, and is used only to check reproduction.
"""
import ast
import json
import re
from pathlib import Path

from inspect_ai.scorer import SampleScore, Score, Target, metric, scorer
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from dataset import load_service

STUDY = Path(__file__).resolve().parent.parent / "study"
RUNNER_SOURCE = (STUDY / "assure" / "_runner.py").read_text(encoding="utf-8")
ENTRY_SOURCE = (Path(__file__).resolve().parent / "sandbox" / "entry.py").read_text(encoding="utf-8")

MODULE = "test_phase_a"       # module name of the suite, as in the study's evidence
MAX_EXAMPLES = 50             # Hypothesis budget at scoring (study: scoring_max_examples)
PER_TEST_TIMEOUT = 10.0       # seconds per test (study: sandbox.run_tests default)

# The message the runner records when it calls a test without the arguments it needs.
# search, not match: in expanded mode the runner prefixes "[parameters {...}] ".
_HARNESS_CALL = re.compile(r"TypeError: .*missing \d+ required (positional|keyword-only) argument")


# ------------------------------------------------------------------ execution
async def _run_job(programs, suite, support, expand, only_tests=None, stop_on_first_fail=False):
    """Run the suite on a list of programs inside the sandbox, in one process.
    Returns one record per program, in the runner's format:
    {"load_error": str|None, "modules": {MODULE: {"collect_error": ..., "tests": {name: {"status", "message", ...}}}}}
    If the process dies (crash, memory, timeout), each program is retried alone,
    as the study does, so that one bad program cannot hide the others.
    stop_on_first_fail: True only on faulty programs, where one failing test is
    enough; on the reference every test must run, to classify each of them."""
    job = {"kind": "tests", "programs": programs, "test_modules": {MODULE: suite},
           "per_item_timeout": PER_TEST_TIMEOUT, "only_tests": only_tests or {},
           "stop_on_first_fail": stop_on_first_fail, "hypothesis": {"max_examples": MAX_EXAMPLES},
           "support": support, "expand_parametrize": expand}
    box = sandbox()
    await box.write_file("_runner.py", RUNNER_SOURCE)
    await box.write_file("entry.py", ENTRY_SOURCE)
    await box.write_file("job.json", json.dumps(job))
    await box.exec(["rm", "-f", "result.json"])
    timeout = 60 + 120 * len(programs)                  # study: sandbox.run_tests
    try:
        await box.exec(["python", "-I", "entry.py", "job.json", "result.json"], timeout=timeout)
        return json.loads(await box.read_file("result.json"))
    except Exception as e:  # noqa: BLE001  timeout, crash, or no result file
        if len(programs) == 1:
            return [{"load_error": f"crash: {type(e).__name__}", "modules": {}}]
        records = []
        for program in programs:
            records += await _run_job([program], suite, support, expand, only_tests,
                                      stop_on_first_fail)
        return records


def _did_not_pass(record):
    """True when a program does not pass the tests it was given (study: _failed_any)."""
    if record["load_error"]:
        return True
    modules = record["modules"].values()
    return any(m.get("collect_error") for m in modules) or any(
        t["status"] != "pass" for m in modules for t in m["tests"].values())


# ------------------------------------------------------------------ classification
def _test_names(suite):
    """Names of the test functions of the suite, or [] if it does not parse."""
    try:
        tree = ast.parse(suite)
    except SyntaxError:
        return []
    return [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test")]


def _takes_arguments(suite):
    """Tests that declare arguments and are not driven by hypothesis @given
    (same rule as study/scripts/runner_artifact.py)."""
    try:
        tree = ast.parse(suite)
    except SyntaxError:
        return set()
    return {n.name for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test")
            and (n.args.args or n.args.kwonlyargs)
            and not any("given" in ast.unparse(d) for d in n.decorator_list)}


def classify_on_reference(suite, record):
    """Split the tests of the suite into valid / false oracle / error, from the
    run on the reference. Returns a dict of lists of test names, plus the
    collection error message if the module did not load."""
    names = _test_names(suite)
    module = record["modules"].get(MODULE, {})
    if record["load_error"] or module.get("collect_error") or not module:
        # Nothing could run: every test of the suite is an ERROR.
        reason = record["load_error"] or module.get("collect_error") or "module not run"
        return {"valid": [], "false_oracle": [], "error": names, "timeout": [],
                "collect_error": reason}
    with_args = _takes_arguments(suite)
    out = {"valid": [], "false_oracle": [], "error": [], "timeout": [], "collect_error": None}
    for name, result in module["tests"].items():
        if result["status"] == "pass":
            out["valid"].append(name)
        elif result["status"] == "error" and name in with_args and _HARNESS_CALL.search(result["message"]):
            out["error"].append(name)
        else:
            out["false_oracle"].append(name)
            if result["status"] == "timeout":
                out["timeout"].append(name)      # still a false oracle, as in the study; listed apart
    return out


async def score_suite(benchmark, suite, expand=True):
    """Score one suite against one service. Independent of the solver, so the
    validation controls can score T_h and T_v with exactly the same code.
    Returns (per-fault detection, classification of the tests, messages of the false oracles)."""
    service = load_service(benchmark)
    fault_ids = sorted(service["faults"])
    detected = {fid: 0 for fid in fault_ids}

    reference_record = (await _run_job([service["reference"]], suite, service["support"], expand))[0]
    classes = classify_on_reference(suite, reference_record)

    if classes["valid"]:
        records = await _run_job([service["faults"][fid]["program"] for fid in fault_ids],
                                 suite, service["support"], expand,
                                 only_tests={MODULE: classes["valid"]}, stop_on_first_fail=True)
        detected = {fid: int(_did_not_pass(r)) for fid, r in zip(fault_ids, records)}

    tests = reference_record["modules"].get(MODULE, {}).get("tests", {})
    messages = {n: tests[n]["message"][:300] for n in classes["false_oracle"] if n in tests}
    return detected, classes, messages


# ------------------------------------------------------------------ metrics
# Score.value is a dict: "fault:<id>" -> 0/1, plus test counts. With several
# epochs, Inspect averages each key over the epochs, so a fault's value becomes
# its detection rate over the runs, as in the paper's per-fault tables.
# Metrics receive one SampleScore per sample; the type annotation
# list[SampleScore] tells Inspect which format to pass (without it, an older one).

def _faults(score):
    return [v for k, v in score.score.value.items() if k.startswith("fault:")]


@metric
def detection():
    """Mean detection rate over all seeded faults of all services (46 faults):
    the "All" column of the paper's table of seeded-fault detection."""
    def compute(scores: list[SampleScore]) -> float:
        values = [v for s in scores for v in _faults(s)]
        return sum(values) / len(values) if values else 0.0
    return compute


@metric
def false_oracle_rate():
    """False oracles / tests that could be executed (tests minus errors), pooled."""
    def compute(scores: list[SampleScore]) -> float:
        fo = sum(s.score.value["false_oracles"] for s in scores)
        executed = sum(s.score.value["tests"] - s.score.value["errors"] for s in scores)
        return fo / executed if executed else 0.0
    return compute


@metric
def error_rate():
    """Errors (tests that could not be executed) / all tests, pooled."""
    def compute(scores: list[SampleScore]) -> float:
        err = sum(s.score.value["errors"] for s in scores)
        tests = sum(s.score.value["tests"] for s in scores)
        return err / tests if tests else 0.0
    return compute


# ------------------------------------------------------------------ scorer
@scorer(metrics=[detection(), false_oracle_rate(), error_rate()])
def suite_scorer(mode="expanded"):
    """Score the suite left in state.store by the solver. mode is "expanded"
    (default) or "frozen" (reproduction of the confirmatory campaign only)."""
    if mode not in ("expanded", "frozen"):
        raise ValueError(f"mode must be 'expanded' or 'frozen', not {mode!r}")

    async def score(state: TaskState, target: Target) -> Score:
        benchmark = state.metadata["benchmark"]
        suite = state.store.get("test_phase_a", "")
        detected, classes, messages = await score_suite(benchmark, suite, expand=(mode == "expanded"))

        n_tests = len(classes["valid"]) + len(classes["false_oracle"]) + len(classes["error"])
        value = {f"fault:{fid}": d for fid, d in detected.items()}
        value.update(tests=n_tests, valid=len(classes["valid"]),
                     false_oracles=len(classes["false_oracle"]), errors=len(classes["error"]))
        missed = [fid for fid, d in detected.items() if not d]
        return Score(
            value=value,
            explanation=(f"{sum(detected.values())}/{len(detected)} faults detected; "
                         f"{n_tests} tests: {len(classes['valid'])} valid, "
                         f"{len(classes['false_oracle'])} false oracles, {len(classes['error'])} errors; "
                         f"missed: {', '.join(missed) or 'none'}"),
            metadata={"mode": mode, "missed": missed, "classes": classes,
                      "false_oracle_messages": messages,
                      "open_questions": state.store.get("open_questions", [])},
        )

    return score
