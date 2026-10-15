"""Visible tests T_v of the tool lending library service (nominal cases)."""
from solution import Service


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def now(self):
        return self.t


def test_register_and_get_member():
    svc = Service(Clock())
    assert svc.register_member("alice", "standard") == (201, {"username": "alice", "tier": "standard"})
    status, body = svc.get_member_summary("alice")
    assert status == 200
    assert body["username"] == "alice"
    assert body["tier"] == "standard"
    assert body["fines"] == 0.0


def test_add_item_and_get():
    svc = Service(Clock())
    assert svc.add_item("t1", "Drill", "Power Tools", 2, 7) == (201, {"item_id": "t1"})
    status, body = svc.get_item("t1")
    assert status == 200
    assert body["available"] == 2
    assert body["total_qty"] == 2


def test_borrow_and_return():
    svc = Service(Clock(100.0))
    svc.register_member("bob", "standard")
    svc.add_item("t1", "Drill", "Power Tools", 1, 7)
    
    b_status, b_body = svc.borrow_item("bob", "t1")
    assert b_status == 201
    assert "loan_id" in b_body
    
    r_status, r_body = svc.return_item(b_body["loan_id"], "good")
    assert r_status == 200
    assert r_body["fine"] == 0.0
    assert r_body["status"] == "good"


def test_renew_loan():
    svc = Service(Clock(100.0))
    svc.register_member("charlie", "standard")
    svc.add_item("t1", "Saw", "Hand Tools", 1, 5)
    
    _, b_body = svc.borrow_item("charlie", "t1")
    renew_status, renew_body = svc.renew_loan(b_body["loan_id"])
    assert renew_status == 200
    assert renew_body["due_date"] > b_body["due_date"]


def test_pay_fine():
    svc = Service(Clock(0.0))
    svc.register_member("dave", "standard")
    svc.add_item("t1", "Drill", "Power Tools", 1, 1)
    _, b = svc.borrow_item("dave", "t1")
    svc.return_item(b["loan_id"], "damaged")  # accumulates 15.0 fine via public API
    
    status, body = svc.pay_fine("dave", 10.0)
    assert status == 200
    assert body["balance"] == 5.0

