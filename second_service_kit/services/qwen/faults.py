"""Seeded faults. Format required by validate.py:

  FAULTS = {fault_id: (requirement, short description, original text, replacement text)}

Each original text occurs exactly once in reference.py. Keep the helpers below.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent

FAULTS = {
    # REQ-1: role whitelist widened -> "guest" wrongly accepted (400 expected).
    "F01": ("REQ-1", "accepts an extra bogus role",
            '''        if not (_is_nonempty_str(user_id) and role in _ROLES):''',
            '''        if not (_is_nonempty_str(user_id) and role in ("member", "staff", "guest")):'''),

    # REQ-1: duplicate check dropped -> second registration returns 201 not 409.
    "F02": ("REQ-1", "duplicate user silently overwritten",
            '''        if user_id in self._users:
            return 409, None
        self._users[user_id] = role''',
            '''        self._users[user_id] = role'''),

    # REQ-2: uniqueness keyed on name instead of id -> same-id clash missed.
    "F03": ("REQ-2", "item uniqueness checked against name",
            '''        if item_id in self._items:
            return 409, None''',
            '''        if name in self._items.values():
            return 409, None'''),

    # REQ-3: renewal extends due_at by double the period instead of loan_period.
    "F04": ("REQ-3", "renewal extends by double period",
            '''        loan["due_at"] = loan["due_at"] + self.loan_period''',
            '''        loan["due_at"] = loan["due_at"] + self.loan_period * 2'''),

    # REQ-3: loan ids start at 0 instead of 1.
    "F05": ("REQ-3", "first loan id is 0",
            '''        self._next_loan_id = 1''',
            '''        self._next_loan_id = 0'''),

    # REQ-3: forgetting to reserve the item -> double checkout allowed.
    "F06": ("REQ-3", "item not marked on loan",
            '''        self._item_loan[item_id] = loan_id
        return 200, {"loan_id": loan_id, "due_at": due_at}''',
            '''        return 200, {"loan_id": loan_id, "due_at": due_at}'''),

    # REQ-3: off-by-one on the concurrent-loan cap.
    "F07": ("REQ-3", "allows one loan past max_loans",
            '''        if self._active_count(user_id) >= self.max_loans:''',
            '''        if self._active_count(user_id) > self.max_loans:'''),

    # REQ-4: ownership check ignored -> members return others' loans.
    "F08": ("REQ-4", "ownership check skipped",
            '''        if not self._owned_or_staff(user_id, loan):
            return 403, None
        if loan["status"] == "returned":
            return 409, None
        loan["status"] = "returned"''',
            '''        if loan["status"] == "returned":
            return 409, None
        loan["status"] = "returned"'''),

    # REQ-4: returning does not free the item.
    "F09": ("REQ-4", "item stays reserved after return",
            '''        loan["status"] = "returned"
        self._item_loan.pop(loan["item"], None)''',
            '''        loan["status"] = "returned"'''),

    # REQ-5: overdue test uses >= so being exactly due wrongly blocks renew.
    "F10": ("REQ-5", "overdue boundary off by one",
            '''        if self.clock.now() > loan["due_at"]:
            return 409, None''',
            '''        if self.clock.now() >= loan["due_at"]:
            return 409, None'''),

    # REQ-5: renewal counter reset each time -> cap never reached.
    "F11": ("REQ-5", "renewal count reset on renew",
            '''        loan["due_at"] = loan["due_at"] + self.loan_period
        loan["renewals_used"] += 1''',
            '''        loan["due_at"] = loan["due_at"] + self.loan_period
        loan["renewals_used"] = 1'''),

    # REQ-5: renewal cap compared with > allowing one extra renewal.
    "F12": ("REQ-5", "off-by-one on max_renewals",
            '''        if loan["renewals_used"] >= self.max_renewals:''',
            '''        if loan["renewals_used"] > self.max_renewals:'''),

    # REQ-6: listing ignores the user filter -> leaks everyone's loans.
    "F13": ("REQ-6", "lists all loans regardless of user",
            '''        for loan in self._loans.values():
            if loan["user"] == user_id:''',
            '''        for loan in self._loans.values():
            if True:'''),

    # REQ-7: item_status always returns loan_id as None even when on loan.
    "F14": ("REQ-7", "item_status omits active loan id",
            '''        return 200, {"available": loan_id is None, "loan_id": loan_id}''',
            '''        return 200, {"available": loan_id is None, "loan_id": None}'''),

    # REQ-8: staff treated as ordinary member (privilege lost).
    "F15": ("REQ-8", "staff privilege broken",
            '''        return self._users.get(user_id) == "staff"''',
            '''        return False'''),
}


def reference():
    return (HERE / "reference.py").read_text(encoding="utf-8")


def variant(fault_id):
    _, _, old, new = FAULTS[fault_id]
    src = reference()
    if src.count(old) != 1:
        raise ValueError(f"{fault_id}: original text occurs {src.count(old)} times")
    return src.replace(old, new)
