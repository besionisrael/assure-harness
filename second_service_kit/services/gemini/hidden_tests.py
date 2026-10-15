"""Hidden test suite T_h of the tool lending library service."""
from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, run_state_machine_as_test
from solution import Service


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def now(self):
        return self.t


def test_req1_member_validation():
    svc = Service(Clock())
    assert svc.register_member("", "standard")[0] == 400
    assert svc.register_member("alice", "invalid")[0] == 400
    assert svc.register_member("alice", "standard")[0] == 201
    assert svc.register_member("alice", "premium")[0] == 409


def test_req2_item_validation():
    svc = Service(Clock())
    assert svc.add_item("", "Hammer", "Tools", 5, 7)[0] == 400
    assert svc.add_item("i1", "Hammer", "Tools", 0, 7)[0] == 400
    assert svc.add_item("i1", "Hammer", "Tools", 5, 0)[0] == 400
    assert svc.add_item("i1", "Hammer", "Tools", 5, 7)[0] == 201
    assert svc.add_item("i1", "Saw", "Tools", 2, 7)[0] == 409


def test_req3_borrow_restrictions():
    svc = Service(Clock(100.0))
    svc.register_member("alice", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 7)
    
    assert svc.borrow_item("missing", "i1")[0] == 404
    assert svc.borrow_item("alice", "missing")[0] == 404
    
    status, body = svc.borrow_item("alice", "i1")
    assert status == 201
    
    svc.add_item("i3", "Pliers", "Tools", 1, 7)
    svc.borrow_item("alice", "i3")
    assert svc.borrow_item("alice", "i3")[0] == 409


def test_req3_borrow_limits_tier():
    svc = Service(Clock())
    svc.register_member("std", "standard")
    for i in range(4):
        svc.add_item(f"item{i}", f"Tool {i}", "Tools", 5, 7)
    
    for i in range(3):
        assert svc.borrow_item("std", f"item{i}")[0] == 201
    assert svc.borrow_item("std", "item3")[0] == 409


def test_req3_unpaid_fines_block_borrow():
    svc = Service(Clock(0.0))
    svc.register_member("debtor", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 1)
    _, b = svc.borrow_item("debtor", "i1")
    svc.return_item(b["loan_id"], "damaged")  # 15.0 fine accumulated via public API
    
    svc.add_item("i2", "Saw", "Tools", 1, 7)
    assert svc.borrow_item("debtor", "i2")[0] == 403


def test_req3_unpaid_fine_boundary_10_exact():
    # Exactly 10.0 fine via 5 days overdue (5 * 2.0 = 10.0)
    clock = Clock(0.0)
    svc = Service(clock)
    svc.register_member("user10", "standard")
    svc.add_item("i1", "Tool1", "Tools", 1, 1)
    _, b = svc.borrow_item("user10", "i1")
    
    clock.t = 5 * 86400.0
    svc.return_item(b["loan_id"], "good")  # exactly 10.0 fine
    
    # Summary should report 10.0 fine
    _, summary = svc.get_member_summary("user10")
    assert summary["fines"] == 10.0
    
    # Trying to borrow another item should be blocked with 403
    svc.add_item("i2", "Tool2", "Tools", 1, 7)
    assert svc.borrow_item("user10", "i2")[0] == 403


def test_req5_return_and_fines():
    clock = Clock(100.0)
    svc = Service(clock)
    svc.register_member("alice", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 5)
    
    _, body = svc.borrow_item("alice", "i1")
    loan_id = body["loan_id"]
    
    assert svc.return_item(loan_id, "good") == (200, {"fine": 0.0, "status": "good"})
    assert svc.return_item(loan_id, "good")[0] == 404
    assert svc.return_item("fake", "good")[0] == 404
    assert svc.return_item(loan_id, "invalid")[0] == 400


