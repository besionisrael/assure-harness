"""Visible tests T_v: nominal happy paths only (shown to agents)."""
from solution import Service


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def now(self):
        return self.t


def test_register_and_add_item():
    svc = Service(Clock())
    assert svc.register_user("ann", "member") == (201, {"user_id": "ann", "role": "member"})
    assert svc.add_item("scope-1", "Oscilloscope") == (201, {"item_id": "scope-1", "name": "Oscilloscope"})


def test_checkout_then_return_lists_loan():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.add_item("scope-1", "Oscilloscope")
    st, body = svc.checkout("ann", "scope-1")
    assert st == 200
    loan_id = body["loan_id"]
    assert isinstance(loan_id, int)
    st2, body2 = svc.return_loan("ann", loan_id)
    assert st2 == 200 and body2 == {"item_id": "scope-1"}
    st3, loans = svc.list_loans("ann")
    assert st3 == 200
    assert len(loans) == 1
    assert loans[0]["loan_id"] == loan_id
    assert loans[0]["status"] == "returned"


def test_renew_nominal():
    svc = Service(Clock())
    svc.register_user("bob", "member")
    svc.add_item("drill", "Cordless drill")
    _, c = svc.checkout("bob", "drill")
    due0 = c["due_at"]
    st, r = svc.renew_loan("bob", c["loan_id"])
    assert st == 200
    assert r["due_at"] > due0
    _, loans = svc.list_loans("bob")
    assert loans[0]["renewals_used"] == 1


def test_item_available_before_checkout():
    svc = Service(Clock())
    svc.add_item("multimeter", "Multimeter")
    st, s = svc.item_status("multimeter")
    assert st == 200 and s == {"available": True, "loan_id": None}


def test_unknown_item_status_404():
    svc = Service(Clock())
    assert svc.item_status("nope")[0] == 404
