You are helping build a benchmark for research on testing software. Your task is to
design and write, on your own, a small stateful software service together with its
specification, a correct reference implementation, two test suites, and a set of
seeded faults. You cannot run code here, so check your own work carefully by
reasoning; we will run a validator and send you its output if something fails.

## What the benchmark is used for

AI coding agents will receive your specification and visible tests, implement the
service, and write tests. We will then run those tests against your seeded faults.
You are not told who must detect what, and that is intentional: choose faults for
their realism only, never to trap or to favor anyone.

## The service

- Domain: your choice, with two exclusions: no document storage and no payments.
  The service must have state: users or sessions, access rules, shared resources,
  repeated or concurrent operations. Examples: booking time slots, inventory,
  ticket queues, API quotas, equipment loans.
- Size: about 10 numbered requirements; a reference implementation of 200 to 400 lines.
- Language: English everywhere.

## Technical conventions (mandatory)

- Python 3.13, standard library only, for the reference and for any code an agent
  must write. Tests may also use `hypothesis`.
- In-process only: no network, no files, no reading of the system clock, no
  randomness that affects an expected result.
- The service is one class named `Service` in a module `solution.py`.
- Every public method returns a pair `(status, body)`: `status` is an HTTP-style
  integer; `body` is a `dict`, a `list`, or `None`.
- External dependencies (time, a third-party system) are injected through the
  constructor, for example `Service(clock, ...)`. If code or tests must import
  something (an exception class, a type), put it in a support module: an extra
  `.py` file. Do not reuse names of standard-library modules.
- The specification is a Markdown file `spec.md` that must contain no fenced code
  block (no triple backticks). Show the interface indented by 4 spaces.
  `<!-- ... -->` comments are removed before agents read it.

## Deliverables

| File | Content |
|---|---|
| `spec.md` | The specification S. Together with T_v, it is all the agents see. The interface must be complete: signatures, possible statuses, response formats |
| `reference.py` | The correct implementation (it is used as `solution.py`) |
| support modules | zero or more extra `.py` files |
| `visible_tests.py` | T_v: 5 to 8 tests of nominal cases. Agents see them |
| `hidden_tests.py` | T_h: the ground truth, never shown to agents. It tests every requirement thoroughly |
| `faults.py` | The seeded faults, in the format of the example below |
| `AUTHOR_NOTES.md` | Your choices, behaviors deliberately left open, and one sentence per fault on why it is plausible |

### Rules for S and T_h (the most important part)

1. T_h tests only what S fixes. If an assertion of T_h requires a behavior that
   cannot be derived from S, it is a design error that corrupts the whole
   measurement. For every assertion of T_h, ask: "which sentence of S requires this?"
2. If a behavior is deliberately left open, do not test it, and list it in
   `AUTHOR_NOTES.md`.
3. Tests are top-level functions `test_*` that import from `solution` and use
   `assert`. No pytest fixtures (helper functions are fine). Each test must take
   under 10 seconds. Stateful tests are allowed through
   `hypothesis.stateful.run_state_machine_as_test` with deterministic settings
   (see the example).
4. T_v must be simple enough that every seeded fault passes it; otherwise the
   fault would be trivial to spot.

### Rules for the seeded faults

- At least 12 faults. Each one is a single local edit of `reference.py`, given as
  a pair (original text, replacement text). The original text must occur exactly
  once in `reference.py`, character for character, including indentation.
- Each fault must pass T_v, fail T_h, and be caught by at least one deterministic
  test (being caught only by a stateful test is not enough).
- Realistic defects, of the kind a competent developer could make. Vary the
  requirements involved and the kinds of defects.

## Response format (mandatory, so that we can extract the files automatically)

Output every file in full. Precede each file by a line `### FILE: <name>`, then
put its content in one fenced block (```markdown for `spec.md` and
`AUTHOR_NOTES.md`, ```python for `.py` files). Write nothing between files except
these lines. Before the first file, you may write a short plan.

## A complete toy example of the format

This tiny counter service only shows the format. It has 2 faults because it is a
toy; you must write at least 12. Do not copy its domain.

### FILE: spec.md
```markdown
# Counter service (toy example of the format)

<!-- Author notes may go in comments like this one; agents never see them. -->

## Interface

The service is a Python module `solution.py` that defines a class `Service`.
Every method returns a pair `(status, body)`.

    class Service:
        def __init__(self, clock): ...
        def create_counter(self, user, name, limit): ...   # 201 {"name": str} | 400 | 409
        def increment(self, user, name): ...               # 200 {"value": int} | 404 | 429
        def read(self, user, name): ...                    # 200 {"value": int, "created_at": float} | 404

`clock` has a method `now()` returning the current time in seconds.

## Requirements

**REQ-1 Creation.** `create_counter` creates a counter with value 0 for the
given user. `limit` is an integer from 1 to 1000; otherwise 400. A user who
already has a counter with that name gets 409. `created_at` is `clock.now()`
at creation.

**REQ-2 Increment.** `increment` adds 1 to the counter and returns the new
value. A counter never exceeds its limit: when the value equals the limit,
`increment` returns 429 and the value does not change.

**REQ-3 Ownership.** Counters are private: a user cannot increment or read
another user's counter, and gets 404 exactly as for a missing counter. Two
users may have counters with the same name.
```

