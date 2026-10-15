You are reviewing the hidden test suite of a small software benchmark. You did not
write it. Be strict and precise.

## The rule being checked

The hidden tests may require only behavior that the specification fixes. An
assertion is a PROBLEM if its expected value cannot be derived from the text of the
specification: the author decided something that is not written. A program that
follows the specification to the letter could then fail the test.

Check every assertion, and pay particular attention to these four cases:
1. Two error conditions hold in the same call (for example two different reasons
   to reject): does the specification say which status wins?
2. An ordering of results (list order, sort key, ties) that the specification does
   not state.
3. A computation or rounding (for example partial days, floor or ceiling,
   float precision) whose rule is not stated.
4. A response format detail (field name, type, None vs empty list, extra fields)
   that the interface does not describe.

Behaviors that the author's notes say were deliberately left open must not be
tested; an assertion on one of them is a PROBLEM.

## Required answer format

1. A table with one row per test function:
   | # | test | spec lines that justify each assertion | verdict (OK / PROBLEM) | reason if PROBLEM |
   For a test marked OK, the line numbers must justify every assertion of the
   test, not just one.
2. Then a section `PROBLEMS:` listing, for each PROBLEM, the test name, the
   exact assertion (copied), and one sentence on what the specification fails to
   fix. Write `PROBLEMS: none` only if every assertion is justified by cited lines.

Do not rewrite the tests, and do not suggest fixes: only review.

## Material

The specification is shown with line numbers, then the author's notes, then each
hidden test.
