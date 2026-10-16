"""Checks of the solver against the main campaign of the study. No API call:
the model is Inspect's mockllm, replaying a stored response.
Run with  python -m pytest -q inspect_eval/tests/test_solver.py"""
import json

from inspect_ai import Task, eval
from inspect_ai.model import ModelOutput, get_model

from dataset import STUDY_DATA, assure_dataset, load_service
from solver import extract_open_questions, extract_test_file, phase_a_prompts, phase_a_verifier
from test_dataset import TRANSCRIPTS

UNITS = STUDY_DATA.parent / "results" / "main_casestudy" / "units"


def _phase_a_call(unit, run):
    """The Phase A call of condition A in one stored unit (prompt and response)."""
    calls = json.loads((UNITS / unit / f"run{run}.transcript.json").read_text(encoding="utf-8"))
    return next(c for c in calls if c["condition"] == "A" and c["phase"] == "A")


def test_prompt_is_the_frozen_one():
    """The user prompt we build is identical to the one sent in the main campaign."""
    for benchmark, unit in TRANSCRIPTS.items():
        _, user = phase_a_prompts(load_service(benchmark)["spec"], "Service")
        assert user == _phase_a_call(unit, 0)["prompt"], benchmark


def test_parsing_matches_the_stored_evidence():
    """On all 15 units, our parsers extract the same suite and the same open
    questions as the study did (runK.json, condition A)."""
    for unit in TRANSCRIPTS.values():
        for run in range(5):
            response = _phase_a_call(unit, run)["response"]
            stored = json.loads((UNITS / unit / f"run{run}.json").read_text(encoding="utf-8"))
            cond_a = stored["conditions"]["A"]
            assert extract_test_file(response) == cond_a["evidence"]["A"]["test_phase_a"], (unit, run)
            assert extract_open_questions(response) == cond_a["open_questions"], (unit, run)


def test_solver_end_to_end_with_a_replayed_response(tmp_path):
    """Run the solver inside Inspect on one service, with a mock model that
    returns a stored Phase A response; the suite lands in the sample's store."""
    response = _phase_a_call(TRANSCRIPTS["svc_qwen"], 0)["response"]
    model = get_model("mockllm/model",
                      custom_outputs=[ModelOutput.from_content("mockllm/model", response)])
    task = Task(dataset=assure_dataset(["svc_qwen"]), solver=phase_a_verifier())
    log = eval(task, model=model, log_dir=str(tmp_path), display="none")[0]

    assert log.status == "success"
    sample = log.samples[0]
    assert sample.messages[0].role == "system"
    assert sample.store["test_phase_a"] == extract_test_file(response)
    assert "def test" in sample.store["test_phase_a"]
