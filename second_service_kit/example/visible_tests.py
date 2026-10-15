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
