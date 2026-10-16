# Authors of the additional case-study services

Models as displayed in each web interface, noted by the first author on
2026-10-13. Self-reports inside AUTHOR_NOTES.md are not reliable: the Mistral
answer called itself "GLM, glm-5-latest-short".

| Service | Model (web interface) | Domain | Initial prompt | Correction rounds |
|---|---|---|---|---|
| gemini | Gemini 3, "low" mode (quick and efficient) | library loans with fines | PROMPT_LLM.md | fix_gemini.txt, fix_gemini_2.txt, fix_gemini_3.txt (ALL OK after round 4) |
| mistral | Mistral Medium 3.5 (Le Chat) | room booking | PROMPT_LLM.md | fix_mistral.txt, fix_mistral_2.txt (ALL OK after round 3) |
| qwen | Qwen 3.7-Plus | equipment loans | PROMPT_LLM.md | fix_qwen.txt (ALL OK after round 2) |

Every model answer is kept unmodified: `<name>.txt`, `<name>_2.txt`, and so on.
The correction messages only pass on the validator's findings; the authoring
model decides how to fix them.

## Cross-review of the hidden tests (2026-10-14)

Each service was reviewed by a model other than its author, never by Claude or
GPT, with `review/PROMPT_REVIEW_<service>_by_<reviewer>.md`. Answers are in
`review/answer_<service>_by_<reviewer>.txt`. A mechanical check (status codes
absent from the spec; tests reading service internals) was run as well.

| Service | Reviewer | Result | Mechanical check |
|---|---|---|---|
| gemini | Mistral (Le Chat) | 5 problems (2 tests read internal state, 1 tests behavior declared open, 2 assert values not fixed by S) | T_h and T_v read `svc.members` / `svc.items` |
| mistral | Qwen | none | clean |
| qwen | Gemini | none | clean |

A first, informal review of the three services (2026-10-13), by an unrecorded
model, reported no problem. It is superseded by this cross-review and is not used.
Correction for gemini: `fix_gemini_4.txt`, then `fix_gemini_5.txt`.

## Decision on the gemini service (2026-10-14): dropped

After the cross-review, two more correction rounds (answers `gemini_5.txt`,
`gemini_6.txt`) did not converge: round 6 introduced a hidden test that fails on
the reference (`test_req3_unpaid_fine_boundary_10_exact`), fault F06 still failed
T_v, and the `status` field asserted by T_h was still not defined by the
specification. As agreed beforehand (at most one more round after round 5), the
service is dropped. It is not used in any run. The main campaign uses
`mistral` and `qwen` (validated, cross-reviewed, mechanical checks clean).
