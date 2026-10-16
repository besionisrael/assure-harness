# Analysis

1 tasks, 3 runs, conditions ['SV', 'A', 'B', 'AB', 'ABp']. Pool and mutant definitions: see assure/scoring.py.
## RQ1: evaluation gap

| Benchmark | Cond. | Visible pass | Hidden pass | Gap |
|---|---|---|---|---|
| casestudy_v2 | SV | 100.0 | 100.0 | 0.0 |
| casestudy_v2 | A | 100.0 | 100.0 | 0.0 |
| casestudy_v2 | B | 100.0 | 100.0 | 0.0 |
| casestudy_v2 | AB | 100.0 | 100.0 | 0.0 |
| casestudy_v2 | ABp | 100.0 | 100.0 | 0.0 |

## RQ2: evidence quality per condition (median of per-task means)

| Cond. | Fault detection | Mutation score | False-oracle rate | Tokens (cond.) |
|---|---|---|---|---|
| SV | 66.7 | 68.9 | 0.0 | 0.0k |
| A | 88.1 | 90.0 | 9.4 | 95.2k |
| B | 88.1 | 94.4 | 13.2 | 115.6k |
| AB | 97.6 | 96.7 | 18.0 | 240.5k |
| ABp | 71.4 | 97.8 | 0.0 | 64.5k |

## RQ3: complementarity of Phase A and Phase B

Within AB (summed over task-runs): faults A-only/B-only/both = [14, 5, 22]; mutants A-only/B-only/both = [12, 9, 66]
Within ABp (summed over task-runs): faults A-only/B-only/both = [17, 3, 10]; mutants A-only/B-only/both = [25, 15, 48]
Conditions A vs B (separate verifiers): faults A-only/B-only/both = [1, 1, 36]; mutants = [0, 4, 81]

### Case study: seeded-fault detection (14 seeded faults, runs detecting / runs)

| Fault | SV | A | B | AB | ABp |
|---|---|---|---|---|---|
| F01 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| F02 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| F03 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| F04 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| F05 | 1/3 | 2/3 | 2/3 | 3/3 | 1/3 |
| F06 | 0/3 | 3/3 | 3/3 | 3/3 | 2/3 |
| F07 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| F08 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| F09 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| F10 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| F11 | 0/3 | 1/3 | 1/3 | 2/3 | 0/3 |
| F12 | 0/3 | 1/3 | 1/3 | 3/3 | 0/3 |
| F13 | 0/3 | 3/3 | 3/3 | 3/3 | 0/3 |
| F14 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

Case study, within AB: seeded faults A-only/B-only/both = [14, 5, 22]

Case study, within ABp: seeded faults A-only/B-only/both = [17, 3, 10]
Phase A reported at least one open question in 100.0% of task-runs.

## RQ4: release decisions, raw evidence, as a release gate sees it

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 0 | 0 | 3 | -- | -- |
| A | 0 | 0 | 3 | 0 | 0.0 | -- |
| B | 0 | 0 | 3 | 0 | 0.0 | -- |
| AB | 0 | 0 | 3 | 0 | 0.0 | -- |
| ABp | 0 | 0 | 0 | 3 | -- | -- |

## RQ4: release decisions, valid tests only (false oracles removed)

| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |
|---|---|---|---|---|---|---|
| SV | 0 | 0 | 0 | 3 | -- | -- |
| A | 0 | 0 | 0 | 3 | -- | -- |
| B | 0 | 0 | 0 | 3 | -- | -- |
| AB | 0 | 0 | 0 | 3 | -- | -- |
| ABp | 0 | 0 | 0 | 3 | -- | -- |

## Protocol tests H1/H2 (PROTOCOL.md; own Holm family; confirmatory only for campaigns run after the freeze)

| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |
|---|---|---|---|---|---|---|---|---|
| H | H1 seeded-fault detection, AB vs SV | sign test over faults | 14 | 0.976 | 0.667 | 5+/0-/9= | 0.0625 | 0.1250 |
| H | H2 seeded-fault detection, AB vs ABp | sign test over faults | 14 | 0.976 | 0.714 | 5+/0-/9= | 0.0625 | 0.1250 |

## Exploratory tests (Holm-corrected, alpha = 0.05)

| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |
|---|---|---|---|---|---|---|---|---|
| RQ1 | SV visible vs hidden (evaluation gap) | McNemar | 3 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs AB | McNemar | 3 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs ABp | McNemar | 3 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs A | McNemar | 3 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ1 | Final correctness SV vs B | McNemar | 3 | 1.000 | 1.000 | discordant 0/0 | 1.0000 | 1.0000 |
| RQ4 | Faulty releases SV vs AB | McNemar | 3 | 0.000 | 0.000 | discordant 0/0 | 1.0000 | 1.0000 |
