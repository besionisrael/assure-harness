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
