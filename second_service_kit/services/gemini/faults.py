"""Seeded faults of the tool lending library service. Format required by validate.py:

    FAULTS = {fault_id: (requirement, short description, original text, replacement text)}

The original text must occur exactly once in reference.py."""
from pathlib import Path

HERE = Path(__file__).resolve().parent

FAULTS = {
    "F01": ("REQ-1", "accepts invalid tier without validation check",
            '''    def register_member(self, username, tier):
        if not _is_str(username) or tier not in ("standard", "premium"):
            return 400, None''',
            '''    def register_member(self, username, tier):
        if not _is_str(username):
            return 400, None'''),

    "F02": ("REQ-2", "does not validate that total_qty and duration_days are positive integers",
            '''        if not _is_positive_int(total_qty) or not _is_positive_int(duration_days):
            return 400, None''',
            '''        if not isinstance(total_qty, int) or not isinstance(duration_days, int):
            return 400, None'''),

    "F03": ("REQ-3", "unpaid fine check uses strict greater-than instead of greater-than-or-equal",
            '''        if member["fines"] >= 10.0:
            return 403, None''',
            '''        if member["fines"] > 10.0:
            return 403, None'''),

    "F04": ("REQ-3", "concurrent loan limit hardcoded to 10 for all tiers",
            '''        limit = 10 if member["tier"] == "premium" else 3''',
            '''        limit = 10'''),

    "F05": ("REQ-5", "overdue days calculation uses floor instead of ceiling",
            '''            overdue_days = math.ceil(overdue_seconds / 86400.0)''',
            '''            overdue_days = math.floor(overdue_seconds / 86400.0)'''),

    "F06": ("REQ-7", "pay_fine reduces fine balance by adding instead of subtracting",
            '''        member["fines"] = max(0.0, member["fines"] - amount)''',
            '''        member["fines"] = max(0.0, member["fines"] + amount)'''),

    "F07": ("REQ-9", "lost item condition increments available quantity instead of reducing total_qty",
            '''        elif condition == "lost":
            fine += 50.0
            item["total_qty"] = max(0, item["total_qty"] - 1)''',
            '''        elif condition == "lost":
            fine += 50.0
            item["available"] += 1'''),

    "F08": ("REQ-8", "loan renewal fails to check for active reservations",
            '''        has_reservation = any(
            r["item_id"] == item_id for r in self.reservations.values()
        )
        if has_reservation:
            return 409, None''',
            '''        has_reservation = any(
            r["item_id"] == item_id for r in self.reservations.values()
        )
        if False:
            return 409, None'''),

    "F09": ("REQ-8", "loan renewal allows renewing multiple times",
            '''        loan = self.loans[loan_id]
        if loan["returned"] or loan["renewed"]:
            return 409, None''',
            '''        loan = self.loans[loan_id]
        if loan["returned"]:
            return 409, None'''),

    "F10": ("REQ-6", "reserve item checks if available < 0 instead of available > 0",
            '''        item = self.items[item_id]
        if item["available"] > 0:
            return 400, None''',
            '''        item = self.items[item_id]
        if item["available"] < 0:
            return 400, None'''),

    "F11": ("REQ-7", "pay_fine does not validate that payment amount is positive",
            '''        if username not in self.members or not _is_positive_number(amount):
            return 400, None''',
            '''        if username not in self.members:
            return 400, None'''),

    "F12": ("REQ-3", "borrowing an out of stock item proceeds instead of returning 409",
            '''        if item["available"] <= 0:
            return 409, None''',
            '''        if False:
            return 409, None'''),
}


def reference():
    return (HERE / "reference.py").read_text(encoding="utf-8")


def variant(fault_id):
    _, _, old, new = FAULTS[fault_id]
    src = reference()
    if src.count(old) != 1:
        raise ValueError(f"{fault_id}: original text occurs {src.count(old)} times")
    return src.replace(old, new)

