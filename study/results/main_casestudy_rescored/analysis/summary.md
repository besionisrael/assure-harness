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
| A | 93.3 | 100.0 | 2.1 | 67.4k |
| B | 93.3 | 100.0 | 1.2 | 76.4k |
| AB | 94.3 | 100.0 | 0.5 | 125.9k |
| ABp | 90.7 | 98.6 | 3.3 | 69.8k |

## RQ3: complementarity of Phase A and Phase B

Within AB (summed over task-runs): faults A-only/B-only/both = [26, 4, 191]; mutants A-only/B-only/both = [43, 0, 386]
Within ABp (summed over task-runs): faults A-only/B-only/both = [77, 12, 111]; mutants A-only/B-only/both = [93, 27, 300]
Conditions A vs B (separate verifiers): faults A-only/B-only/both = [2, 5, 214]; mutants = [2, 1, 427]

### Seeded-fault detection, casestudy_v2 (14 seeded faults, runs detecting / runs)

| Fault | SV | A | B | AB | ABp |
|---|---|---|---|---|---|
| F01 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F02 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F03 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F04 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F05 | 5/5 | 5/5 | 5/5 | 5/5 | 3/5 |
| F06 | 1/5 | 5/5 | 5/5 | 5/5 | 2/5 |
| F07 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F08 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F09 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F10 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F11 | 0/5 | 0/5 | 2/5 | 2/5 | 0/5 |
| F12 | 0/5 | 2/5 | 3/5 | 4/5 | 0/5 |
| F13 | 3/5 | 5/5 | 5/5 | 5/5 | 1/5 |
| F14 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |

### Seeded-fault detection, svc_mistral (17 seeded faults, runs detecting / runs)

| Fault | SV | A | B | AB | ABp |
|---|---|---|---|---|---|
| F01 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F02 | 4/5 | 4/5 | 5/5 | 5/5 | 5/5 |
| F03 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F04 | 1/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F05 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F06 | 4/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F07 | 4/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F08 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F09 | 5/5 | 5/5 | 4/5 | 5/5 | 4/5 |
| F10 | 4/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F11 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F12 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F13 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F14 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F15 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F16 | 4/5 | 5/5 | 5/5 | 5/5 | 4/5 |
| F17 | 1/5 | 5/5 | 5/5 | 5/5 | 3/5 |

### Seeded-fault detection, svc_qwen (15 seeded faults, runs detecting / runs)

| Fault | SV | A | B | AB | ABp |
|---|---|---|---|---|---|
| F01 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 |
| F02 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F03 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F04 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F05 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F06 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F07 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F08 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F09 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F10 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F11 | 5/5 | 5/5 | 5/5 | 5/5 | 4/5 |
| F12 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F13 | 5/5 | 5/5 | 5/5 | 5/5 | 4/5 |
| F14 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| F15 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |

Case study, within AB: seeded faults A-only/B-only/both = [26, 4, 191]

Case study, within ABp: seeded faults A-only/B-only/both = [77, 12, 111]
Phase A reported at least one open question in 91.1% of task-runs.

## RQ4: release decisions, raw evidence, as a release gate sees it

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 0 | 0 | 15 | -- | -- |
| A | 0 | 0 | 6 | 9 | 0.0 | -- |
| B | 0 | 0 | 6 | 9 | 0.0 | -- |
| AB | 0 | 0 | 8 | 7 | 0.0 | -- |
| ABp | 0 | 0 | 0 | 15 | -- | -- |

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
| H | H1 seeded-fault detection, AB vs SV | sign test over faults | 46 | 0.961 | 0.852 | 11+/0-/35= | 0.0010 | 0.0020 |
| H | H2 seeded-fault detection, AB vs ABp | sign test over faults | 46 | 0.961 | 0.870 | 10+/0-/36= | 0.0020 | 0.0020 |

## Exploratory tests (Holm-corrected, alpha = 0.05)

| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |
|---|---|---|---|---|---|---|---|---|
| RQ1 | SV visible vs hidden (evaluation gap) | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs AB | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs ABp | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs A | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs B | McNemar | 15 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ2 | Context independence SV vs AB (detection_rate) | Wilcoxon | 3 | 0.851 | 0.959 | A12=0.06 | 0.5000 | 1.0000 |
| RQ2 | Model independence AB vs ABp (detection_rate) | Wilcoxon | 3 | 0.959 | 0.863 | A12=0.78 | 0.2500 | 1.0000 |
| RQ2 | Context independence SV vs AB (mutation_score) | Wilcoxon | 3 | 0.923 | 0.998 | A12=0.00 | 0.2500 | 1.0000 |
| RQ2 | Model independence AB vs ABp (mutation_score) | Wilcoxon | 3 | 0.998 | 0.978 | A12=0.78 | 0.5000 | 1.0000 |
| RQ2 | Context independence SV vs AB (false_oracle_rate) | Wilcoxon | 3 | 0.011 | 0.009 | A12=0.33 | 1.0000 | 1.0000 |
| RQ2 | Model independence AB vs ABp (false_oracle_rate) | Wilcoxon | 3 | 0.009 | 0.026 | A12=0.11 | 0.2500 | 1.0000 |
| RQ3 | A vs B (detection_rate) | Wilcoxon | 3 | 0.936 | 0.950 | A12=0.44 | 1.0000 | 1.0000 |
| RQ3 | AB vs A (detection_rate) | Wilcoxon | 3 | 0.959 | 0.936 | A12=0.72 | 0.5000 | 1.0000 |
| RQ3 | AB vs B (detection_rate) | Wilcoxon | 3 | 0.959 | 0.950 | A12=0.72 | 0.5000 | 1.0000 |
| RQ3 | A vs B (mutation_score) | Wilcoxon | 3 | 0.998 | 0.996 | A12=0.56 | 1.0000 | 1.0000 |
| RQ3 | AB vs A (mutation_score) | Wilcoxon | 3 | 0.998 | 0.998 | A12=0.50 | 1.0000 | 1.0000 |
| RQ3 | AB vs B (mutation_score) | Wilcoxon | 3 | 0.998 | 0.996 | A12=0.56 | 1.0000 | 1.0000 |
| RQ4 | Faulty releases SV vs AB | McNemar | 15 | 0.000 | 0.000 | discordant 0/0 | 1.0000 | 1.0000 |
