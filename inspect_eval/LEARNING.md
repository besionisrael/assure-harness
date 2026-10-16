# How this evaluation is built

A guide to the architecture of the evaluation, written so that it can be rebuilt
from scratch. Read it with the code open; every file is short.

## The question, in Inspect terms

> Given only a specification S, does a model write tests that detect seeded
> faults in an implementation it never sees, without asserting behavior the
> specification does not require?

An Inspect evaluation is a **Task** = **Dataset** + **Solver** + **Scorer**,
optionally run inside a **sandbox**, and every run writes a **log**.

```
            Dataset (dataset.py)          3 Samples, one per service
                 |  input = S, metadata = service id, fault list
                 v
            Solver (solver.py)            frozen Phase A prompt, 1 model call
                 |  state.store["test_phase_a"] = the generated test file
                 v
            Scorer (scorer.py)            runs the tests in Docker
                 |  reference -> valid / false oracle / error
                 |  faulty programs -> detected or not, per fault
                 v
            Score.value = {"fault:F01": 1, ..., "tests": .., "false_oracles": .., "errors": ..}
                 |  epochs: Inspect averages each key over the runs
                 v
            Metrics: detection (mean over 46 faults), false_oracle_rate, error_rate
```

## Files

| File | Inspect concept | Role |
|---|---|---|
| `dataset.py` | `Dataset`, `Sample` | Reads the three services of `study/data/`. One `Sample` per service: `input` is S without its author comments, `target` is the list of fault ids, `metadata` names the service. `load_service()` returns the ground truth (reference, faulty programs, T_v, T_h, support modules); it is used by the scorer and never enters a Sample, so it cannot leak into a prompt. `replay_dataset()` gives one Sample per (service, run) of the study, for the replay. |
| `solver.py` | `@solver`, `TaskState`, `store` | `phase_a_verifier()` builds the system and user prompts from `study/assure/prompts.py` (refuses to run if the prompt version is not the frozen one), calls the model once, and parses the test file and the open questions into `state.store`. `known_suite()` and `stored_suite()` are solvers that call no model: they put a known suite (T_h, T_v) or a suite stored by the study in the store. |
| `scorer.py` | `@scorer`, `@metric`, `sandbox()` | Copies the study's frozen runner into the container, runs the suite on the reference, classifies each test, then runs the valid tests on every faulty program. Returns one `Score` per Sample with one key per fault. Defines the three metrics. |
| `task.py` | `@task`, `Task`, `GenerateConfig` | Assembles the pieces. `assure_phase_a` is the evaluation; `control_hidden`, `control_visible` and `replay_study` check the scorer. |
| `sandbox/` | sandbox (Docker) | `compose.yaml` and `Dockerfile`: Python 3.13, hypothesis and pytest pinned, no network, 2 GB, non-root. `entry.py` runs inside the container: it loads the runner and writes the result as JSON. |
| `report.py` | logs (`read_eval_log`) | Reads finished logs, without any model call or Docker, and writes `results/REPORT.md` and `results/per_fault.csv`. |
| `replay_check.py` | logs | Compares a `replay_study` log with the study's `scores.jsonl`, run by run. |
| `tests/` | | `pytest` checks: dataset content, prompt and parsing identical to the study, classification rules, a synthetic suite in the sandbox. |
| `results/` | | The report, the per-fault table, and the four logs it was built from. |

## Design decisions, and the alternatives set aside

**One Sample per service, not per fault.** Phase A sees only S, so the suite
does not depend on the fault. The study wrote one suite per service and per run,
then scored it against every fault. With one Sample per fault, Inspect would run
14 to 17 identical prompts in parallel and score different suites against
different faults. The fault stays the unit of analysis in the metrics.

**Reuse the study's frozen files instead of rewriting them.** The prompt comes
from `study/assure/prompts.py`; the tests run with `study/assure/_runner.py`,
unchanged. The study's package cannot be imported on Windows (its sandbox uses
POSIX-only modules), so the three small rules the evaluation needs (spec comment
removal, fault patching, output parsing) are copied, and tests check that the
copies agree with the study on its own data.

**Parse in the solver, execute in the scorer.** The log then shows exactly which
suite was scored, and the scorer can be reused unchanged on suites that no model
wrote in this run (controls, replay).

**Messages built by hand.** Inspect's `system_message()` and `prompt_template()`
format their text with `{...}`; the frozen rules contain literal braces.

**Three classes of tests, decided on the reference.**
- VALID: passes on the reference; used for detection.
- FALSE ORACLE: does not pass on the reference (assertion, exception, or timeout).
- ERROR: could not be executed: its module does not load, or it requires
  arguments the runner never passes (a fixture; parametrize in frozen mode),
  recognized by the study's rule (arguments, no `@given`, a `TypeError` about a
  missing argument). Errors count neither as detections nor as false oracles.

A fault is detected when at least one valid test does not pass on it. The
reference runs every test (to classify each); faulty programs stop at the first
failure. A test caught this: an early version stopped on the reference too, and
left tests unclassified.

**Two scoring modes.** `expanded` (default) runs the cases of
`pytest.mark.parametrize`, as the study's exploratory rescoring did; a
parametrized test is valid only if all its cases pass. `frozen` calls every test
without arguments, as the confirmatory campaign did, and exists only to check
reproduction.

**JSON, not pickle, out of the sandbox.** The result is read on the host;
unpickling data written next to untrusted code would let that code run on the host.

**Bounded concurrency.** Each container may use 2 GB. Unbounded, 15 containers
froze an 8 GB Docker VM; run with `--max-sandboxes 3`.

## How the scorer is validated

| Check | Expected | Where |
|---|---|---|
| T_h as the suite | 46/46 faults, 0 false oracle, 0 error | `task.py@control_hidden` |
| T_v as the suite | 0/46 faults (every fault passes T_v by construction) | `task.py@control_visible` |
| Classification rules | fixture -> ERROR; TypeError in a test body -> FALSE ORACLE; parametrize -> VALID (expanded) or ERROR (frozen) | `tests/test_scorer.py` |
| Replay, frozen | the study's confirmatory scores, run by run | `task.py@replay_study` + `replay_check.py` |
| Replay, expanded | the study's exploratory rescoring, run by run | same, `-T campaign=main_casestudy_rescored` |

Both replays reproduce all 15 runs exactly, and in frozen mode the ERROR class
finds the 78 runner-incompatible tests of the study's own decomposition.

## Rebuilding it: a suggested order

1. `dataset.py`: load one service, print its Sample, write the content tests.
2. `solver.py`: rebuild the prompt, compare it with a stored transcript; run
   with `mockllm` before spending tokens.
3. `sandbox/` and `scorer.py`: start with the controls (T_h, T_v); they need no model.
4. `task.py`: one task per question; controls get `model="mockllm/model"`.
5. `report.py`: read the logs; never rerun models to make a table.

## Inspect details that cost time

- Metrics receive `list[SampleScore]` only if the inner function is annotated
  that way; without the annotation, an older format (`list[Score]`) is passed.
- With several Python installs, `inspect` on the PATH may belong to another
  interpreter; `python -m inspect_ai` avoids it.
- A dict `Score.value` is averaged key by key over epochs by the default reducer.
- `inspect eval-retry <log>` reuses finished samples and reruns only the others.
- For OpenAI reasoning models, Inspect uses the Responses API by default;
  `-M responses_api=false` keeps the Chat Completions API that the study used.
