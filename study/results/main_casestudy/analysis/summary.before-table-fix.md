# Analysis

3 tasks, 5 runs, conditions ['SV', 'A', 'B', 'AB', 'ABp']. Pool and mutant definitions: see assure/scoring.py.
## RQ1: evaluation gap

| Benchmark | Cond. | Visible pass | Hidden pass | Gap |
|---|---|---|---|---|
| casestudy_v2 | SV | 100.0 | 100.0 | 0.0 |
| casestudy_v2 | A | 100.0 | 100.0 | 0.0 |
| casestudy_v2 | B | 100.0 | 100.0 | 0.0 |
| casestudy_v2 | AB | 100.0 | 100.0 | 0.0 |
| casestudy_v2 | ABp | 100.0 | 100.0 | 0.0 |
| svc_mistral | SV | 100.0 | 100.0 | 0.0 |
| svc_mistral | A | 100.0 | 100.0 | 0.0 |
| svc_mistral | B | 100.0 | 100.0 | 0.0 |
| svc_mistral | AB | 100.0 | 100.0 | 0.0 |
| svc_mistral | ABp | 100.0 | 100.0 | 0.0 |
| svc_qwen | SV | 100.0 | 100.0 | 0.0 |
| svc_qwen | A | 100.0 | 100.0 | 0.0 |
| svc_qwen | B | 100.0 | 100.0 | 0.0 |
| svc_qwen | AB | 100.0 | 100.0 | 0.0 |
| svc_qwen | ABp | 100.0 | 100.0 | 0.0 |

## RQ2: evidence quality per condition (median of per-task means)

| Cond. | Fault detection | Mutation score | False-oracle rate | Tokens (cond.) |
|---|---|---|---|---|
| SV | 84.7 | 95.2 | 0.0 | 0.0k |
| A | 93.3 | 96.3 | 14.3 | 67.4k |
| B | 93.3 | 96.0 | 8.0 | 76.4k |
| AB | 93.3 | 99.3 | 9.9 | 125.9k |
| ABp | 90.7 | 96.6 | 4.2 | 69.8k |

## RQ3: complementarity of Phase A and Phase B

Within AB (summed over task-runs): faults A-only/B-only/both = [27, 7, 186]; mutants A-only/B-only/both = [49, 12, 362]
Within ABp (summed over task-runs): faults A-only/B-only/both = [78, 13, 106]; mutants A-only/B-only/both = [92, 31, 293]
Conditions A vs B (separate verifiers): faults A-only/B-only/both = [4, 11, 205]; mutants = [7, 14, 404]

### Case study: seeded-fault detection (15 seeded faults, runs detecting / runs)

| Fault | SV | A | B | AB | ABp |
|---|---|---|---|---|---|
| F01 | 10/15 | 10/15 | 10/15 | 10/15 | 10/15 |
| F02 | 14/15 | 14/15 | 15/15 | 15/15 | 15/15 |
| F03 | 15/15 | 14/15 | 15/15 | 15/15 | 14/15 |
| F04 | 11/15 | 13/15 | 14/15 | 15/15 | 15/15 |
| F05 | 15/15 | 13/15 | 14/15 | 14/15 | 13/15 |
| F06 | 10/15 | 15/15 | 15/15 | 15/15 | 12/15 |
| F07 | 14/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| F08 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| F09 | 15/15 | 14/15 | 14/15 | 15/15 | 14/15 |
| F10 | 14/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| F11 | 10/15 | 10/15 | 12/15 | 12/15 | 9/15 |
| F12 | 10/15 | 12/15 | 13/15 | 14/15 | 9/15 |
| F13 | 13/15 | 14/15 | 14/15 | 15/15 | 9/15 |
| F14 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| F15 | 10/15 | 10/15 | 10/15 | 10/15 | 10/15 |

Case study, within AB: seeded faults A-only/B-only/both = [27, 7, 186]

