# Analysis

3 tasks, 3 runs, conditions ['SV', 'A', 'B', 'AB', 'ABp']. Pool and mutant definitions: see assure/scoring.py.
## RQ1: evaluation gap

| Benchmark | Cond. | Visible pass | Hidden pass | Gap |
|---|---|---|---|---|
| humaneval | SV | 100.0 | 83.3 | 16.7 |
| humaneval | A | 100.0 | 100.0 | 0.0 |
| humaneval | B | 100.0 | 100.0 | 0.0 |
| humaneval | AB | 100.0 | 83.3 | 16.7 |
| humaneval | ABp | 100.0 | 83.3 | 16.7 |
| casestudy | SV | 100.0 | 33.3 | 66.7 |
| casestudy | A | 100.0 | 66.7 | 33.3 |
| casestudy | B | 100.0 | 33.3 | 66.7 |
| casestudy | AB | 100.0 | 66.7 | 33.3 |
| casestudy | ABp | 100.0 | 100.0 | 0.0 |

## RQ2: evidence quality per condition (median of per-task means)

| Cond. | Fault detection | Mutation score | False-oracle rate | Tokens (cond.) |
|---|---|---|---|---|
| SV | 16.7 | 90.0 | 0.0 | 0.0k |
| A | 100.0 | 92.2 | 8.3 | 8.6k |
| B | 94.4 | 95.6 | 16.7 | 16.8k |
| AB | 100.0 | 98.9 | 23.3 | 25.2k |
| ABp | 100.0 | 96.7 | 16.7 | 21.0k |

## RQ3: complementarity of Phase A and Phase B

Within AB (summed over task-runs): faults A-only/B-only/both = [31, 2, 18]; mutants A-only/B-only/both = [87, 10, 85]
Within ABp (summed over task-runs): faults A-only/B-only/both = [32, 2, 16]; mutants A-only/B-only/both = [87, 9, 84]
Conditions A vs B (separate verifiers): faults A-only/B-only/both = [31, 0, 20]; mutants = [87, 9, 86]

### Case study: seeded-fault detection (10 seeded faults, runs detecting / runs)

| Fault | SV | A | B | AB | ABp |
|---|---|---|---|---|---|
| F01 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| F02 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| F03 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| F04 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| F05 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| F06 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| F07 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| F08 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| F09 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| F10 | 0/3 | 3/3 | 0/3 | 3/3 | 3/3 |

Case study, within AB: seeded faults A-only/B-only/both = [30, 0, 0]

Case study, within ABp: seeded faults A-only/B-only/both = [30, 0, 0]
Phase A reported at least one open question in 0.0% of task-runs.

## RQ4: release decisions, raw evidence, as a release gate sees it

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 3 | 0 | 6 | -- | 0.0 |
| A | 1 | 0 | 3 | 5 | 25.0 | 100.0 |
| B | 0 | 2 | 4 | 3 | 0.0 | 0.0 |
| AB | 2 | 0 | 6 | 1 | 25.0 | 100.0 |
| ABp | 1 | 0 | 7 | 1 | 12.5 | 100.0 |

## RQ4: release decisions, valid tests only (false oracles removed)

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 3 | 0 | 6 | -- | 0.0 |
| A | 1 | 0 | 0 | 8 | 100.0 | 100.0 |
| B | 0 | 2 | 0 | 7 | -- | 0.0 |
| AB | 2 | 0 | 0 | 7 | 100.0 | 100.0 |
| ABp | 1 | 0 | 0 | 8 | 100.0 | 100.0 |

## Statistical tests (Holm-corrected, alpha = 0.05)

| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |
|---|---|---|---|---|---|---|---|---|
| RQ1 | SV visible vs hidden (evaluation gap) | McNemar | 9 | 1.000 | 0.667 | discordant 3/0 | 0.2500 | 1.0000 |
| RQ1 | Final correctness SV vs AB | McNemar | 9 | 0.667 | 0.778 | discordant 2/3 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs ABp | McNemar | 9 | 0.667 | 0.889 | discordant 1/3 | 0.6250 | 1.0000 |
| RQ1 | Final correctness SV vs A | McNemar | 9 | 0.667 | 0.889 | discordant 0/2 | 0.5000 | 1.0000 |
| RQ1 | Final correctness SV vs B | McNemar | 9 | 0.667 | 0.778 | discordant 0/1 | 1.0000 | 1.0000 |
| RQ2 | Context independence SV vs AB (detection_rate) | Wilcoxon | 3 | 0.389 | 1.000 | A12=0.17 | 0.5000 | 1.0000 |
| RQ2 | Model independence AB vs ABp (detection_rate) | Wilcoxon | 3 | 1.000 | 0.981 | A12=0.67 | 1.0000 | 1.0000 |
| RQ2 | Context independence SV vs AB (mutation_score) | Wilcoxon | 3 | 0.789 | 0.974 | A12=0.28 | 0.5000 | 1.0000 |
| RQ2 | Model independence AB vs ABp (mutation_score) | Wilcoxon | 3 | 0.974 | 0.967 | A12=0.56 | 1.0000 | 1.0000 |
| RQ2 | Context independence SV vs AB (false_oracle_rate) | Wilcoxon | 3 | 0.000 | 0.219 | A12=0.00 | 0.2500 | 1.0000 |
| RQ2 | Model independence AB vs ABp (false_oracle_rate) | Wilcoxon | 3 | 0.219 | 0.132 | A12=0.78 | 0.2500 | 1.0000 |
| RQ3 | A vs B (detection_rate) | Wilcoxon | 3 | 1.000 | 0.648 | A12=0.83 | 0.5000 | 1.0000 |
| RQ3 | AB vs A (detection_rate) | Wilcoxon | 3 | 1.000 | 1.000 | A12=0.50 | 1.0000 | 1.0000 |
| RQ3 | AB vs B (detection_rate) | Wilcoxon | 3 | 1.000 | 0.648 | A12=0.83 | 0.5000 | 1.0000 |
| RQ3 | A vs B (mutation_score) | Wilcoxon | 3 | 0.841 | 0.652 | A12=0.33 | 1.0000 | 1.0000 |
| RQ3 | AB vs A (mutation_score) | Wilcoxon | 3 | 0.974 | 0.841 | A12=0.94 | 0.5000 | 1.0000 |
| RQ3 | AB vs B (mutation_score) | Wilcoxon | 3 | 0.974 | 0.652 | A12=0.61 | 0.5000 | 1.0000 |
| RQ4 | Faulty releases SV vs AB | McNemar | 9 | 0.333 | 0.000 | discordant 3/0 | 0.2500 | 1.0000 |
