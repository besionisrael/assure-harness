# Author notes

## Design choices

- Domain: physical equipment loans (catalog + users + loans). Chosen because it
  exercises shared mutable resources, per-user quotas, time-based rules, and a
  role-based override, while staying in-process and deterministic.
- Status codes follow the usual REST-ish convention: 200/201 success, 400 bad
  input, 403 forbidden, 404 not found, 409 conflict, 422 unprocessable.
- Check-order precedence (REQ-3/4/5) is spelled out in the spec so hidden tests
  can rely on a single observable code for overlapping conditions.

## Behaviors deliberately left open (NOT tested)

- Exact validation of the constructor arguments (`max_loans`, `max_renewals`,
  `loan_period`) beyond the documented types/ranges.
- Whether `return_loan`/`renew_loan` of a *nonexistent* id is reported before
  or after an ownership failure — the spec fixes existence first, so only that
  order is tested; nothing else about error precedence outside the listed steps.
- Internal representation of `loan_id` (only the sequence-from-1 property is
  specified).
- Tie-breaking is impossible (ids unique), so ordering stability is unspecified.
- Behavior of registering with a name identical to another user's id is not a
  concept here; ids are global keys.

## Why each fault is plausible (one line each)

- **F01**: copy-pasting a longer role list from another product's docs.
- **F02**: "just overwrite" convenience that quietly kills the conflict code.
- **F03**: confusing business-level uniqueness (by name) with key uniqueness.
- **F04**: using `* 2` instead of `+ period` when wiring the extension formula.
- **F05**: zero-based indexing habit leaking into a public id sequence.
- **F06**: forgetting the side-effect line that reserves the resource.
- **F07**: `>=` vs `>` boundary mistake on a quota check.
- **F08**: removing a guard during a refactor that assumed callers were trusted.
- **F09**: updating status but forgetting the companion release of the lock.
- **F10**: inclusive-vs-exclusive comparison on a deadline.
- **F11**: resetting a counter instead of incrementing it.
- **F12**: mirror-image boundary slip on the renewal cap.
- **F13**: dropping a filter predicate while optimizing iteration.
- **F14**: forgetting to forward the loan id into the response dict.
- **F15**: stubbing out a permission branch and leaving the stub in place.