Case study, within ABp: seeded faults A-only/B-only/both = [78, 13, 106]
Phase A reported at least one open question in 91.1% of task-runs.

## RQ4: release decisions, raw evidence, as a release gate sees it

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 0 | 0 | 15 | -- | -- |
| A | 0 | 0 | 13 | 2 | 0.0 | -- |
| B | 0 | 0 | 11 | 4 | 0.0 | -- |
| AB | 0 | 0 | 14 | 1 | 0.0 | -- |
| ABp | 0 | 0 | 4 | 11 | 0.0 | -- |

## RQ4: release decisions, valid tests only (false oracles removed)

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 0 | 0 | 15 | -- | -- |
| A | 0 | 0 | 0 | 15 | -- | -- |
| B | 0 | 0 | 0 | 15 | -- | -- |
| AB | 0 | 0 | 2 | 13 | 0.0 | -- |
| ABp | 0 | 0 | 0 | 15 | -- | -- |

## Protocol tests H1/H2 (PROTOCOL.md; own Holm family; confirmatory only for campaigns run after the freeze)

| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |
|---|---|---|---|---|---|---|---|---|
| H | H1 seeded-fault detection, AB vs SV | sign test over faults | 46 | 0.957 | 0.852 | 11+/1-/34= | 0.0063 | 0.0063 |
| H | H2 seeded-fault detection, AB vs ABp | sign test over faults | 46 | 0.957 | 0.857 | 13+/0-/33= | 0.0002 | 0.0005 |

## Exploratory tests (Holm-corrected, alpha = 0.05)

| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |
|---|---|---|---|---|---|---|---|---|
| RQ1 | SV visible vs hidden (evaluation gap) | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs AB | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs ABp | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs A | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs B | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ2 | Context independence SV vs AB (detection_rate) | Wilcoxon | 3 | 0.851 | 0.954 | A12=0.17 | 0.5000 | 1.0000 |
| RQ2 | Model independence AB vs ABp (detection_rate) | Wilcoxon | 3 | 0.954 | 0.851 | A12=1.00 | 0.2500 | 1.0000 |
| RQ2 | Context independence SV vs AB (mutation_score) | Wilcoxon | 3 | 0.923 | 0.984 | A12=0.11 | 0.2500 | 1.0000 |
| RQ2 | Model independence AB vs ABp (mutation_score) | Wilcoxon | 3 | 0.984 | 0.968 | A12=0.72 | 0.5000 | 1.0000 |
| RQ2 | Context independence SV vs AB (false_oracle_rate) | Wilcoxon | 3 | 0.011 | 0.089 | A12=0.00 | 0.2500 | 1.0000 |
| RQ2 | Model independence AB vs ABp (false_oracle_rate) | Wilcoxon | 3 | 0.089 | 0.065 | A12=0.67 | 0.7500 | 1.0000 |
| RQ3 | A vs B (detection_rate) | Wilcoxon | 3 | 0.906 | 0.937 | A12=0.39 | 0.5000 | 1.0000 |
| RQ3 | AB vs A (detection_rate) | Wilcoxon | 3 | 0.954 | 0.906 | A12=0.61 | 0.5000 | 1.0000 |
| RQ3 | AB vs B (detection_rate) | Wilcoxon | 3 | 0.954 | 0.937 | A12=0.61 | 0.5000 | 1.0000 |
| RQ3 | A vs B (mutation_score) | Wilcoxon | 3 | 0.956 | 0.973 | A12=0.44 | 0.5000 | 1.0000 |
| RQ3 | AB vs A (mutation_score) | Wilcoxon | 3 | 0.984 | 0.956 | A12=0.78 | 0.2500 | 1.0000 |
| RQ3 | AB vs B (mutation_score) | Wilcoxon | 3 | 0.984 | 0.973 | A12=0.61 | 1.0000 | 1.0000 |
| RQ4 | Faulty releases SV vs AB | McNemar | 15 | 0.000 | 0.000 | discordant 0/0 | 1.0000 | 1.0000 |
