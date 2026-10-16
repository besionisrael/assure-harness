# assure: experimental harness for "Who Verifies the Builder?"

This harness runs the controlled study of the paper *Who Verifies the Builder? Toward Independent Assurance for Agent-Produced Software*. It compares self-validation by a coding agent with independent verification, on three stateful services with seeded faults (main campaign, `configs/main_casestudy.yaml`) and on an exploratory pilot of EvalPlus tasks (HumanEval+ and MBPP+).

Run every command below from this folder (`cd study`). The Inspect evaluation derived from this study is in [`../inspect_eval/`](../inspect_eval/).

## Design in one paragraph

For each task and run, the **builder** receives the specification `S` and the visible tests `T_v`. It writes a program and its own tests, then iterates on the results of both suites for at most five rounds. The result, `P0`, together with the builder's conversation, is the shared starting point of every condition, so that differences between conditions come from the evidence alone. In **SV**, `P0` is final and the builder's tests are the evidence. In **A**, **B**, **AB**, and **ABp**, a **verifier** in a fresh context produces frozen evidence:

- **Phase A** is specification-first and sees only `S` and the function name.
- **Phase B** is implementation-aware. It sees `P0` read-only, then the mutants of `P0` that survive its tests.

The evidence is run on the current program, and failures go back to the builder as counterexamples. A counterexample gives the guarantee, the observed behavior and the falsifying input, never the test code. This loop runs for at most three rounds. **ABp** uses a verifier from another provider. The hidden suite `T_h` (EvalPlus plus inputs) is never shown to any agent and is used only for scoring.

| Condition | Evidence produced by | Sees S | Sees T_v | Sees P |
|---|---|---|---|---|
| SV | builder | yes | yes | yes (own) |
| A | verifier, Phase A | yes | no | no |
| B | verifier, Phase B (mutation-guided) | yes | no | yes, read-only |
| AB | verifier, A frozen then B | yes | no | after A |
| ABp | as AB, other model/provider | yes | no | after A |

## Install

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q tests          # harness self-tests
```

The EvalPlus datasets are in `data/` (HumanEval+ v0.1.10, MBPP+ v0.2.0). Expected outputs are computed once from the canonical solutions and cached in `data/cache/`.

**Safety.** The harness executes code written by language models. Each execution runs in a separate interpreter with time and memory limits. These limits do not isolate the network or the file system, so run the harness in the provided container:

```bash
docker build -t assure .
docker run --rm -e ANTHROPIC_API_KEY -e OPENAI_API_KEY -v "$PWD/results:/app/results" assure run --config configs/pilot.yaml
```

## Run

```bash
export ANTHROPIC_API_KEY=...   # builder and same-model verifier
export OPENAI_API_KEY=...      # alternative verifier (condition ABp)

python3 -m assure plan    --config configs/pilot.yaml   # experiment size
python3 -m assure run     --config configs/pilot.yaml   # resumable: finished units are skipped
python3 -m assure score   --config configs/pilot.yaml   # resumable: scored tasks are skipped
python3 -m assure analyze --config configs/pilot.yaml   # statistics and LaTeX macros
```

`configs/mock.yaml` runs the whole pipeline offline with a simulated backend. It validates the plumbing only, and its numbers have no scientific meaning.

**Recommended order:**

1. Run the pilot (20 tasks, 1 run).
2. Read a few transcripts in `results/pilot/units/*/*/run0.transcript.json`.
3. Check the cost per unit.
4. Freeze `assure/prompts.py`.
5. Launch `configs/main.yaml`.

## Outputs

```
results/<campaign>/
  config.json                       exact configuration used
  units/<bench>/<task>/runK.json    programs, evidence, counterexample rounds, tokens
  units/<bench>/<task>/runK.transcript.json   every prompt and response
  scores.jsonl                      one row per (task, run, condition)
  analysis/summary.md               all research questions, readable
  analysis/stats.csv                every test, raw and Holm-adjusted p-values
  analysis/results_macros.tex       numbers for the paper
```

Copy `analysis/results_macros.tex` next to `main.tex`. The paper's tables read it through `\res{...}` and print TBD for missing values.

## Metric definitions (assure/scoring.py)

- **False oracle**: a test that fails on the canonical solution. False oracles are excluded from detection metrics.
- **Fault pool** of a task: every distinct program, from any run and condition, that fails `T_v` or `T_h`.
- **Detection rate**: the fraction of the pool on which at least one valid test fails.
- **Mutation score**: computed on first-order mutants of the canonical solution. Mutants that `T_v ∪ T_h` cannot detect are treated as likely equivalent and excluded.
- **Verdict**: *release* if the final program passes `T_v` and all tests of the evidence, *block* otherwise. It is computed twice: on the raw evidence, as a release gate would see it, and on valid tests only.
- **Statistics**: exact McNemar test over (task, run) pairs for binary outcomes. Wilcoxon signed-rank test over per-task means with the Vargha–Delaney Â12 effect size for continuous outcomes. Holm correction over the family of tests.

## Layout

```
assure/_runner.py   sandboxed evaluation (runs in a separate interpreter)
assure/sandbox.py   process launch, limits, crash isolation
assure/data.py      EvalPlus loading, expected outputs
assure/mutation.py  AST mutation operators (AOR, ROR, LCR, UOD, UOI, CRP, BCR)
assure/llm.py       Anthropic, OpenAI-compatible, and mock backends
assure/prompts.py   all prompts (shared template across roles)
assure/agents.py    builder and verifier roles, counterexamples
assure/pipeline.py  experimental conditions
assure/scoring.py   metrics
assure/analyze.py   statistics and LaTeX output
```
