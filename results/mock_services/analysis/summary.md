# Analysis

2 tasks, 1 runs, conditions ['SV', 'A', 'B', 'AB', 'ABp']. Pool and mutant definitions: see assure/scoring.py.
## RQ1: evaluation gap

| Benchmark | Cond. | Visible pass | Hidden pass | Gap |
|---|---|---|---|---|
| svc_mistral | SV | 100.0 | 100.0 | 0.0 |
| svc_mistral | A | 100.0 | 100.0 | 0.0 |
| svc_mistral | B | 100.0 | 100.0 | 0.0 |
| svc_mistral | AB | 100.0 | 100.0 | 0.0 |
| svc_mistral | ABp | 100.0 | 100.0 | 0.0 |
| svc_qwen | SV | 100.0 | 100.0 | 0.0 |
| svc_qwen | A | 100.0 | 100.0 | 0.0 |
| svc_qwen | B | 100.0 | 100.0 | 0.0 |
| svc_qwen | AB | 100.0 | 0.0 | 100.0 |
| svc_qwen | ABp | 100.0 | 0.0 | 100.0 |

## RQ2: evidence quality per condition (median of per-task means)

| Cond. | Fault detection | Mutation score | False-oracle rate | Tokens (cond.) |
|---|---|---|---|---|
| SV | 0.0 | 50.1 | 0.0 | 0.0k |
| A | 100.0 | 98.1 | 0.0 | 2.0k |
| B | 0.0 | 0.0 | 25.0 | 15.6k |
| AB | 100.0 | 98.1 | 3.4 | 27.1k |
| ABp | 100.0 | 98.1 | 3.5 | 35.7k |

## RQ3: complementarity of Phase A and Phase B

Within AB (summed over task-runs): faults A-only/B-only/both = [32, 0, 0]; mutants A-only/B-only/both = [55, 0, 0]
Within ABp (summed over task-runs): faults A-only/B-only/both = [32, 0, 0]; mutants A-only/B-only/both = [55, 0, 0]
Conditions A vs B (separate verifiers): faults A-only/B-only/both = [32, 0, 0]; mutants = [55, 0, 0]

### Case study: seeded-fault detection (15 seeded faults, runs detecting / runs)

| Fault | SV | A | B | AB | ABp |
|---|---|---|---|---|---|
| F01 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F02 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F03 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F04 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F05 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F06 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F07 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F08 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F09 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F10 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F11 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F12 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F13 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F14 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| F15 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 |

Case study, within AB: seeded faults A-only/B-only/both = [32, 0, 0]

Case study, within ABp: seeded faults A-only/B-only/both = [32, 0, 0]
Phase A reported at least one open question in 0.0% of task-runs.

## RQ4: release decisions, raw evidence, as a release gate sees it

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 0 | 0 | 2 | -- | -- |
| A | 0 | 0 | 0 | 2 | -- | -- |
| B | 0 | 0 | 1 | 1 | 0.0 | -- |
| AB | 1 | 0 | 0 | 1 | 100.0 | 100.0 |
| ABp | 1 | 0 | 1 | 0 | 50.0 | 100.0 |

## RQ4: release decisions, valid tests only (false oracles removed)

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 0 | 0 | 2 | -- | -- |
| A | 0 | 0 | 0 | 2 | -- | -- |
| B | 0 | 0 | 0 | 2 | -- | -- |
| AB | 1 | 0 | 0 | 1 | 100.0 | 100.0 |
| ABp | 1 | 0 | 0 | 1 | 100.0 | 100.0 |

## Protocol tests H1/H2 (PROTOCOL.md; own Holm family; confirmatory only for campaigns run after the freeze)

| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |
|---|---|---|---|---|---|---|---|---|
| H | H1 seeded-fault detection, AB vs SV | sign test over faults | 32 | 1.000 | 0.000 | 32+/0-/0= | 0.0000 | 0.0000 |
| H | H2 seeded-fault detection, AB vs ABp | sign test over faults | 32 | 1.000 | 1.000 | 0+/0-/32= | 1.0000 | 1.0000 |

## Exploratory tests (Holm-corrected, alpha = 0.05)

| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |
|---|---|---|---|---|---|---|---|---|
| RQ1 | SV visible vs hidden (evaluation gap) | McNemar | 2 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs AB | McNemar | 2 | 1.000 | 0.500 | discordant 1/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs ABp | McNemar | 2 | 1.000 | 0.500 | discordant 1/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs A | McNemar | 2 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs B | McNemar | 2 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ2 | Context independence SV vs AB (detection_rate) | Wilcoxon | 2 | 0.000 | 1.000 | A12=0.00 | 0.5000 | 1.0000 |
| RQ2 | Model independence AB vs ABp (detection_rate) | Wilcoxon | 2 | 1.000 | 1.000 | A12=0.50 | 1.0000 | 1.0000 |
| RQ2 | Context independence SV vs AB (mutation_score) | Wilcoxon | 2 | 0.501 | 0.981 | A12=0.00 | 0.5000 | 1.0000 |
| RQ2 | Model independence AB vs ABp (mutation_score) | Wilcoxon | 2 | 0.981 | 0.981 | A12=0.50 | 1.0000 | 1.0000 |
| RQ2 | Context independence SV vs AB (false_oracle_rate) | Wilcoxon | 2 | 0.000 | 0.034 | A12=0.25 | 1.0000 | 1.0000 |
| RQ2 | Model independence AB vs ABp (false_oracle_rate) | Wilcoxon | 2 | 0.034 | 0.035 | A12=0.50 | 1.0000 | 1.0000 |
| RQ3 | A vs B (detection_rate) | Wilcoxon | 2 | 1.000 | 0.000 | A12=1.00 | 0.5000 | 1.0000 |
| RQ3 | AB vs A (detection_rate) | Wilcoxon | 2 | 1.000 | 1.000 | A12=0.50 | 1.0000 | 1.0000 |
| RQ3 | AB vs B (detection_rate) | Wilcoxon | 2 | 1.000 | 0.000 | A12=1.00 | 0.5000 | 1.0000 |
| RQ3 | A vs B (mutation_score) | Wilcoxon | 2 | 0.981 | 0.000 | A12=1.00 | 0.5000 | 1.0000 |
| RQ3 | AB vs A (mutation_score) | Wilcoxon | 2 | 0.981 | 0.981 | A12=0.50 | 1.0000 | 1.0000 |
| RQ3 | AB vs B (mutation_score) | Wilcoxon | 2 | 0.981 | 0.000 | A12=1.00 | 0.5000 | 1.0000 |
| RQ4 | Faulty releases SV vs AB | McNemar | 2 | 0.000 | 0.000 | discordant 0/0 | 1.0000 | 1.0000 |
