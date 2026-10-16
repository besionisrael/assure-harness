# Case study v2: deliberate ambiguities (DRAFT, 2026-10-09). Never shown to any agent.

Version 1 (data/casestudy) stays unchanged: the pilot results of 2026-10-08/09
depend on it. Version 2 is a copy of v1 plus the changes below. These changes
are fixed before any v2 run, and this file is the record of that.

## Why

In v1 every requirement was stated precisely. Builder tests and verifier tests
all caught the seeded faults, so the study could not observe the failure mode
the paper is about: code and tests that share one misreading of S. v2 adds
places where a misreading is plausible.

## Two kinds of ambiguity

**Type D (determined but subtle).** S fixes the behavior, but only through the
interaction of two sentences, or against the most natural implementation. A
careful reader gets it right. T_h tests it, so it counts toward correctness.
This type tests the paper's claim that self-validation misses shared misreadings.

**Type O (open).** S really does not decide. A stakeholder intent R is
recorded below, but T_h does not test it, because a builder cannot be scored on
something S does not say. What we measure instead: whether each condition
*surfaces* the question (Phase A open questions, builder rejections of
counterexamples), and how many verifier tests on these points are false
oracles. This type tests the framework's claim that open questions are
exposed rather than resolved silently. Coding is manual, after the runs, with
the protocol below.

## Changes to S

| ID | Type | Change to S (v1 -> v2) | Natural misreading | Intent / T_h |
|---|---|---|---|---|
| D1 | D | REQ-14 gains: "The *caller* of a method is the user the token belongs to." REQ-23 already says keys are scoped to the caller. | keys scoped to the token (session) | T_h: a retry after logout + new login, same key and amount, returns 200 with the original payment and charges nothing |
| D2 | D | REQ-19: "A cursor that was not issued to the caller gives 400" now reads with the definition of D1 | cursor bound to the token | T_h: a cursor obtained with one token works with another token of the same user |
| D3 | D | REQ-19: replace "provided no document is created or deleted meanwhile" by: "Documents deleted after a cursor was issued are not returned; documents created after it appear on later pages; no document is returned twice and no remaining document is skipped." | cursor = offset into the list, which skips or repeats items after a deletion | T_h: delete or create between pages, then check each remaining document is returned exactly once |
| D4 | D | REQ-21 gains: "Updating a document does not change its position in any ordering." | ordering by last modification | T_h: update the oldest document, check list, search and export order |
| O1 | O | S stays silent on administrators (as in v1) | | R: no admin role. Not in T_h |
| O2 | O | REQ-20 keeps "ignoring case" without defining it for non-ASCII text | `lower()` vs `casefold()` ("Straße" / "STRASSE") | R: casefold. Not in T_h |
| O3 | O | REQ-23 keeps "a key the caller already used" | is a key "used" by a request that returned 400? | R: no, a rejected request does not consume the key. Not in T_h |
| O4 | O | S says nothing on the form of idempotency keys (observed in v1, run 2) | is the empty string a valid key? | R: any non-empty string; empty gives 400. Not in T_h |
| O5 | O | REQ-14 keeps "at least 8 characters" (observed in v1, run 2) | are unencodable characters (lone surrogates) allowed? | R: the method must return a status, never raise. Not in T_h |

O4 and O5 come from verifier behavior observed in the v1 pilot. They are
included as observed, and the paper must say so.

## New seeded faults (beta), each one a natural misreading of a D item

| ID | Item | Change to the reference |
|---|---|---|
| F11 | D1 | idempotency keys stored per token instead of per user |
| F12 | D2 | cursor bound to the token instead of the user |
| F13 | D3 | cursor stores an offset instead of the last item returned |
| F14 | D4 | update moves the document to the end of every ordering |

F01 to F10 are kept unchanged. Each new fault must pass T_v and fail T_h
(checked by validate.py).

## Coding protocol for type O (manual, after the runs, before looking at scores)

For each run and condition, and for each item O1 to O5, record:
1. *raised*: Phase A lists it as an open question (verifier conditions only);
2. *tested*: a verifier test asserts a behavior on it; and whether that test
   fails on the reference (a false oracle by the current definition);
3. *builder*: the final program's behavior on it, and whether it matches R;
4. *disputed*: a counterexample on it was rejected by the builder.
