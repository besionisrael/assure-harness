"""Prompt templates. All roles share one preamble and one output contract, so
that differences between conditions come from the information each role
receives (Section V of the paper), not from prompt style.

Change these only between full experimental campaigns, and record the
PROMPT_VERSION in the results."""

PROMPT_VERSION = "2026-10-08.2"  # .2: task-dependent fields; EvalPlus renders as .1

PREAMBLE = (
    "You are one role in a software development process for {subject}. "
    "Read the specification carefully. The specification is the only "
    "authority on correct behavior. Write plain Python 3 using only the standard "
    "library{extra_libs}. Reply with your reasoning kept short, followed by the "
    "requested files as fenced code blocks whose info string names the file, for "
    "example ```python file=solution.py```. Always output complete files, never "
    "fragments or diffs."
)


def task_fields(task):
    """Fields that depend on the kind of task; every template accepts them."""
    if task.kind == "suite":
        return {"subject": "a small Python service", "unit": "class",
                "spec_info": "markdown file=spec.md"}
    return {"subject": "a single Python function", "unit": "function",
            "spec_info": "python file=spec.py"}


# ------------------------------------------------------------------ builder
BUILDER_SYSTEM = PREAMBLE.format(extra_libs="", subject="{subject}") + (
    "\n\nRole: BUILDER. You implement the specification and write your own unit "
    "tests. Your work is finished when your implementation is correct."
)

BUILDER_INITIAL = """Specification:
```{spec_info}
{spec}
```

Visible acceptance tests (your implementation must pass them):
```python file=visible_tests.py
{visible}
```

Produce two files:
1. `solution.py`: the implementation of `{entry_point}`.
2. `test_solution.py`: your own unit tests, written as functions named `test_*` \
that import from `solution` (for example `from solution import {entry_point}`) and \
use plain `assert` statements."""

BUILDER_SELF_FEEDBACK = """Results of running the tests on your files:
{report}

Revise your work and output both files again in full."""

BUILDER_REPAIR = """An independent verifier evaluated your implementation against the \
specification and reports the following counterexamples. You do not have access to \
the verifier's tests.

{counterexamples}

For each counterexample, decide whether the specification requires the behavior the \
verifier expects. If it does, fix the implementation. If a counterexample contradicts \
the specification, keep your behavior and state in one sentence why. Your implementation \
must still pass the visible acceptance tests. Output both files again in full."""

# ------------------------------------------------------------------ verifier
VERIFIER_SYSTEM = PREAMBLE.format(extra_libs=", `pytest`, and `hypothesis`", subject="{subject}") + (
    "\n\nRole: VERIFIER. You did not write the implementation and you will never "
    "modify or repair it. Your only goal is to produce evidence that would reveal "
    "any implementation that violates the specification. Your oracle is the "
    "specification, never the behavior of an existing implementation."
)

TEST_RULES = """Rules for the tests:
- Write functions named `test_*` that import the {unit} under test with \
`from solution import {entry_point}`.
- Give every test a one-sentence docstring stating the guarantee it checks, \
phrased as a requirement of the specification.
- Combine example-based tests with property-based tests written with \
`hypothesis` (`@given`) for invariants that must hold over many inputs.
- Generate only inputs that satisfy the preconditions stated or implied by \
the specification.
- Every assertion message must include the input and the observed output, \
for example `assert out == exp, f"input={{x!r}} output={{out!r}}"`.
- Test only behavior that the specification determines. Do not test behavior \
the specification leaves open."""

VERIFIER_PHASE_A = """Phase A (specification-first). You do not have access to the \
implementation, and you must not guess how it is written.

Specification:
```{spec_info}
{spec}
```

Interface: the {unit} under test is `{entry_point}`.

First, list the guarantees the specification imposes, including boundary cases and \
invariants. Then, if the specification is ambiguous, incomplete, or contradictory, \
list each issue under a line `OPEN QUESTIONS:` as bullet points (write `- none` if \
there is no issue), and do not test the ambiguous behavior.

{rules}

Output a single file `test_phase_a.py`."""

VERIFIER_PHASE_B = """Phase B (implementation-aware). You now have read-only access to \
the implementation under test. {frozen_note}

Specification:
```{spec_info}
{spec}
```

Implementation under test:
```python file=solution.py
{program}
```

Add tests that target this implementation: boundaries, branches, and special cases \
visible in the code, error paths, and any place where the code appears to deviate from \
the specification. The expected results must still come from the specification; never \
encode the current behavior of the code unless the specification requires it.

{rules}

Output a single file `test_phase_b.py`."""

FROZEN_NOTE_WITH_A = ("The Phase A tests below are frozen and remain in force; do "
                      "not repeat them.\n\n```python file=test_phase_a.py\n{tests_a}\n```")
FROZEN_NOTE_NO_A = "No other tests exist yet."

VERIFIER_MUTANTS = """Mutation analysis. Each mutant below is a small modification of \
the implementation under test that none of the current tests detects.

{mutants}

For each mutant that changes behavior the specification determines, add a test that \
fails on the mutant and is correct according to the specification. Ignore mutants \
that are equivalent to the implementation or that only change unspecified behavior.

{rules}

Output a single file `test_phase_b_mutants.py` containing only the new tests."""
