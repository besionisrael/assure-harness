# Who verifies the verifier?

An [Inspect](https://inspect.aisi.org.uk/) evaluation of LLMs as **independent
software verifiers**, built on a pre-registered study of self-validation versus
independent verification for agent-produced code.

When a coding agent writes both the program and the tests, passing tests are no
longer independent evidence. One answer is a separate verifier that writes
tests from the specification alone. That only helps if the verifier is itself
reliable: its tests must catch real violations (detection) without asserting
behavior the specification does not require (false oracles). This repository
measures both, and checks the measuring instrument before trusting it.

The repository has two parts:

- [`inspect_eval/`](inspect_eval/): the evaluation (this README, first).
- [`study/`](study/): the study it comes from: harness, services, seeded
  faults, registered protocol, raw results and analysis (second part below).

## The evaluation

**Question.** Given only a specification S, does a model write tests that
detect seeded faults in an implementation it never sees, without false oracles?

**Material.** Three small stateful Python services from the study (documents
and payments, room booking, equipment loans), each with a specification, a
reference implementation, a visible suite T_v, a hidden suite T_h, and seeded
faults: **46 faults** in total. Each fault is one local edit of the reference
that passes T_v and fails T_h.

**Method.** The model receives the study's frozen "Phase A" prompt
(specification-first: S and the name of the class under test, nothing else) and
writes one test suite per service. In a Docker sandbox, the suite is run on the
reference implementation and every test is classified:

| Class | Rule | Used for |
|---|---|---|
| valid | passes on the reference | detection |
| false oracle | does not pass on the reference | reported as a rate |
| error | cannot run (module does not load, or needs arguments the runner never passes) | reported apart; neither detection nor false oracle |

A fault is **detected** when at least one valid test does not pass on the
faulty program. Five epochs per model; each fault's detection rate is averaged
over them, and the headline number is the mean over the 46 faults.

### Results (5 epochs, scoring mode `expanded`)

| Model | Detection (46 faults) | Documents (14) | Booking (17) | Loans (15) | False oracles | Errors | Tests written |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 5.5 (`claude-sonnet-5-5`) | **95.2%** | 91.4% | 100.0% | 93.3% | 0.4% | 0.0% | 772 |
| GPT-5.5 (`gpt-5.5-2026-04-23`) | **85.7%** | 72.9% | 90.6% | 92.0% | 2.8% | 0.0% | 176 |

Full per-fault table: [`inspect_eval/results/REPORT.md`](inspect_eval/results/REPORT.md).

- **Faults both models miss.** Two documents-service faults
  bind an idempotency key or a pagination cursor to the session token instead of
  the user. The specification fixes the correct behavior only through the
  interaction of two sentences. Claude detected each in 2 of 5 runs, GPT-5.5
  in none. One loans fault (an extra accepted role) was detected by no model and
  by no condition of the study. Catching it requires guessing the exact role
  value, so it is a limit of that fault, not evidence of a shared blind spot.
- **Consistency with the study.** Claude's new suites agree fault by fault with
  condition A of the study's rescored campaign on 44 of 46 faults (95.2% here,
  93.9% there). These are new draws, not a replay.
- **Exploratory comparison (not pre-registered).** An exact sign test over the
  faults, the study's own procedure: 11 faults favor Claude, 0 favor GPT-5.5,
  35 ties, p = 0.001. It compares one pair of models, so provider, capability
  and suite size are confounded (Claude wrote 4.4 times as many tests).

### Validation of the scorer

The scorer is checked before any model is scored, with the same code path:

| Check | Expected | Observed |
|---|---|---|
| T_h used as the suite | 46/46 detected, no false oracle | 46/46, 0, 0 errors |
| T_v used as the suite (every fault passes T_v by construction) | 0/46 detected | 0/46 |
| Replay of the study's stored Phase A suites, `frozen` mode | the study's confirmatory scores | 15/15 runs identical (valid tests, counts, faults) |
| Replay, `expanded` mode | the study's exploratory rescoring | 15/15 runs identical |
| Synthetic suite (fixture, parametrize, false oracle) | each test in its class | pass (`inspect_eval/tests`) |

In `frozen` mode, the error class finds the same 78 runner-incompatible tests
that the study's own decomposition reports (824 tests, 16 genuine false oracles).
That scoring defect of the study, which silently failed parametrized tests, is
the reason the evaluation keeps errors apart and validates its scorer first.

