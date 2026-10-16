"""Hidden suite T_h. Every assertion follows from a sentence of spec.md."""
from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, run_state_machine_as_test

from solution import Service


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def now(self):
        return self.t


# ---------------- REQ-1 ----------------
def test_req1_invalid_inputs():
    svc = Service(Clock())
    for bad_id in ["", None, 5, True]:
        assert svc.register_user(bad_id, "member")[0] == 400, bad_id
    for bad_role in ["", "guest", "MEMBER", None, 1]:
        assert svc.register_user("u", bad_role)[0] == 400, bad_role


def test_req1_duplicate_user():
    svc = Service(Clock())
    assert svc.register_user("ann", "member") == (201, {"user_id": "ann", "role": "member"})
    assert svc.register_user("ann", "staff")[0] == 409


# ---------------- REQ-2 ----------------
def test_req2_invalid_inputs():
    svc = Service(Clock())
    for bad in ["", None, 3]:
        assert svc.add_item(bad, "n")[0] == 400, bad
        assert svc.add_item("i", bad)[0] == 400, bad


def test_req2_duplicate_id_but_shared_name():
    svc = Service(Clock())
    assert svc.add_item("a", "Hammer")[0] == 201
    assert svc.add_item("b", "Hammer")[0] == 201          # same name ok
    assert svc.add_item("a", "Saw")[0] == 409             # same id clash


# ---------------- REQ-3 ----------------
def test_req3_check_order_and_codes():
    svc = Service(Clock())
    assert svc.checkout("ghost", "x")[0] == 404           # user missing first
    svc.register_user("ann", "member")
    assert svc.checkout("ann", "ghost")[0] == 404         # item missing
    svc.add_item("tool", "Tool")
    assert svc.checkout("ann", "tool")[0] == 200


def test_req3_due_at_uses_clock_plus_period():
    clk = Clock(50.0)
    svc = Service(clk, loan_period=4.0)
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    st, b = svc.checkout("ann", "t")
    assert st == 200 and b["due_at"] == 54.0


def test_req3_loan_ids_sequential_from_one():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    for i in range(3):
        svc.add_item(f"t{i}", "T")
    ids = [svc.checkout("ann", f"t{i}")[1]["loan_id"] for i in range(3)]
    assert ids == [1, 2, 3]


def test_req3_item_on_loan_conflict():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("bob", "member")
    svc.add_item("t", "T")
    assert svc.checkout("ann", "t")[0] == 200
    assert svc.checkout("bob", "t")[0] == 409


def test_req3_max_loans_boundary():
    svc = Service(Clock(), max_loans=2)
    svc.register_user("ann", "member")
    for i in range(3):
        svc.add_item(f"t{i}", "T")
    assert svc.checkout("ann", "t0")[0] == 200
    assert svc.checkout("ann", "t1")[0] == 200
    assert svc.checkout("ann", "t2")[0] == 422            # already at limit


# ---------------- REQ-4 ----------------
def test_req4_unknown_loan_404():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    assert svc.return_loan("ann", 999)[0] == 404


def test_req4_not_owner_member_forbidden():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("bob", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.return_loan("bob", lid)[0] == 403
    # still active for ann
    assert svc.item_status("t")[1]["available"] is False


def test_req4_already_returned_conflict():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.return_loan("ann", lid)[0] == 200
    assert svc.return_loan("ann", lid)[0] == 409


def test_req4_return_frees_item():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.item_status("t") == (200, {"available": False, "loan_id": lid})
    assert svc.return_loan("ann", lid)[0] == 200
    assert svc.item_status("t") == (200, {"available": True, "loan_id": None})


# ---------------- REQ-5 ----------------
def test_req5_unknown_and_forbidden():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("bob", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.renew_loan("ann", 999)[0] == 404
    assert svc.renew_loan("bob", lid)[0] == 403


def test_req5_returned_cannot_renew():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    svc.return_loan("ann", lid)
    assert svc.renew_loan("ann", lid)[0] == 409


def test_req5_overdue_boundary_strict():
    clk = Clock(100.0)
    svc = Service(clk, loan_period=10.0, max_renewals=5)
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]      # due 110
    clk.t = 110.0                                     # exactly due -> not overdue
    assert svc.renew_loan("ann", lid)[0] == 200       # renew ok, due->120
    clk.t = 120.0001                                  # strictly overdue
    assert svc.renew_loan("ann", lid)[0] == 409


def test_req5_renewal_cap_boundary():
    svc = Service(Clock(), loan_period=10.0, max_renewals=2)
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.renew_loan("ann", lid)[0] == 200       # used 1
    assert svc.renew_loan("ann", lid)[0] == 200       # used 2
    assert svc.renew_loan("ann", lid)[0] == 422       # at cap


def test_req5_renew_extends_by_period():
    clk = Clock(0.0)
    svc = Service(clk, loan_period=8.0, max_renewals=3)
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]      # due 8
    st, b = svc.renew_loan("ann", lid)
    assert st == 200 and b["due_at"] == 16.0


# ---------------- REQ-6 ----------------
def test_req6_unknown_user_404():
    svc = Service(Clock())
    assert svc.list_loans("ghost")[0] == 404