def test_req5_overdue_fines():
    clock = Clock(0.0)
    svc = Service(clock)
    svc.register_member("alice", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 1)
    _, body = svc.borrow_item("alice", "i1")
    loan_id = body["loan_id"]
    
    clock.t = 3 * 86400.0
    res = svc.return_item(loan_id, "good")
    assert res[0] == 200
    assert res[1]["fine"] == 4.0


def test_req5_overdue_ceiling_fine():
    clock = Clock(0.0)
    svc = Service(clock)
    svc.register_member("alice", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 1)
    _, body = svc.borrow_item("alice", "i1")
    loan_id = body["loan_id"]
    
    clock.t = 86400.0 + (1.5 * 86400.0)  # 1.5 days overdue
    res = svc.return_item(loan_id, "good")
    assert res[0] == 200
    assert res[1]["fine"] == 4.0  # Ceiling of 1.5 is 2 days * 2.0 = 4.0


def test_req6_reservations():
    svc = Service(Clock())
    svc.register_member("alice", "standard")
    svc.register_member("bob", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 7)
    
    assert svc.reserve_item("bob", "i1")[0] == 400
    svc.borrow_item("alice", "i1")
    assert svc.reserve_item("bob", "i1")[0] == 201
    assert svc.reserve_item("bob", "i1")[0] == 409


def test_req7_pay_fine_validation():
    svc = Service(Clock())
    svc.register_member("alice", "standard")
    assert svc.pay_fine("alice", 0)[0] == 400
    assert svc.pay_fine("alice", -5.0)[0] == 400


def test_req8_renew_loan():
    svc = Service(Clock(0.0))
    svc.register_member("alice", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 7)
    _, body = svc.borrow_item("alice", "i1")
    loan_id = body["loan_id"]
    
    assert svc.renew_loan(loan_id)[0] == 200
    assert svc.renew_loan(loan_id)[0] == 409


def test_req8_renew_blocked_by_reservation():
    svc = Service(Clock(0.0))
    svc.register_member("alice", "standard")
    svc.register_member("bob", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 7)
    _, body = svc.borrow_item("alice", "i1")
    loan_id = body["loan_id"]
    
    # Item is out of stock, so Bob can reserve it
    assert svc.reserve_item("bob", "i1")[0] == 201
    
    # Alice trying to renew when item is reserved should be rejected with 409
    assert svc.renew_loan(loan_id)[0] == 409


def test_req9_damaged_and_lost():
    svc = Service(Clock())
    svc.register_member("alice", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 7)
    _, b1 = svc.borrow_item("alice", "i1")
    
    svc.add_item("i2", "Saw", "Tools", 1, 7)
    _, b2 = svc.borrow_item("alice", "i2")
    
    r1 = svc.return_item(b1["loan_id"], "damaged")
    assert r1[1]["fine"] == 15.0
    assert svc.get_item("i1")[1]["available"] == 1
    
    r2 = svc.return_item(b2["loan_id"], "lost")
    assert r2[1]["fine"] == 50.0
    assert svc.get_item("i2")[1]["total_qty"] == 0


class LibraryStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.svc = Service(Clock(0.0))
        self.members_set = set()
        self.items_set = set()

    @rule(username=st.sampled_from(["u1", "u2"]), tier=st.sampled_from(["standard", "premium"]))
    def register(self, username, tier):
        status, _ = self.svc.register_member(username, tier)
        if username in self.members_set:
            assert status == 409
        else:
            assert status == 201
            self.members_set.add(username)

    @rule(item_id=st.sampled_from(["itemA", "itemB"]), qty=st.integers(1, 3))
    def add_item(self, item_id, qty):
        status, _ = self.svc.add_item(item_id, "Name", "Cat", qty, 5)
        if item_id in self.items_set:
            assert status == 409
        else:
            assert status == 201
            self.items_set.add(item_id)


def test_stateful_library():
    run_state_machine_as_test(LibraryStateMachine, settings=settings(max_examples=30, stateful_step_count=10, deadline=None, database=None, derandomize=True))