### Run it

Requirements: Python 3.13 (tested), Docker, and API keys for the models you evaluate.

```bash
pip install -r inspect_eval/requirements.txt
python -m pytest -q inspect_eval/tests                       # ~1 min, needs Docker

# validation controls (no model call)
inspect eval inspect_eval/task.py@control_hidden  --max-sandboxes 3
inspect eval inspect_eval/task.py@control_visible --max-sandboxes 3

# the evaluation (~15 calls of up to 64k output tokens per model)
inspect eval inspect_eval/task.py@assure_phase_a --model anthropic/claude-sonnet-5-5 --epochs 5 --max-sandboxes 3
inspect eval inspect_eval/task.py@assure_phase_a --model openai/gpt-5.5-2026-04-23 -M responses_api=false --epochs 5 --max-sandboxes 3

# report from logs (no model call); the logs of the results above are included
python inspect_eval/report.py inspect_eval/results/logs/phase_a_*.eval

# reproduction of the study's scores (no model call)
inspect eval inspect_eval/task.py@replay_study -T campaign=main_casestudy --max-sandboxes 3
python inspect_eval/replay_check.py logs/<replay log>.eval
```

`--max-sandboxes` bounds concurrent containers (2 GB each). Keep it times 2 GB
below the memory of your Docker VM. If several Python installs are on your PATH,
use `python -m inspect_ai eval` instead of `inspect eval`.

How the evaluation is built, file by file: [`inspect_eval/LEARNING.md`](inspect_eval/LEARNING.md).

### Limitations

- **Phase A only.** One call, no feedback, no access to the implementation.
  This is one component of the study's verifier conditions, not a replication
  of them (the study's AB and ABp also include an implementation-aware phase
  and a counterexample loop).
- **Small, partly saturated benchmark.** Three services, 46 seeded faults. Most
  faults are detected by every model and condition. In the study, 12 faults
  separated the conditions; that subset was identified from the study's data
  and is not used as an evaluation set here.
- **Seeded faults, not real ones.** In the study the builder produced no faulty
  program, so all faults are seeded. They may not represent the defects of
  agent-written code. Two of the three services, their faults and their hidden
  tests were written by other LLMs (Mistral Medium 3.5, Qwen 3.7-Plus) and
  reviewed by models, not by humans.
- **False oracles depend on the reference.** Where S leaves behavior open, a
  test is judged against what the reference happens to do.
- **Two models, five epochs.** Provider defaults for temperature and reasoning.
  Differences between models confound provider, capability and suite size. The
  sign test is exploratory.
- **Inspect's provider adapters** replace the study's SDK calls. The prompts are
  checked to be identical, but request details may differ (for example, prompt
  caching is enabled by Inspect for Anthropic).

## The study

[`study/`](study/) contains the controlled study the evaluation is derived from.
It compares a coding agent's self-validation (SV) with an independent verifier
in a fresh context, specification-first (A), implementation-aware with mutation
guidance (B), both (AB), and AB with a verifier from another provider (ABp).
The builder and verifier are Claude Sonnet 5.5; the other provider is GPT-5.5.
The protocol, with two confirmatory hypotheses, hashes of every frozen file and
a deviation log, was registered before the main campaign:
[`study/PROTOCOL.md`](study/PROTOCOL.md).

Main campaign: 3 services, 5 runs each, 15 units, 5.8M tokens.

- The builder's final program was correct in all 15 units, so every analyzed
  fault is seeded.
- **H1 (context independence):** AB detected more seeded faults than the
  builder's own tests: 11 faults favor AB, 1 favors SV, 34 ties; exact sign test
  over faults, Holm-corrected p = 0.006.
- **H2 (model independence):** the verifier from another provider detected fewer
  faults than the same-model verifier: 13 faults favor AB, 0 favor ABp;
  Holm-corrected p = 0.0005.
- **Measurement defect, documented after the runs:** the harness called test
  functions without arguments, so parametrized verifier tests failed on every
  program. They were excluded from detection (the confirmatory results are
  conservative), and genuine false-oracle rates were 0.7 to 2.3%. An exploratory
  rescoring with these tests run gives the same conclusions (H1 11/0, p = 0.001;
  H2 10/0, p = 0.002). See the deviation log in the protocol.

How to run the study, its outputs and metric definitions:
[`study/README.md`](study/README.md). Raw units, transcripts and scores of
every campaign are in `study/results/`.
