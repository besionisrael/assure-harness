"""Checks of the scorer.

  * classification rules on hand-made runner records (fast, no Docker);
  * an integration run in the Docker sandbox with a synthetic suite whose
    classes are known: valid tests, one false oracle, one fixture test (ERROR),
    one parametrized test (valid in expanded mode, ERROR in frozen mode).
Run with  python -m pytest -q inspect_eval/tests/test_scorer.py   (Docker must be running)"""
from inspect_ai import Task, eval
from inspect_ai.solver import Generate, TaskState, solver

from dataset import assure_dataset, load_service
from scorer import MODULE, _test_names, classify_on_reference, suite_scorer
from task import SANDBOX

SUITE_HEAD = "import pytest\n"
SUITE_EXTRA = '''

def test_synthetic_false_oracle():
    """A status code the specification never uses: must be a FALSE ORACLE."""
    assert Service(Clock()).register_user("u", "member")[0] == 999


def test_synthetic_fixture(tmp_path):
    """Needs a pytest fixture the runner never passes: must be an ERROR."""
    assert tmp_path


@pytest.mark.parametrize("role", ["member", "staff"])
def test_synthetic_parametrized(role):
    """Valid in expanded mode (both cases run), ERROR in frozen mode (called without role)."""
    assert Service(Clock()).register_user("u", role)[0] == 201
'''


def _record(tests, collect_error=None):
    """A runner record for one program, as _runner.run_tests returns it."""
    return {"load_error": None,
            "modules": {MODULE: {"collect_error": collect_error,
                                 "tests": {n: {"status": s, "message": m} for n, (s, m) in tests.items()}}}}


# ------------------------------------------------------------------ fast unit tests
def test_classification_rules():
    suite = ("def test_ok(): pass\n"
             "def test_wrong(): pass\n"
             "def test_fixture(tmp_path): pass\n"
             "def test_typeerror_in_body(): pass\n"
             "def test_slow(): pass\n")
    record = _record({
        "test_ok": ("pass", ""),
        "test_wrong": ("fail", "AssertionError: 404 != 403"),
        "test_fixture": ("error", "TypeError: test_fixture() missing 1 required positional argument: 'tmp_path'"),
        # A TypeError raised inside a test that takes no argument is the test's own bug:
        "test_typeerror_in_body": ("error", "TypeError: f() missing 1 required positional argument: 'x'"),
        "test_slow": ("timeout", "test exceeded time limit"),
    })
    classes = classify_on_reference(suite, record)
    assert classes["valid"] == ["test_ok"]
    assert classes["error"] == ["test_fixture"]
    assert sorted(classes["false_oracle"]) == ["test_slow", "test_typeerror_in_body", "test_wrong"]
    assert classes["timeout"] == ["test_slow"]


def test_collection_error_makes_every_test_an_error():
    suite = "def test_a(): pass\ndef test_b(): pass\n"
    classes = classify_on_reference(suite, _record({}, collect_error="ImportError: no module x"))
    assert classes["error"] == ["test_a", "test_b"]
    assert classes["valid"] == [] and classes["false_oracle"] == []


# ------------------------------------------------------------------ sandbox integration
@solver
def _synthetic_suite():
    """Put T_h of the loans service plus the synthetic tests in the store."""
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.store.set("test_phase_a", SUITE_HEAD + load_service("svc_qwen")["hidden"] + SUITE_EXTRA)
        return state
    return solve


def _run(mode, tmp_path):
    task = Task(dataset=assure_dataset(["svc_qwen"]), solver=_synthetic_suite(),
                scorer=suite_scorer(mode=mode), sandbox=SANDBOX, model="mockllm/model")
    log = eval(task, log_dir=str(tmp_path), display="none")[0]
    assert log.status == "success"
    return log.samples[0].scores["suite_scorer"]


def test_expanded_and_frozen_modes_in_the_sandbox(tmp_path):
    n_hidden = len(_test_names(load_service("svc_qwen")["hidden"]))

    expanded = _run("expanded", tmp_path)
    assert expanded.value["valid"] == n_hidden + 1                  # T_h + the parametrized test
    assert expanded.metadata["classes"]["false_oracle"] == ["test_synthetic_false_oracle"]
    assert expanded.metadata["classes"]["error"] == ["test_synthetic_fixture"]
    assert expanded.metadata["missed"] == []                         # T_h still detects all 15 faults

    frozen = _run("frozen", tmp_path)
    assert frozen.value["valid"] == n_hidden
    assert sorted(frozen.metadata["classes"]["error"]) == ["test_synthetic_fixture",
                                                           "test_synthetic_parametrized"]
    assert frozen.metadata["missed"] == []
