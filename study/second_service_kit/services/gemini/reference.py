"""Reference implementation of the Tool Lending Library Service."""

import math
from support import LendingException

def _is_str(x):
    return isinstance(x, str) and len(x.strip()) > 0

def _is_positive_int(x):
    return isinstance(x, int) and not isinstance(x, bool) and x > 0

def _is_positive_number(x):
    return (isinstance(x, (int, float)) and not isinstance(x, bool) and x > 0)


class Service:
    def __init__(self, clock):
        self.clock = clock
        self.members = {}       # username -> {"tier": str, "fines": float}
        self.items = {}         # item_id -> {"name": str, "category": str, "total_qty": int, "available": int, "duration_days": int}
        self.loans = {}         # loan_id -> {"username": str, "item_id": str, "due_date": float, "returned": bool, "renewed": bool}
        self.reservations = {}  # reservation_id -> {"username": str, "item_id": str}
        self._loan_counter = 0
        self._res_counter = 0

    def register_member(self, username, tier):
        if not _is_str(username) or tier not in ("standard", "premium"):
            return 400, None
        if username in self.members:
            return 409, None
        self.members[username] = {"tier": tier, "fines": 0.0}
        return 201, {"username": username, "tier": tier}

    def add_item(self, item_id, name, category, total_qty, duration_days):
        if not _is_str(item_id) or not _is_str(name) or not _is_str(category):
            return 400, None
        if not _is_positive_int(total_qty) or not _is_positive_int(duration_days):
            return 400, None
        if item_id in self.items:
            return 409, None
        self.items[item_id] = {
            "name": name,
            "category": category,
            "total_qty": total_qty,
            "available": total_qty,
            "duration_days": duration_days
        }
        return 201, {"item_id": item_id}

    def borrow_item(self, username, item_id):
        if username not in self.members or item_id not in self.items:
            return 404, None
        member = self.members[username]
        if member["fines"] >= 10.0:
            return 403, None
        item = self.items[item_id]
        if item["available"] <= 0:
            return 409, None
        
        limit = 10 if member["tier"] == "premium" else 3
        active_loans_count = sum(
            1 for l in self.loans.values()
            if l["username"] == username and not l["returned"]
        )
        if active_loans_count >= limit:
            return 409, None

        self._loan_counter += 1
        loan_id = f"L{self._loan_counter}"
        due_date = self.clock.now() + (item["duration_days"] * 86400.0)

        item["available"] -= 1
        self.loans[loan_id] = {
            "username": username,
            "item_id": item_id,
            "due_date": due_date,
            "returned": False,
            "renewed": False
        }
        return 201, {"loan_id": loan_id, "due_date": due_date}

    def return_item(self, loan_id, condition):
        if condition not in ("good", "damaged", "lost"):
            return 400, None
        if not _is_str(loan_id) or loan_id not in self.loans:
            return 404, None
        loan = self.loans[loan_id]
        if loan["returned"]:
            return 404, None

        loan["returned"] = True
        item = self.items[loan["item_id"]]
        
        fine = 0.0
        now = self.clock.now()
        if now > loan["due_date"]:
            overdue_seconds = now - loan["due_date"]
            overdue_days = math.ceil(overdue_seconds / 86400.0)
            fine += overdue_days * 2.0

        if condition == "damaged":
            fine += 15.0
            item["available"] += 1
        elif condition == "lost":
            fine += 50.0
            item["total_qty"] = max(0, item["total_qty"] - 1)
        else:
            item["available"] += 1

        if fine > 0.0:
            self.members[loan["username"]]["fines"] += fine

        return 200, {"fine": fine, "status": condition}

    def renew_loan(self, loan_id):
        if not _is_str(loan_id) or loan_id not in self.loans:
            return 404, None
        loan = self.loans[loan_id]
        if loan["returned"] or loan["renewed"]:
            return 409, None

        item_id = loan["item_id"]
        has_reservation = any(
            r["item_id"] == item_id for r in self.reservations.values()
        )
        if has_reservation:
            return 409, None

        item = self.items[item_id]
        loan["due_date"] += item["duration_days"] * 86400.0
        loan["renewed"] = True
        return 200, {"due_date": loan["due_date"]}

    def reserve_item(self, username, item_id):
        if username not in self.members or item_id not in self.items:
            return 404, None
        item = self.items[item_id]
        if item["available"] > 0:
            return 400, None

        already_reserved = any(
            r["username"] == username and r["item_id"] == item_id
            for r in self.reservations.values()
        )
        if already_reserved:
            return 409, None

        self._res_counter += 1
        res_id = f"R{self._res_counter}"
        self.reservations[res_id] = {"username": username, "item_id": item_id}
        return 201, {"reservation_id": res_id}

    def pay_fine(self, username, amount):
        if username not in self.members or not _is_positive_number(amount):
            return 400, None
        member = self.members[username]
        member["fines"] = max(0.0, member["fines"] - amount)
        return 200, {"balance": member["fines"]}

    def get_item(self, item_id):
        if item_id not in self.items:
            return 404, None
        item = self.items[item_id]
        return 200, {
            "item_id": item_id,
            "name": item["name"],
            "category": item["category"],
            "total_qty": item["total_qty"],
            "available": item["available"],
            "duration_days": item["duration_days"]
        }

    def get_member_summary(self, username):
        if username not in self.members:
            return 404, None
        member = self.members[username]
        active_loans = [
            {"loan_id": lid, "item_id": l["item_id"], "due_date": l["due_date"], "renewed": l["renewed"]}
            for lid, l in self.loans.items()
            if l["username"] == username and not l["returned"]
        ]
        res_count = sum(
            1 for r in self.reservations.values() if r["username"] == username
        )
        return 200, {
            "username": username,
            "tier": member["tier"],
            "loans": active_loans,
            "reservations_count": res_count,
            "fines": member["fines"]
        }

