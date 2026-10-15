# Analysis

20 tasks, 1 runs, conditions ['SV', 'A', 'B', 'AB', 'ABp']. Pool and mutant definitions: see assure/scoring.py.
## RQ1: evaluation gap

| Benchmark | Cond. | Visible pass | Hidden pass | Gap |
|---|---|---|---|---|
| humaneval | SV | 100.0 | 100.0 | 0.0 |
| humaneval | A | 100.0 | 100.0 | 0.0 |
| humaneval | B | 100.0 | 100.0 | 0.0 |
| humaneval | AB | 100.0 | 100.0 | 0.0 |
| humaneval | ABp | 100.0 | 100.0 | 0.0 |
| mbpp | SV | 100.0 | 90.0 | 10.0 |
| mbpp | A | 100.0 | 90.0 | 10.0 |
| mbpp | B | 100.0 | 90.0 | 10.0 |
| mbpp | AB | 100.0 | 90.0 | 10.0 |
| mbpp | ABp | 100.0 | 90.0 | 10.0 |

## RQ2: evidence quality per condition (median of per-task means)

| Cond. | Fault detection | Mutation score | False-oracle rate | Tokens (cond.) |
|---|---|---|---|---|
| SV | 0.0 | 100.0 | 0.0 | 0.0k |
| A | 0.0 | 100.0 | 0.0 | 3.4k |
| B | 0.0 | 100.0 | 0.0 | 3.9k |
| AB | 0.0 | 100.0 | 0.0 | 13.3k |
| ABp | 0.0 | 100.0 | 0.0 | 12.8k |

## RQ3: complementarity of Phase A and Phase B

Within AB (summed over task-runs): faults A-only/B-only/both = [0, 0, 0]; mutants A-only/B-only/both = [2, 1, 241]
Within ABp (summed over task-runs): faults A-only/B-only/both = [0, 0, 0]; mutants A-only/B-only/both = [3, 31, 209]
Conditions A vs B (separate verifiers): faults A-only/B-only/both = [0, 0, 0]; mutants = [0, 4, 241]
Phase A reported at least one open question in 68.3% of task-runs.

## RQ4: release decisions, raw evidence, as a release gate sees it

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 1 | 0 | 19 | -- | 0.0 |
| A | 1 | 0 | 3 | 16 | 25.0 | 100.0 |
| B | 0 | 1 | 2 | 17 | 0.0 | 0.0 |
| AB | 0 | 1 | 5 | 14 | 0.0 | 0.0 |
| ABp | 0 | 1 | 6 | 13 | 0.0 | 0.0 |

## RQ4: release decisions, valid tests only (false oracles removed)

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 1 | 0 | 19 | -- | 0.0 |
| A | 0 | 1 | 0 | 19 | -- | 0.0 |
| B | 0 | 1 | 0 | 19 | -- | 0.0 |
| AB | 0 | 1 | 0 | 19 | -- | 0.0 |
| ABp | 0 | 1 | 0 | 19 | -- | 0.0 |

## Statistical tests (Holm-corrected, alpha = 0.05)

| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |
|---|---|---|---|---|---|---|---|---|
| RQ1 | SV visible vs hidden (evaluation gap) | McNemar | 20 | 1.000 | 0.950 | discordant 1/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs AB | McNemar | 20 | 0.950 | 0.950 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs ABp | McNemar | 20 | 0.950 | 0.950 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs A | McNemar | 20 | 0.950 | 0.950 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs B | McNemar | 20 | 0.950 | 0.950 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ2 | Context independence SV vs AB (mutation_score) | Wilcoxon | 18 | 0.992 | 0.960 | A12=0.51 | 0.9102 | 1.0000 |
| RQ2 | Model independence AB vs ABp (mutation_score) | Wilcoxon | 18 | 0.960 | 0.983 | A12=0.50 | 0.9810 | 1.0000 |
| RQ2 | Context independence SV vs AB (false_oracle_rate) | Wilcoxon | 20 | 0.062 | 0.063 | A12=0.43 | 0.2061 | 1.0000 |
| RQ2 | Model independence AB vs ABp (false_oracle_rate) | Wilcoxon | 20 | 0.063 | 0.088 | A12=0.47 | 0.8646 | 1.0000 |
| RQ3 | A vs B (mutation_score) | Wilcoxon | 18 | 0.953 | 0.988 | A12=0.42 | 0.2331 | 1.0000 |
| RQ3 | AB vs A (mutation_score) | Wilcoxon | 18 | 0.960 | 0.953 | A12=0.55 | 0.4053 | 1.0000 |
| RQ3 | AB vs B (mutation_score) | Wilcoxon | 18 | 0.960 | 0.988 | A12=0.47 | 0.6625 | 1.0000 |
| RQ4 | Faulty releases SV vs AB | McNemar | 20 | 0.050 | 0.050 | discordant 0/0 | 1.0000 | 1.0000 |