### FILE: reference.py
```python
"""Reference implementation of the toy counter service."""


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


class Service:
    def __init__(self, clock):
        self.clock = clock
        self._counters = {}      # (user, name) -> {"value", "limit", "created_at"}

    def create_counter(self, user, name, limit):
        if not (_is_int(limit) and 1 <= limit <= 1000):
            return 400, None
        if (user, name) in self._counters:
            return 409, None
        self._counters[(user, name)] = {"value": 0, "limit": limit,
                                        "created_at": self.clock.now()}
        return 201, {"name": name}

    def increment(self, user, name):
        c = self._counters.get((user, name))
        if c is None:
            return 404, None
        if c["value"] >= c["limit"]:
            return 429, None
        c["value"] += 1
        return 200, {"value": c["value"]}

    def read(self, user, name):
        c = self._counters.get((user, name))
        if c is None:
            return 404, None
        return 200, {"value": c["value"], "created_at": c["created_at"]}
```

### FILE: visible_tests.py
```python
"""Visible tests T_v of the toy example (shown to agents): nominal cases only."""
from solution import Service


class Clock:
    def now(self):
        return 100.0


def test_create_and_read():
    svc = Service(Clock())
    assert svc.create_counter("ann", "visits", 10) == (201, {"name": "visits"})
    assert svc.read("ann", "visits") == (200, {"value": 0, "created_at": 100.0})


def test_increment():
    svc = Service(Clock())
    svc.create_counter("ann", "visits", 10)
    assert svc.increment("ann", "visits") == (200, {"value": 1})
    assert svc.increment("ann", "visits") == (200, {"value": 2})


def test_duplicate_name():
    svc = Service(Clock())
    svc.create_counter("ann", "visits", 10)
    assert svc.create_counter("ann", "visits", 5)[0] == 409
```

### FILE: hidden_tests.py
```python
"""Hidden suite T_h of the toy example. Every assertion follows from a sentence of spec.md."""
from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, run_state_machine_as_test

from solution import Service


class Clock:
    def __init__(self, t=100.0):
        self.t = t

    def now(self):
        return self.t


def test_req1_limit_bounds():                       # REQ-1: limit from 1 to 1000
    svc = Service(Clock())
    for bad in [0, 1001, -3, 2.5, "7", None]:
        assert svc.create_counter("ann", f"c{bad}", bad)[0] == 400, bad
    assert svc.create_counter("ann", "low", 1)[0] == 201
    assert svc.create_counter("ann", "high", 1000)[0] == 201


def test_req2_never_exceeds_limit():                # REQ-2: 429 at the limit, value unchanged
    svc = Service(Clock())
    svc.create_counter("ann", "c", 2)
    assert svc.increment("ann", "c")[0] == 200
    assert svc.increment("ann", "c") == (200, {"value": 2})
    assert svc.increment("ann", "c")[0] == 429
    assert svc.read("ann", "c")[1]["value"] == 2


def test_req3_other_users_counter_is_404():         # REQ-3: 404 exactly as for a missing counter
    svc = Service(Clock())
    svc.create_counter("ann", "c", 5)
    assert svc.read("bob", "c") == svc.read("bob", "missing") == (404, None)
    assert svc.increment("bob", "c") == (404, None)
    assert svc.read("ann", "c")[1]["value"] == 0


def test_req3_same_name_for_two_users():
    svc = Service(Clock())
    assert svc.create_counter("ann", "c", 5)[0] == 201
    assert svc.create_counter("bob", "c", 5)[0] == 201


class Counters(RuleBasedStateMachine):
    """Model-based check of REQ-2 and REQ-3."""

    def __init__(self):
        super().__init__()
        self.svc, self.model = Service(Clock()), {}

    @rule(user=st.sampled_from(["ann", "bob"]), limit=st.integers(1, 3))
    def create(self, user, limit):
        status, _ = self.svc.create_counter(user, "c", limit)
        assert status == (409 if user in self.model else 201)
        self.model.setdefault(user, [0, limit])

    @rule(user=st.sampled_from(["ann", "bob"]))
    def increment(self, user):
        status, body = self.svc.increment(user, "c")
        if user not in self.model:
            assert status == 404
        elif self.model[user][0] == self.model[user][1]:
            assert status == 429
        else:
            self.model[user][0] += 1
            assert body == {"value": self.model[user][0]}


def test_stateful_counters():
    run_state_machine_as_test(Counters, settings=settings(max_examples=50, stateful_step_count=20,
                                                          deadline=None, database=None,
                                                          derandomize=True))
```

### FILE: faults.py
```python
"""Seeded faults of the toy example. Format required by validate.py:

  FAULTS = {fault_id: (requirement, short description, original text, replacement text)}

The original text must occur exactly once in reference.py; the faulty program is
reference.py with that text replaced. Keep the two helper functions below."""
from pathlib import Path

HERE = Path(__file__).resolve().parent

FAULTS = {
    "F01": ("REQ-2", "off-by-one: the counter can reach limit + 1",
            '''        if c["value"] >= c["limit"]:''',
            '''        if c["value"] > c["limit"]:'''),

    "F02": ("REQ-3", "read looks counters up by name only, ignoring the user",
            '''    def read(self, user, name):
        c = self._counters.get((user, name))''',
            '''    def read(self, user, name):
        c = next((v for (u, n), v in self._counters.items() if n == name), None)'''),
}


def reference():
    return (HERE / "reference.py").read_text(encoding="utf-8")


def variant(fault_id):
    _, _, old, new = FAULTS[fault_id]
    src = reference()
    if src.count(old) != 1:
        raise ValueError(f"{fault_id}: original text occurs {src.count(old)} times")
    return src.replace(old, new)
```

## Your task

Now design your own service, following every rule above, and output all its files:
`spec.md`, `reference.py`, any support modules, `visible_tests.py`, `hidden_tests.py`,
`faults.py` (keep the `reference()` and `variant()` helpers of the example), and
`AUTHOR_NOTES.md`. In `AUTHOR_NOTES.md`, also give the exact name and version of the
model you are, as far as you know it.