def test_req6_only_own_loans_sorted_with_statuses():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("bob", "member")
    for i in range(3):
        svc.add_item(f"t{i}", "T")
    l0 = svc.checkout("ann", "t0")[1]["loan_id"]
    l1 = svc.checkout("bob", "t1")[1]["loan_id"]
    l2 = svc.checkout("ann", "t2")[1]["loan_id"]
    svc.return_loan("ann", l0)
    _, ann = svc.list_loans("ann")
    assert [r["loan_id"] for r in ann] == [l0, l2]
    assert ann[0]["status"] == "returned"
    assert ann[1]["status"] == "active"
    _, bob = svc.list_loans("bob")
    assert [r["loan_id"] for r in bob] == [l1]


# ---------------- REQ-7 ----------------
def test_req7_unknown_item_404():
    svc = Service(Clock())
    assert svc.item_status("ghost")[0] == 404


def test_req7_availability_tracks_active_loan():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    assert svc.item_status("t") == (200, {"available": True, "loan_id": None})
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.item_status("t") == (200, {"available": False, "loan_id": lid})


# ---------------- REQ-8 ----------------
def test_req8_staff_can_act_on_others():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("admin", "staff")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.renew_loan("admin", lid)[0] == 200
    assert svc.return_loan("admin", lid)[0] == 200


def test_req8_member_still_forbidden_after_staff_rule():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("bob", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.renew_loan("bob", lid)[0] == 403


# ---------------- REQ-9 ----------------
def test_req9_custom_limits():
    svc = Service(Clock(), max_loans=1, max_renewals=0)
    svc.register_user("ann", "member")
    svc.add_item("a", "A")
    svc.add_item("b", "B")
    assert svc.checkout("ann", "a")[0] == 200
    assert svc.checkout("ann", "b")[0] == 422
    lid = svc.checkout("ann", "a")  # already held; conflict
    assert lid[0] == 409
    _, c = svc.checkout("ann", "a")
    # renew with cap 0
    # need a fresh loan not conflicting: return then checkout again
    svc.return_loan("ann", 1)
    _, c = svc.checkout("ann", "a")
    assert svc.renew_loan("ann", c["loan_id"])[0] == 422


# ---------------- REQ-10 ----------------
def test_req10_no_wall_clock_dependency():
    # two clocks give independent timelines
    svc = Service(Clock(10.0), loan_period=5.0)
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    assert svc.checkout("ann", "t")[1]["due_at"] == 15.0


# ---------------- stateful model ----------------
class Loans(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.clk = Clock(100.0)
        self.svc = Service(self.clk, max_loans=2, max_renewals=1, loan_period=10.0)
        self.users = {}      # uid -> role
        self.items = set()
        self.loans = {}      # lid -> dict
        self.next_lid = 1

    @initialize()
    def seed(self):
        for u in ("ann", "bob"):
            self.svc.register_user(u, "member")
            self.users[u] = "member"
        self.svc.register_user("admin", "staff")
        self.users["admin"] = "staff"
        for i in ("x", "y", "z"):
            self.svc.add_item(i, "N")
            self.items.add(i)

    @rule(tick=st.integers(0, 30))
    def advance_time(self, tick):
        self.clk.t += float(tick)

    @rule(uid=st.sampled_from(["ann", "bob"]), iid=st.sampled_from(["x", "y", "z"]))
    def checkout(self, uid, iid):
        active_for_user = sum(1 for L in self.loans.values()
                              if L["user"] == uid and L["status"] == "active")
        on_loan = any(L["item"] == iid and L["status"] == "active" for L in self.loans.values())
        stt, body = self.svc.checkout(uid, iid)
        if on_loan:
            assert stt == 409
        elif active_for_user >= 2:
            assert stt == 422
        else:
            assert stt == 200
            assert body["loan_id"] == self.next_lid
            self.loans[self.next_lid] = {
                "user": uid, "item": iid,
                "due_at": self.clk.t + 10.0, "renewals_used": 0, "status": "active",
            }
            self.next_lid += 1

    @rule(lid=st.integers(1, 3))
    def return_loan(self, lid):
        L = self.loans.get(lid)
        stt, body = self.svc.return_loan("admin", lid)
        if L is None:
            assert stt == 404
        elif L["status"] == "returned":
            assert stt == 409
        else:
            assert stt == 200 and body["item_id"] == L["item"]
            L["status"] = "returned"

    @rule(lid=st.integers(1, 3))
    def renew_loan(self, lid):
        L = self.loans.get(lid)
        stt, body = self.svc.renew_loan("admin", lid)
        if L is None:
            assert stt == 404
        elif L["status"] == "returned":
            assert stt == 409
        elif self.clk.t > L["due_at"]:
            assert stt == 409
        elif L["renewals_used"] >= 1:
            assert stt == 422
        else:
            assert stt == 200
            L["due_at"] += 10.0
            L["renewals_used"] += 1
            assert body["due_at"] == L["due_at"]


def test_stateful_model():
    run_state_machine_as_test(Loans, settings=settings(
        max_examples=40, stateful_step_count=15, deadline=None,
        database=None, derandomize=True))
