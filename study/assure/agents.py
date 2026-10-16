"""Builder and verifier roles. Information flow follows the framework:
the verifier never sees the visible tests nor the builder's tests or
reasoning; the builder never sees the verifier's tests, only counterexamples
(principle P2); the verifier never proposes fixes (P4)."""
import copy
import re

from . import llm, mutation, prompts, sandbox


class Role:
    def __init__(self, backend, meta, log):
        self.backend, self.meta, self.log = backend, dict(meta), log
        self.messages = []
        self.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

    def _ask(self, system, content, **meta_extra):
        self.messages.append({"role": "user", "content": content})
        meta = dict(self.meta, **meta_extra)
        try:
            text, usage = self.backend.complete(system, self.messages, meta)
        except llm.IncompleteResponse as e:  # keep the partial answer in the transcript
            self.log.append({"role": meta["role"], "condition": meta.get("condition"),
                             "phase": meta.get("phase"), "backend": self.backend.name,
                             "prompt": content, "response": e.text, "usage": e.usage,
                             "incomplete": True})
            raise
        self.messages.append({"role": "assistant", "content": text})
        self.usage["input_tokens"] += usage.get("input_tokens", 0)
        self.usage["output_tokens"] += usage.get("output_tokens", 0)
        self.usage["calls"] += 1
        self.log.append({"role": meta["role"], "condition": meta.get("condition"),
                         "phase": meta.get("phase"), "backend": self.backend.name,
                         "prompt": content, "response": text, "usage": usage})
        return text


# ====================================================================== builder
class Builder(Role):
    def __init__(self, backend, task, meta, log, cfg):
        super().__init__(backend, dict(meta, role="builder", task=task), log)
        self.task, self.cfg = task, cfg
        self.fields = prompts.task_fields(task)
        self.system = prompts.BUILDER_SYSTEM.format(**self.fields)
        self.solution, self.tests = "", "from solution import *\n"
        self.programs = []          # every version of the program, in order

    def fork(self, condition):
        twin = copy.copy(self)
        twin.messages = copy.deepcopy(self.messages)
        twin.programs = list(self.programs)
        twin.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
        twin.meta = dict(self.meta, condition=condition)
        return twin

    def _absorb(self, text):
        files = llm.extract_files(text)
        sol = files.get("solution.py")
        tst = files.get("test_solution.py")
        for name, code in files.items():  # tolerate unnamed blocks
            name_re = re.escape(self.task.entry_point)
            if sol is None and re.search(rf"def\s+{name_re}\s*\(|class\s+{name_re}\b", code) \
                    and "def test" not in code:
                sol = code
            elif tst is None and "def test" in code and name != "solution.py":
                tst = code
        if sol:
            self.solution = sol
        if tst:
            self.tests = tst
        self.programs.append(self.solution)

    def _check(self):
        """Run visible tests and the builder's own tests; return a text report
        and whether everything passes."""
        t = self.task
        own = sandbox.run_tests([self.solution], {"test_solution": self.tests},
                                max_examples=self.cfg["hypothesis_max_examples"],
                                support=t.support)[0]
        lines = []
        if t.kind == "suite":
            vis = sandbox.run_tests([self.solution], {"visible_tests": t.visible_suite},
                                    support=t.support)[0]
            vmod = vis["modules"].get("visible_tests", {})
            if vis["load_error"]:
                lines.append(f"solution.py fails to load: {vis['load_error']}")
            elif vmod.get("collect_error"):
                lines.append(f"visible_tests.py fails to load: {vmod['collect_error']}")
            for name, r in vmod.get("tests", {}).items():
                if r["status"] != "pass":
                    lines.append(f"Visible test {name} {r['status']}: {r['message']}")
            visible_ok = not lines and bool(vmod.get("tests"))
        else:
            vis = sandbox.eval_io([self.solution], t.entry_point, t.visible_inputs,
                                  t.visible_expected, t.atol, max_failures=10)[0]
            if vis["load_error"]:
                lines.append(f"solution.py fails to load: {vis['load_error']}")
            for f in vis["failures"]:
                lines.append(f"Visible test failed: {t.entry_point}(*{f['input']}) "
                             f"expected {f['expected']}, observed {f['observed']}")
            visible_ok = not vis["load_error"] and len(vis["status"]) > 0 and all(vis["status"])
        mod = own["modules"].get("test_solution", {})
        if own["load_error"] is None and mod.get("collect_error"):
            lines.append(f"test_solution.py fails to load: {mod['collect_error']}")
        for name, r in mod.get("tests", {}).items():
            if r["status"] != "pass":
                lines.append(f"Your test {name} {r['status']}: {r['message']}")
        return "\n".join(lines) or "All tests pass.", (not lines and visible_ok)

    def self_validate(self, max_rounds):
        t = self.task
        text = self._ask(self.system, prompts.BUILDER_INITIAL.format(
            spec=t.spec, visible=t.visible_tests_text(), entry_point=t.entry_point,
            **self.fields),
            phase="initial")
        self._absorb(text)
        rounds = 0
        for rounds in range(1, max_rounds + 1):
            report, ok = self._check()
            if ok:
                return {"self_rounds": rounds - 1, "self_converged": True}
            self._absorb(self._ask(self.system,
                                   prompts.BUILDER_SELF_FEEDBACK.format(report=report),
                                   phase="self-fix"))
        _, ok = self._check()
        return {"self_rounds": rounds, "self_converged": ok}

    def repair(self, counterexamples, inner_rounds):
        self._absorb(self._ask(self.system,
                               prompts.BUILDER_REPAIR.format(counterexamples=counterexamples),
                               phase="repair"))
        for _ in range(inner_rounds):
            report, ok = self._check()
            if ok:
                break
            self._absorb(self._ask(self.system,
                                   prompts.BUILDER_SELF_FEEDBACK.format(report=report),
                                   phase="self-fix"))


