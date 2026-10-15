# Pre-registered protocol: main campaign (FROZEN 2026-10-14 22:05)

Status: **FROZEN on 2026-10-14 22:05** by the first author. Hashes of section 5 checked at freeze: unchanged. Archive: `frozen/protocol_freeze_2026-10-14.zip` (its SHA-256 is in section 12). The items marked **[DECIDE-n]** must be settled
first. The protocol is frozen when the decision log below is complete, the
hashes are recomputed, and the file is committed or archived with a date.
No main-campaign unit may run before that.

## 1. What is already known (exploratory data, never pooled with the main campaign)

| Data | Location | Role |
|---|---|---|
| EvalPlus pilot, 20 tasks x 1 run, `max_tokens` 8192 | `results/pilot/` | ceiling effect: 1 faulty program in 20 |
| Case study v1, 3 runs | `results/pilot_casestudy/` | builder correct 3/3; SV detects 9-10/10 seeded faults; verifiers 8-10/10 with 5-29% false oracles |
| Case study v2, 3 runs | `results/pilot_casestudy_v2/` | builder correct 3/3; on F11-F13, SV 0/9, AB 8/9, ABp 0/9 |

Case study v2 was designed **after** the v1 results were seen
(`data/casestudy_v2/DESIGN.md`). Its pilot is therefore exploratory, and it is
the source of the hypotheses below. Only data collected after the freeze are
confirmatory.

## 2. Claim under test [DECIDE-1]

The pilot data do not show the mechanism currently stated in the paper (code
and tests sharing one misreading of S): the builder's code was correct in
every run. They show instead that the builder's tests miss subtle interactions
its code handles correctly. Proposed wording for the confirmatory claim:

> Evidence produced by an independent verifier (condition AB) detects more
> seeded faults than the builder's own tests (SV), on faults that violate
> behavior fixed by S; the cost is a higher rate of false oracles, which the
> counterexample loop exposes.

## 3. Confirmatory hypotheses (one Holm family, alpha = 0.05, two-sided)

- **H1 (context independence).** Detection of seeded faults: AB > SV.
- **H2 (model independence).** Detection of seeded faults: AB vs ABp, no
  predicted direction. The v1 pilot (mutation score) and the v2 pilot
  (detection) pointed in opposite directions.

Everything else is exploratory and reported as such: false-oracle rates,
release decisions (RQ4), Phase A / Phase B complementarity (RQ3), mutation
scores, and the type O coding.

## 4. Unit of analysis and test [DECIDE-2]

The same seeded faults are reused in every run, so (run, fault) pairs are not
independent. Options:

| Option | Test | Comment |
|---|---|---|
| **a (recommended)** | Exact sign test over faults, on the per-fault detection rate averaged over runs (ties dropped) | honest unit; **underpowered with the current faults**: with only the 5 faults that separated SV and AB in the v2 pilot, even a perfect result gives p = 0.0625. Needs at least 6 informative faults (p = 0.031), better 8 or more (p = 0.008) |
| b | Exact McNemar over (run, fault) pairs | in the v2 pilot, 13 vs 0 discordant pairs, p of about 0.0002; but it treats repeated faults as independent and overstates the evidence |
| c | Option a as primary, option b as a reported sensitivity analysis | |

Analysis of the v2 pilot with option a, exploratory only: 5 faults favor AB,
0 favor SV, 9 ties; p = 0.0625 (Holm 0.125). This matches the power limit above.

With option a, power depends on the number of seeded faults that S fixes but
the builder's tests may miss. That number must be raised **by design, before
the main campaign** (see [DECIDE-5]).

## 5. Frozen materials

Models: builder and verifier `claude-sonnet-5-5`; alternative verifier
`gpt-5.5-2026-04-23`. Thinking/effort: provider defaults, not set (Sonnet 5.5:
adaptive, effort high). Temperature: provider default. `max_tokens` 64000 for
every role. Anthropic calls are streamed. Refusal fallbacks are **not**
enabled, because a silent switch to another model would bias the comparison
between conditions.

Budgets: self_rounds 5, cex_rounds 3, inner_repair_rounds 2,
max_counterexamples 5, phase_b_mutants 30, phase_b_survivors_shown 6,
hypothesis_max_examples 100, scoring_max_examples 50, scoring_mutants 30.
Prompts: `PROMPT_VERSION` 2026-10-08.2.

SHA-256 (first 16 hex digits), checked at the freeze (unchanged since the snapshot of
2026-10-14). Any later change to these files is a deviation and must be logged.

