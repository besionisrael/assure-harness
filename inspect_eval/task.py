"""Inspect tasks of the evaluation.

  assure_phase_a      the evaluation: a model writes a Phase A suite from S alone
  control_hidden      validation: T_h as the suite, must detect 46/46 faults, 0 false oracle
  control_visible     validation: T_v as the suite, must detect 0/46 faults, 0 false oracle
  replay_study        reproduction: rescore the suites stored by the study (see replay_check.py)

Examples (from the repository root):
  inspect eval inspect_eval/task.py@control_hidden --max-sandboxes 3
  inspect eval inspect_eval/task.py@assure_phase_a --model anthropic/claude-sonnet-5-5 --epochs 5 --max-sandboxes 3
  inspect eval inspect_eval/task.py@assure_phase_a -T mode=frozen ...   (reproduction only)

--max-sandboxes bounds the number of containers running at once. Each container
may use up to 2 GB (sandbox/compose.yaml); without a bound, 15 samples scored at
once exceeded an 8 GB Docker VM and froze the Docker daemon. Keep
max-sandboxes x 2 GB below the memory of your Docker VM.
If several Python installs are on the PATH, use `python -m inspect_ai eval ...`
to be sure the CLI runs with the interpreter that has inspect-ai and the SDKs.
"""
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig

from dataset import assure_dataset, replay_dataset
from scorer import suite_scorer
from solver import known_suite, phase_a_verifier, stored_suite

SANDBOX = ("docker", str(Path(__file__).resolve().parent / "sandbox" / "compose.yaml"))


@task
def assure_phase_a(mode="expanded"):
    """Phase A evidence of a model on the 3 services (46 seeded faults).
    Generation settings follow the protocol (PROTOCOL.md, section 5): provider
    defaults for temperature and reasoning, 64k output tokens (reasoning included)."""
    return Task(
        dataset=assure_dataset(),
        solver=phase_a_verifier(),
        scorer=suite_scorer(mode=mode),
        sandbox=SANDBOX,
        config=GenerateConfig(max_tokens=64000),
    )


@task
def control_hidden(mode="expanded"):
    """Positive control of the scorer: the hidden suite T_h detects every fault."""
    return Task(dataset=assure_dataset(), solver=known_suite("hidden"),
                scorer=suite_scorer(mode=mode), sandbox=SANDBOX, model="mockllm/model")


@task
def replay_study(campaign="main_casestudy"):
    """Reproduction check: rescore the Phase A suites stored by the study, with
    the scoring mode of that campaign, then compare with replay_check.py.
      main_casestudy           frozen    (confirmatory campaign)
      main_casestudy_rescored  expanded  (exploratory rescoring)"""
    mode = {"main_casestudy": "frozen", "main_casestudy_rescored": "expanded"}[campaign]
    return Task(dataset=replay_dataset(), solver=stored_suite(campaign),
                scorer=suite_scorer(mode=mode), sandbox=SANDBOX, model="mockllm/model")


@task
def control_visible(mode="expanded"):
    """Negative control of the scorer: the visible suite T_v detects no fault."""
    return Task(dataset=assure_dataset(), solver=known_suite("visible"),
                scorer=suite_scorer(mode=mode), sandbox=SANDBOX, model="mockllm/model")