# ===================================================================== verifier
def _first_file(text, preferred):
    files = llm.extract_files(text)
    if preferred in files:
        return files[preferred]
    tests = [c for c in files.values() if "def test" in c]
    return tests[0] if tests else ""


class Verifier(Role):
    def __init__(self, backend, task, meta, log, cfg):
        super().__init__(backend, dict(meta, role="verifier", task=task), log)
        self.task, self.cfg = task, cfg
        self.fields = prompts.task_fields(task)
        self.system = prompts.VERIFIER_SYSTEM.format(**self.fields)
        self.rules = prompts.TEST_RULES.format(entry_point=task.entry_point, **self.fields)
        self.open_questions = []

    def phase_a(self):
        text = self._ask(self.system, prompts.VERIFIER_PHASE_A.format(
            spec=self.task.spec, entry_point=self.task.entry_point, rules=self.rules,
            **self.fields),
            phase="A")
        self.open_questions = llm.extract_open_questions(text)
        return {"test_phase_a": _first_file(text, "test_phase_a.py")}

    def phase_b(self, program, frozen_a):
        note = (prompts.FROZEN_NOTE_WITH_A.format(tests_a=frozen_a["test_phase_a"])
                if frozen_a else prompts.FROZEN_NOTE_NO_A)
        text = self._ask(self.system, prompts.VERIFIER_PHASE_B.format(
            frozen_note=note, spec=self.task.spec, program=program, rules=self.rules,
            **self.fields),
            phase="B")
        evidence_b = {"test_phase_b": _first_file(text, "test_phase_b.py")}
        survivors, n_mutants = self._surviving_mutants(program, dict(frozen_a or {}, **evidence_b))
        mutation_info = {"mutants": n_mutants, "survivors": len(survivors)}
        if survivors:
            shown = survivors[: self.cfg["budgets"]["phase_b_survivors_shown"]]
            listing = "\n\n".join(f"Mutant {m['id']} ({m['operator']}):\n```diff\n{m['diff']}\n```"
                                  for m in shown)
            text = self._ask(self.system, prompts.VERIFIER_MUTANTS.format(
                mutants=listing, rules=self.rules), phase="B-mut")
            evidence_b["test_phase_b_mutants"] = _first_file(text, "test_phase_b_mutants.py")
            mutation_info["shown"] = len(shown)
        return evidence_b, mutation_info

    def _surviving_mutants(self, program, test_modules):
        mutants = mutation.generate(program, self.cfg["budgets"]["phase_b_mutants"], seed=0)
        if not mutants:
            return [], 0
        res = sandbox.run_tests([program] + [m["code"] for m in mutants], test_modules,
                                max_examples=self.cfg["hypothesis_max_examples"],
                                support=self.task.support)
        base = _passing(res[0])
        survivors = []
        for m, r in zip(mutants, res[1:]):
            killed = r["load_error"] is not None or bool(base - _passing(r))
            if not killed:
                survivors.append(m)
        return survivors, len(mutants)


def _passing(record):
    out = set()
    for mod, mres in record.get("modules", {}).items():
        for name, r in mres.get("tests", {}).items():
            if r["status"] == "pass":
                out.add((mod, name))
    return out


# ============================================================ counterexamples
def counterexamples(result, limit):
    """Turn failing verifier tests into counterexamples that reveal the
    violated guarantee and the falsifying input, but not the test code."""
    items = []
    if result["load_error"]:
        items.append(f"- The implementation fails to load: {result['load_error']}")
    for mod, mres in result.get("modules", {}).items():
        for name, r in mres.get("tests", {}).items():
            if r["status"] == "pass":
                continue
            notes = " ".join(n.replace(name + "(", "falsifying_input(") for n in r["notes"])
            guarantee = r["doc"] or "(no statement provided)"
            detail = r["message"] if r["status"] != "timeout" else \
                "the implementation did not terminate within the time limit"
            items.append(f"- Guarantee: {guarantee}\n  Observed: {detail}"
                         + (f"\n  {notes}" if notes else ""))
    return "\n".join(f"{i+1}. {s[2:]}" for i, s in enumerate(items[:limit])), len(items)
