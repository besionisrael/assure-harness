"""Unit tests of the harness itself (run with: python -m pytest tests)."""
import importlib.util
from pathlib import Path

from assure import agents, llm, mutation, sandbox

spec = importlib.util.spec_from_file_location(
    "runner", Path(__file__).resolve().parent.parent / "assure" / "_runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_float_tolerance_and_types():
    assert runner.outputs_equal(0.1 + 0.2, 0.3, 0)
    assert not runner.outputs_equal([1, 2], (1, 2), 0)
    assert runner.outputs_equal({"a": [1.0, 2.0]}, {"a": [1.0, 2.0 + 1e-9]}, 0)
    assert not runner.outputs_equal(1.0, 1.1, 0)


def test_mutants_are_valid_and_distinct():
    code = "def f(xs):\n    \"\"\"doc\"\"\"\n    s = 0\n    for x in xs:\n        if x > 0 and x % 2 == 0:\n            s += x\n    return s\n"
    ms = mutation.generate(code, max_mutants=100)
    assert len(ms) > 8
    assert len({m["code"] for m in ms}) == len(ms)
    assert all("doc" in m["code"] for m in ms)  # docstring never mutated
    ops = {m["operator"] for m in ms}
    assert {"ROR", "AOR", "LCR", "CRP"} <= ops


def test_io_detects_wrong_program_and_timeout():
    good = "def f(x):\n    return x * 2\n"
    bad = "def f(x):\n    return x + 2\n"
    loop = "def f(x):\n    while True:\n        pass\n"
    res = sandbox.eval_io([good, bad, loop], "f", [[1], [3]], [2, 6], per_item_timeout=0.5)
    assert all(res[0]["status"]) and not any(res[1]["status"])
    assert res[2]["failures"][0]["observed"] == "timeout"


def test_unpicklable_outputs_do_not_crash():
    match = "import re\ndef f(s):\n    return re.search('^a', s)\n"
    raw = sandbox.eval_io([match], "f", [["abc"]], None)[0]
    assert raw["unpicklable"] == "Match" and raw["outputs"][0][1] is None
    scored = sandbox.eval_io([match], "f", [["abc"]], [True])[0]
    assert scored["load_error"] is None and scored["status"] == [False]


def test_tests_runner_statuses():
    mods = {"m": "from solution import f\n"
                 "def test_ok():\n    assert f(2) == 4\n"
                 "def test_wrong():\n    '''Doubling.'''\n    assert f(2) == 5, 'input=2'\n"}
    r = sandbox.run_tests(["def f(x):\n    return 2 * x\n"], mods)[0]["modules"]["m"]["tests"]
    assert r["test_ok"]["status"] == "pass" and r["test_wrong"]["status"] == "fail"
    assert r["test_wrong"]["doc"] == "Doubling."


def test_counterexamples_hide_test_code():
    res = {"load_error": None, "modules": {"m": {"tests": {
        "test_secret_name": {"status": "fail", "message": "AssertionError: input=[0, -1]",
                             "notes": ["Failing test case: test_secret_name(\n    xs=[0, -1],\n)"],
                             "doc": "The output is sorted."}}}}}
    text, n = agents.counterexamples(res, 5)
    assert n == 1 and "The output is sorted." in text and "xs=[0, -1]" in text
    assert "test_secret_name" not in text


def test_file_extraction_and_open_questions():
    text = ("Reasoning.\nOPEN QUESTIONS:\n- Is the empty list allowed?\n"
            "```python file=solution.py\ndef f():\n    return 1\n```\n"
            "```python file=test_solution.py\ndef test_a():\n    pass\n```")
    files = llm.extract_files(text)
    assert set(files) == {"solution.py", "test_solution.py"}
    assert llm.extract_open_questions(text) == ["Is the empty list allowed?"]


def test_faulty_release_compares_gate_outcome_not_correctness():
    from assure.analyze import Analysis
    def row(task, cond, correct, verdict):
        return {"benchmark": "b", "task_id": task, "run": 0, "condition": cond,
                "correct": correct, "verdict": verdict}
    rows = [row("t1", "SV", False, "release"), row("t1", "AB", False, "block"),
            row("t2", "SV", True, "release"), row("t2", "AB", True, "block")]
    a = Analysis(rows)
    a.mcnemar_pair("Faulty releases SV vs AB", "RQ4", "SV", "faulty_release", "AB", "faulty_release")
    t = a.tests[-1]
    assert (t["mean_a"], t["mean_b"], t["effect"]) == (0.5, 0.0, "discordant 1/0")


def test_evalplus_prompts_render_exactly_as_version_1():
    import json
    from assure import data, prompts as p
    fixture = Path(__file__).resolve().parent / "fixtures" / "prompts_evalplus_2026-10-08.1.json"
    old = json.loads(fixture.read_text())
    spec = 'def f(x):\n    """Return x doubled."""\n'
    task = data.Task("T/0", "humaneval", "f", spec, "", [], [], [], [])
    fl = p.task_fields(task)
    rules = p.TEST_RULES.format(entry_point="f", **fl)
    new = {
        "builder_system": p.BUILDER_SYSTEM.format(**fl),
        "builder_initial": p.BUILDER_INITIAL.format(spec=spec, visible="assert f(1) == 2",
                                                    entry_point="f", **fl),
        "verifier_system": p.VERIFIER_SYSTEM.format(**fl),
        "rules": rules,
        "phase_a": p.VERIFIER_PHASE_A.format(spec=spec, entry_point="f", rules=rules, **fl),
        "phase_b_frozen": p.VERIFIER_PHASE_B.format(
            frozen_note=p.FROZEN_NOTE_WITH_A.format(tests_a="def test_x(): pass"), spec=spec,
            program="def f(x): return 2*x", rules=rules, **fl),
        "phase_b_alone": p.VERIFIER_PHASE_B.format(frozen_note=p.FROZEN_NOTE_NO_A, spec=spec,
                                                   program="def f(x): return 2*x", rules=rules, **fl),
        "mutants": p.VERIFIER_MUTANTS.format(mutants="Mutant M1", rules=rules, **fl),
        "self_feedback": p.BUILDER_SELF_FEEDBACK.format(report="All tests pass.", **fl),
        "repair": p.BUILDER_REPAIR.format(counterexamples="1. x", **fl),
    }
    assert new == old


def test_casestudy_ground_truth_through_harness_sandbox():
    from assure import data
    t = data.load_casestudy()
    suites = {"visible_tests": t.visible_suite, "hidden_tests": t.hidden_suite}
    ref, f01, f09 = sandbox.run_tests([t.canonical, t.seeded["F01"], t.seeded["F09"]], suites,
                                      support=t.support)
    statuses = lambda r: {n: x["status"] for m in r["modules"].values() for n, x in m["tests"].items()}  # noqa: E731
    assert ref["load_error"] is None and set(statuses(ref).values()) == {"pass"}
    assert statuses(f01)["test_req17_search_never_returns_other_users_documents"] == "fail"
    assert statuses(f09)["test_req23_retry_after_timeout_charges_at_most_once"] == "fail"
    assert all(v == "pass" for n, v in statuses(f09).items() if n.startswith("test_") and
               n in t.visible_suite)


def test_builder_check_on_suite_task():
    from assure import data
    t = data.load_casestudy()
    cfg = {"hypothesis_max_examples": 10}
    b = agents.Builder(llm.MockBackend(), t, {"run": 0, "condition": "P0"}, [], cfg)
    b.solution, b.tests = t.seeded["F08"], t.visible_suite
    assert b._check() == ("All tests pass.", True)      # seeded faults pass T_v
    b.solution = t.canonical.replace("return 201, {\"id\": doc_id}", "return 200, {\"id\": doc_id}")
    report, ok = b._check()
    assert not ok and "Visible test test_create_and_get_document fail" in report


def test_incomplete_responses_raise():
    import pytest
    for text, stop in [("", "end_turn"), ("partial", "max_tokens"), ("partial", "length"),
                       ("no", "refusal"), ("   ", "stop")]:
        with pytest.raises(llm.IncompleteResponse):
            llm._check_complete("m", text, stop, {})
    llm._check_complete("m", "```python file=a.py\n```", "end_turn", {})
    llm._check_complete("m", "ok", "stop", {})


def test_interrupted_unit_is_replayed_without_new_calls(tmp_path):
    import json
    import pytest
    from assure import data, pipeline
    task = data.load_casestudy()
    cfg = {"conditions": ["SV", "A"], "hypothesis_max_examples": 10,
           "budgets": {"self_rounds": 2, "cex_rounds": 2, "inner_repair_rounds": 1,
                       "max_counterexamples": 5, "phase_b_mutants": 5, "phase_b_survivors_shown": 2}}

    class Counting(llm.MockBackend):
        def __init__(self, fail_after=None, **kw):
            super().__init__(**kw)
            self.calls, self.fail_after = 0, fail_after

        def complete(self, system, messages, meta):
            if self.fail_after is not None and self.calls >= self.fail_after:
                raise RuntimeError("simulated quota error")
            self.calls += 1
            return super().complete(system, messages, meta)

    def backends(fail_after=None):
        b = Counting(fail_after, seed=1, label="mock-builder")
        v = Counting(fail_after, seed=2, label="mock-verifier")
        return {"builder": b, "verifier": v, "verifier_alt": v}

    ref_dir, cut_dir = tmp_path / "ref", tmp_path / "cut"
    pipeline.run_unit(task, 0, backends(), cfg, ref_dir)
    with pytest.raises(RuntimeError, match="simulated"):
        pipeline.run_unit(task, 0, backends(fail_after=1), cfg, cut_dir)
    partial = pipeline._unit_path(cut_dir, task, 0).with_suffix(".partial.transcript.json")
    assert len(json.loads(partial.read_text())) == 2          # one builder + one verifier call kept
    resumed = backends()
    pipeline.run_unit(task, 0, resumed, cfg, cut_dir)
    ref = json.loads(pipeline._unit_path(ref_dir, task, 0).read_text())
    got = json.loads(pipeline._unit_path(cut_dir, task, 0).read_text())
    assert got["replayed_calls"] == 2 and not partial.exists()
    assert got["conditions"] == ref["conditions"] and got["p0"] == ref["p0"]
    total = sum(b.calls for b in {id(b): b for b in resumed.values()}.values())
    assert total == len(json.loads(pipeline._unit_path(ref_dir, task, 0)
                                   .with_suffix(".transcript.json").read_text())) - 2

    log = json.loads(pipeline._unit_path(ref_dir, task, 0).with_suffix(".transcript.json").read_text())
    log[0]["prompt"] += " (edited)"
    r = llm.Replay(log)
    with pytest.raises(llm.ReplayMismatch, match="prompt differs"):
        agents.Builder(r.wrap(backends()["builder"]), task, {"run": 0, "condition": "P0"}, [], cfg) \
            .self_validate(1)


def test_casestudy_versions_and_what_agents_see():
    import json
    from assure import data
    v1, v2 = data.load_casestudy("casestudy"), data.load_casestudy("casestudy_v2")
    assert (v1.task_id, v2.task_id) == ("casestudy/docpay", "casestudy/docpay-v2")
    assert len(v1.seeded) == 10 and len(v2.seeded) == 14
    for t in (v1, v2):
        low = t.spec.lower()
        assert not any(w in low for w in ("seeded", "hidden", "design.md", "version 2", "draft"))
    assert "The *caller* of a method is the user the token belongs to." in v2.spec
    assert "Documents deleted after a cursor was issued are not returned" in v2.spec
    assert "Updating a document does not change its position" in v2.spec
    assert "caller* of a method" not in v1.spec and "provided no document is created" in v1.spec


def test_seeded_sign_test_uses_faults_as_units():
    from assure.analyze import Analysis
    rows = []
    for run in range(3):
        rows.append({"benchmark": "cs", "task_id": "t", "run": run, "condition": "AB",
                     "correct": True, "verdict": "release",
                     "seeded_faults": ["F1", "F2", "F3"], "seeded_detected": ["F1", "F2", "F3"]})
        rows.append({"benchmark": "cs", "task_id": "t", "run": run, "condition": "SV",
                     "correct": True, "verdict": "release",
                     "seeded_faults": ["F1", "F2", "F3"], "seeded_detected": ["F1"] if run else []})
    a = Analysis(rows)
    a.seeded_sign_test("H1", "AB", "SV")
    t = a.confirm[-1]
    assert t["n"] == 3 and t["effect"] == "3+/0-/0=" and abs(t["p"] - 0.25) < 1e-9


def test_third_party_services_load_with_their_ground_truth():
    from assure import data
    for bench, n_faults in (("svc_mistral", 17), ("svc_qwen", 15)):
        t = data.load_casestudy(bench)
        assert t.kind == "suite" and t.entry_point == "Service" and len(t.seeded) == n_faults
        assert "```" not in t.spec and "<!--" not in t.spec
        assert all(code != t.canonical for code in t.seeded.values())
    assert sorted(data.load_casestudy("casestudy_v2").support) == ["gateway"]


def test_seeded_table_keeps_services_apart():
    from assure.analyze import Analysis
    rows = []
    for bench, detected in (("svc_mistral", ["F01"]), ("svc_qwen", [])):
        for c in ("SV", "AB"):
            rows.append({"benchmark": bench, "task_id": bench, "run": 0, "condition": c,
                         "correct": True, "verdict": "release", "parts": {},
                         "seeded_faults": ["F01", "F02"], "seeded_detected": detected,
                         "seeded_detection_rate": len(detected) / 2})
    a = Analysis(rows)
    a.seeded_table()
    text = "\n".join(a.md)
    assert "Seeded-fault detection, svc_mistral" in text and "Seeded-fault detection, svc_qwen" in text
    assert text.count("| F01 | 1/1 | 1/1 |") == 1 and text.count("| F01 | 0/1 | 0/1 |") == 1
    assert a.macros["resSeedDetABSvcM"] == "50.0" and a.macros["resSeedDetABSvcQ"] == "0.0"


def test_parametrize_is_run_only_when_expanded():
    mods = {"m": "import pytest\nfrom solution import f\n\n"
                 "@pytest.mark.parametrize('x,exp', [(1, 2), pytest.param(3, 6)])\n"
                 "@pytest.mark.parametrize('k', [1])\n"
                 "def test_double(x, exp, k):\n    assert f(x) * k == exp\n"}
    good, bad = "def f(x):\n    return 2 * x\n", "def f(x):\n    return 2 * x if x < 3 else 0\n"
    frozen = sandbox.run_tests([good], mods)[0]["modules"]["m"]["tests"]["test_double"]
    assert frozen["status"] == "error"                       # behavior of the frozen campaign
    ok, ko = sandbox.run_tests([good, bad], mods, expand_parametrize=True)
    assert ok["modules"]["m"]["tests"]["test_double"]["status"] == "pass"
    r = ko["modules"]["m"]["tests"]["test_double"]
    assert r["status"] == "fail" and "'x': 3" in r["message"]
