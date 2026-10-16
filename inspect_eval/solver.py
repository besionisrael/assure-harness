"""Solver of the evaluation: the study's Phase A verifier, one model call.

It reproduces Verifier.phase_a() of study/assure/agents.py:
  1. build the system and user prompts from study/assure/prompts.py (frozen);
  2. call the model once (the model is chosen on the command line, --model);
  3. extract the test file `test_phase_a.py` and the OPEN QUESTIONS list.
The extracted suite goes into state.store, where the scorer reads it.

Not reproduced, on purpose: Phase B, mutation analysis, the builder and the
counterexample loop. This evaluation measures Phase A evidence only.
"""
import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace

from inspect_ai.model import ChatMessageSystem, ChatMessageUser
from inspect_ai.solver import Generate, TaskState, solver

PROMPTS_FILE = Path(__file__).resolve().parent.parent / "study" / "assure" / "prompts.py"
FROZEN_PROMPT_VERSION = "2026-10-08.2"   # PROTOCOL.md, section 5


def _load_frozen_prompts():
    """Import study/assure/prompts.py by path. It has no imports of its own, so it
    loads on Windows, unlike the rest of the study's package. We refuse to run if
    the prompt version is not the one registered in the protocol."""
    spec = importlib.util.spec_from_file_location("assure_prompts", PROMPTS_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.PROMPT_VERSION != FROZEN_PROMPT_VERSION:
        raise RuntimeError(f"prompts.py is version {module.PROMPT_VERSION}, "
                           f"expected the frozen {FROZEN_PROMPT_VERSION}")
    return module


PROMPTS = _load_frozen_prompts()


def phase_a_prompts(spec, entry_point):
    """Return (system, user) exactly as the study builds them for a service.
    Same calls as Verifier.__init__ and Verifier.phase_a in study/assure/agents.py;
    task_fields only reads task.kind, which is "suite" for the services."""
    fields = PROMPTS.task_fields(SimpleNamespace(kind="suite"))
    system = PROMPTS.VERIFIER_SYSTEM.format(**fields)
    rules = PROMPTS.TEST_RULES.format(entry_point=entry_point, **fields)
    user = PROMPTS.VERIFIER_PHASE_A.format(spec=spec, entry_point=entry_point,
                                           rules=rules, **fields)
    return system, user


# ------------------------------------------------------------------ parsing
# Copies of the study's parsers (study/assure/llm.py and agents.py). The study's
# llm.py cannot be imported here because it imports the provider SDKs; a test
# checks that these copies give the same suites as the study's stored evidence.
_BLOCK = re.compile(r"```([^\n]*)\n(.*?)```", re.S)
_FILE = re.compile(r"file\s*=\s*[\"']?([\w./-]+)")


def extract_files(text):
    """{file name: code} from fenced blocks such as ```python file=test_phase_a.py.
    Unnamed blocks are named block<i>."""
    files = {}
    for i, m in enumerate(_BLOCK.finditer(text)):
        named = _FILE.search(m.group(1))
        files[named.group(1) if named else f"block{i}"] = m.group(2).strip() + "\n"
    return files


def extract_test_file(text, preferred="test_phase_a.py"):
    """The suite: the block named test_phase_a.py, otherwise the first block that
    contains a test function, otherwise "" (an empty suite detects nothing)."""
    files = extract_files(text)
    if preferred in files:
        return files[preferred]
    tests = [code for code in files.values() if "def test" in code]
    return tests[0] if tests else ""


def extract_open_questions(text):
    """Bullet points after `OPEN QUESTIONS:`; "none" means no question."""
    m = re.search(r"OPEN QUESTIONS:\s*\n(.*?)(?:```|\Z)", text, re.S)
    if not m:
        return []
    items = [line.strip("-* \t") for line in m.group(1).splitlines()
             if line.strip().startswith(("-", "*"))]
    return [q for q in items if q and q.lower() not in ("none", "none.", "n/a")]


# ------------------------------------------------------------------ solver
@solver
def phase_a_verifier():
    """Phase A: the model receives S and the name of the class under test, and
    writes a test suite. One call, no tools, no feedback."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        # Replace the default conversation (the raw input) by the study's prompts.
        system, user = phase_a_prompts(state.input_text, state.metadata["entry_point"])
        state.messages = [ChatMessageSystem(content=system), ChatMessageUser(content=user)]

        state = await generate(state)

        # Parse once here, so that the scorer only executes and the logs show
        # exactly which suite was scored.
        text = state.output.completion
        state.store.set("test_phase_a", extract_test_file(text))
        state.store.set("open_questions", extract_open_questions(text))
        state.store.set("stop_reason", state.output.stop_reason)
        return state

    return solve


@solver
def stored_suite(campaign):
    """Replay: put in the store the Phase A suite that the study stored for this
    run (condition A, study/results/<campaign>/units/<benchmark>/<unit>/runK.json),
    so that the scorer can be checked against the study's own scores."""
    import json
    units = PROMPTS_FILE.parent.parent / "results" / campaign / "units"

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        benchmark, run = state.metadata["benchmark"], state.metadata["run"]
        (path,) = (units / benchmark).glob(f"*/run{run}.json")      # one unit folder per service
        unit = json.loads(path.read_text(encoding="utf-8"))
        state.store.set("test_phase_a", unit["conditions"]["A"]["evidence"]["A"]["test_phase_a"])
        return state

    return solve


@solver
def known_suite(kind):
    """Validation control: instead of asking a model, put a known suite of the
    study in the store, so that the scorer is tested on suites whose result is
    known in advance. kind is "hidden" (T_h: must detect every fault, with no
    false oracle) or "visible" (T_v: must detect no fault, since every seeded
    fault passes T_v by construction)."""
    from dataset import load_service   # local import: only the controls need it

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.store.set("test_phase_a", load_service(state.metadata["benchmark"])[kind])
        return state

    return solve
