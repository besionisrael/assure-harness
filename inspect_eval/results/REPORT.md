# Phase A evaluation: results

Scoring mode: expanded. Detection is the mean over the 46 seeded faults of each fault's detection rate over the runs (epochs).

## Per model

| Model | Detection (46) | Documents (14) | Booking (17) | Loans (15) | False oracles | Errors | Tests | Runs | Truncated | Output tokens |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic/claude-sonnet-5-5 | 95.2% | 91.4% | 100.0% | 93.3% | 0.4% | 0.0% | 772 | 15 | 0 | 308,316 |
| openai/gpt-5.5-2026-04-23 | 85.7% | 72.9% | 90.6% | 92.0% | 2.8% | 0.0% | 176 | 15 | 0 | 145,201 |

## Per fault (runs detecting / runs)

The two study columns are condition A of the study's main campaign (same prompt, Claude Sonnet 5.5), given as context: they are other draws, not a replication.

| Service | Fault | anthropic/claude-sonnet-5-5 | openai/gpt-5.5-2026-04-23 | study A (frozen) | study A (rescored) |
|---|---|---|---|---|---|
| casestudy_v2 | F01 | 5/5 | 5/5 | 5/5 | 5/5 |
| casestudy_v2 | F02 | 5/5 | 5/5 | 5/5 | 5/5 |
| casestudy_v2 | F03 | 5/5 | 5/5 | 5/5 | 5/5 |
| casestudy_v2 | F04 | 5/5 | 5/5 | 5/5 | 5/5 |
| casestudy_v2 | F05 | 5/5 | 4/5 | 3/5 | 5/5 |
| casestudy_v2 | F06 | 5/5 | 5/5 | 5/5 | 5/5 |
| casestudy_v2 | F07 | 5/5 | 5/5 | 5/5 | 5/5 |
| casestudy_v2 | F08 | 5/5 | 5/5 | 5/5 | 5/5 |
| casestudy_v2 | F09 | 5/5 | 3/5 | 4/5 | 5/5 |
| casestudy_v2 | F10 | 5/5 | 4/5 | 5/5 | 5/5 |
| casestudy_v2 | F11 | 2/5 | 0/5 | 0/5 | 0/5 |
| casestudy_v2 | F12 | 2/5 | 0/5 | 2/5 | 2/5 |
| casestudy_v2 | F13 | 5/5 | 1/5 | 5/5 | 5/5 |
| casestudy_v2 | F14 | 5/5 | 4/5 | 5/5 | 5/5 |
| svc_mistral | F01 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F02 | 5/5 | 5/5 | 4/5 | 4/5 |
| svc_mistral | F03 | 5/5 | 5/5 | 4/5 | 5/5 |
| svc_mistral | F04 | 5/5 | 2/5 | 3/5 | 5/5 |
| svc_mistral | F05 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F06 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F07 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F08 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F09 | 5/5 | 4/5 | 5/5 | 5/5 |
| svc_mistral | F10 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F11 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F12 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F13 | 5/5 | 5/5 | 4/5 | 5/5 |
| svc_mistral | F14 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F15 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F16 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_mistral | F17 | 5/5 | 1/5 | 5/5 | 5/5 |
| svc_qwen | F01 | 0/5 | 0/5 | 0/5 | 0/5 |
| svc_qwen | F02 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F03 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F04 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F05 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F06 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F07 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F08 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F09 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F10 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F11 | 5/5 | 4/5 | 5/5 | 5/5 |
| svc_qwen | F12 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F13 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F14 | 5/5 | 5/5 | 5/5 | 5/5 |
| svc_qwen | F15 | 5/5 | 5/5 | 5/5 | 5/5 |

## Faults missed in common

Never detected by any model: svc_qwen/F01.

Missed in at least one run by every model: casestudy_v2/F11, casestudy_v2/F12, svc_qwen/F01.

- anthropic/claude-sonnet-5-5: missed in at least one run: 3 faults
- openai/gpt-5.5-2026-04-23: missed in at least one run: 12 faults

## Exploratory comparison (not pre-registered)

Exact two-sided sign test over the seeded faults, the procedure the study used for its registered hypotheses. This comparison was not registered: it is exploratory, one pair of models, and it confounds provider, capability, and suite size (see the Tests column above). The prompt was developed in a study where Claude was builder and verifier, and was not adapted to GPT-5.5.

anthropic/claude-sonnet-5-5 vs openai/gpt-5.5-2026-04-23: 11 faults favor anthropic/claude-sonnet-5-5, 0 favor openai/gpt-5.5-2026-04-23, 35 ties; p = 0.0010.