| File | Hash |
|---|---|
| data/casestudy_v2/spec.md | 293699bc2ad6256a |
| data/casestudy_v2/reference.py | 8b5ddf78652db859 |
| data/casestudy_v2/gateway.py | cd21a9e28325c52e |
| data/casestudy_v2/visible_tests.py | 2a5a431c7d71a84f |
| data/casestudy_v2/hidden_tests.py | cc7e5faa4161f79d |
| data/casestudy_v2/faults.py | c90d215b3da163bd |
| data/service_mistral/spec.md | 4b6986ae7f290fd0 |
| data/service_mistral/reference.py | 3de18d71cea15309 |
| data/service_mistral/visible_tests.py | 2555ca5a8cba5ecb |
| data/service_mistral/hidden_tests.py | 32e27b7f85e9fa16 |
| data/service_mistral/faults.py | 82d48c8bb77ebe26 |
| data/service_qwen/spec.md | ef78a86b4e6b0fda |
| data/service_qwen/reference.py | 409e83156bf51873 |
| data/service_qwen/visible_tests.py | f19be7c0d62f95a4 |
| data/service_qwen/hidden_tests.py | 6631a06fca5fb1c1 |
| data/service_qwen/faults.py | 3495ec96983597b2 |
| assure/prompts.py | ba64b61e475e3be4 |
| assure/scoring.py | 5318bb8333ec6294 |
| assure/analyze.py | 4f391481dc62f929 |
| assure/agents.py | bae11df9a1bb2810 |
| assure/pipeline.py | 7a2b68370ac8b832 |
| assure/llm.py | 3b099ec4f0deefc7 |
| assure/_runner.py | 9308d1bc0a6b355d |
| assure/sandbox.py | 02e33d38fcc14a41 |
| assure/mutation.py | cc41892e8fc8def1 |
| assure/data.py | 8342f36befe541bb |
| configs/main_casestudy.yaml | 9dd84226d9ebbcc7 |

## 6. Campaign [DECIDE-3, DECIDE-4, DECIDE-5]

- **[DECIDE-3] Runs of the case study:** recommended 5 (about 2.7M tokens for v2).
- **[DECIDE-4] EvalPlus:** the planned 80 tasks x 3 runs (about 10M tokens) is
  expected to show only the ceiling effect. Recommended: keep the pilot as is,
  report it as exploratory, and spend the budget on the case study.
- **[DECIDE-5] More seeded faults and/or a second service.** Resolved
  (section 11): two additional services, each with its own S, T_v, T_h and
  seeded faults, written by third-party models that are not under study
  (`second_service_kit/answers/MODELS.md`). The campaign covers three services:

  | Benchmark | Service | Author | Seeded faults | Hidden tests |
  |---|---|---|---|---|
  | `casestudy_v2` | documents and payments, v2 | the authors (`data/casestudy_v2/DESIGN.md`) | 14 | 39 |
  | `svc_mistral` | room booking | Mistral Medium 3.5 | 17 | 27 |
  | `svc_qwen` | equipment loans | Qwen 3.7-Plus | 15 | 27 |

  H1 and H2 are tested over all 46 faults as units. Neither new service has
  been run with real models before the freeze: only an offline mock run
  (`configs/mock_services.yaml`) checked the plumbing. Config:
  `configs/main_casestudy.yaml` (5 runs, three services).

## 7. Execution rules

1. Before each run: a minimal call to every backend (`preflight`).
2. An interrupted unit is resumed by replaying its partial transcript
   (`runK.partial.transcript.json`). A replay mismatch stops the unit.
3. No run is discarded. Every unit is reported, including failures and their causes.
4. If a pinned model becomes unavailable, the campaign stops, and the deviation
   is logged in section 10.
5. Scoring and analysis run only after all units are complete.

## 8. Metrics (definitions in `assure/scoring.py`)

As implemented, plus one open point:

- **[DECIDE-6] False oracles on type O items.** The current definition (a test
  that fails on the reference) depends, for type O items, on an arbitrary
  choice of the reference. Example from the v2 pilot: for O2 the reference uses
  `lower()`, so the three AB tests that required Unicode case folding were
  counted as false oracles. Options: (a) keep the definition and report these
  tests separately; (b) exclude tests on type O items from the false-oracle
  rate. Both need an explicit rule; (b) changes a metric.

## 9. Type O coding

As defined in `data/casestudy_v2/DESIGN.md`. The coder pre-fills the grid with
`data/casestudy_v2/o_coding.py`, then confirms or corrects every keyword
candidate in the `coder_*` columns, before reading the detection scores of the
same campaign. Coder: the first author. Deviation: the v2 pilot was coded
after its scores had been seen (section 10).

## 10. Deviation log

| Date | Deviation |
|---|---|
| 2026-10-13 | v2 pilot: type O grid prepared after its detection scores had been seen |
| 2026-10-14 | DECIDE-5: the additional services were written by third-party models (Mistral Medium 3.5, Qwen 3.7-Plus) instead of a human author who had not seen the results. They are not models under study. Their authors received only `second_service_kit/PROMPT_LLM.md` and the validator's findings |
| 2026-10-14 | The planned human review of the hidden tests was replaced by a cross-review by a third-party model (each service reviewed by a model other than its author, never Claude or GPT) and mechanical checks (status codes absent from the spec, tests reading internal state). A first, informal review by an unrecorded model is not used |
| 2026-10-14 | A third service (Gemini 3, library loans) was dropped after six correction rounds did not converge; it was never run |
| 2026-10-15 | After the runs, `data/casestudy_v2/o_coding.py` (a tool, not a frozen file) was changed only to keep the casestudy_v2 units of a multi-service campaign; no other change |
| 2026-10-15 | Type O coding (section 9) done by a third-party model (Qwen 3.7-Plus) instead of the first author, with `results/main_casestudy/analysis/O_coding/PROMPT_O_CODING_qwen.md`, before any detection score was read. The prompt contains the item definitions and the 38 cases with keyword candidates; it contains neither the intents R nor any detection result. The 87 cases without any candidate are coded raised = no, tested = 0, disputed = no by rule |
| 2026-10-15 | Bug fix in a frozen file, `assure/analyze.py` (hash 00b825de86b179b5 -> 3bfa058d91d158b2): the descriptive per-fault table `seeded_table` used the fault list of the first service only and pooled detections of all services under the same fault ids. It now gives one table per service, plus per-service macros `resSeedDet<cond><service>`. The confirmatory tests H1/H2 were not affected: `stats.csv` is byte-identical before and after (copies kept as `analysis/*.before-table-fix.*`). Regression test added |
| 2026-10-15 | Measurement defect found after the runs: the frozen runner calls every test function without arguments, so verifier tests written with `pytest.mark.parametrize` (or a pytest fixture) failed with TypeError on every program, including the reference. They were counted as invalid (excluded from detection, so H1/H2 are conservative) and as failures by the raw release gate. Decomposition with `scripts/runner_artifact.py`: of the invalid verifier tests, 282 of 323 are runner-incompatible; genuine false-oracle rates are 0.7-2.3% (SV 0.6%). |
| 2026-10-15 | Frozen files changed to support an **exploratory** rescoring (`assure/_runner.py` 9308d1bc0a6b355d -> 8353c583181da59f, `assure/sandbox.py` 02e33d38fcc14a41 -> adf5f359ec7c6496, `assure/scoring.py` 5318bb8333ec6294 -> 570c0dd58d90c140): an opt-in option `scoring_expand_parametrize` runs parametrize cases (one test passes only if all its cases pass). The default is off and the frozen behavior is unchanged: rescoring a copy of the v2 pilot with the option off gives a byte-identical `scores.jsonl`. Exploratory campaign `results/main_casestudy_rescored/` (same units, no model call, `configs/main_casestudy_rescored.yaml`): H1 11/0, p = 0.001; H2 10/0, p = 0.002. The confirmatory results remain those of `results/main_casestudy/`. Counterexample rounds during the runs cannot be replayed: some builders received counterexamples that were TypeErrors (they rejected them) |

## 11. Decision log (complete before freezing)

| Item | Decision | Date |
|---|---|---|
| DECIDE-1 claim | Wording of section 2 | 2026-10-13 |
| DECIDE-2 unit and test | Option a: exact sign test over faults, per-fault detection rate averaged over runs, ties dropped; H1 and H2 form their own Holm family (`Analysis.confirmatory` in `assure/analyze.py`) | 2026-10-13 |
| DECIDE-3 runs | 5 runs per service | 2026-10-13 |
| DECIDE-4 EvalPlus scope | No main EvalPlus campaign; the pilot is reported as exploratory | 2026-10-13 |
| DECIDE-5 faults / second service | Two services written by third-party models, validated (`second_service_kit/validate.py`, and through the harness), cross-reviewed, mechanically checked; see section 6 and the deviation log. Planned initially: a human author who had not seen the pilot results | 2026-10-14 |
| DECIDE-6 false oracles on type O | Option a, confirmed: keep the definition, report separately the tests on type O items (identified by the confirmed coding), with and without them | 2026-10-14 |

## 12. Freeze record

| Item | Value |
|---|---|
| Frozen at | 2026-10-14 22:05 |
| Archive | `frozen/protocol_freeze_2026-10-14.zip` (34 files; the archived PROTOCOL.md predates this section) |
| Archive SHA-256 | `d4e8071114a0996ffce9a9fd3bf0b29bb18c2a366eab2f77626b24b783d6b69b` |
| Main campaign config | `configs/main_casestudy.yaml` |
