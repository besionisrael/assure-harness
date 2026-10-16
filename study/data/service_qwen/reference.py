"""Reference implementation of the Equipment Loan Service."""


def _is_nonempty_str(x):
    return isinstance(x, str) and len(x) > 0


_ROLES = ("member", "staff")


class Service:
    def __init__(self, clock, max_loans=3, max_renewals=2, loan_period=7.0):
        self.clock = clock
        self.max_loans = max_loans
        self.max_renewals = max_renewals
        self.loan_period = loan_period
        self._users = {}            # user_id -> role
        self._items = {}            # item_id -> name
        self._loans = {}            # loan_id -> loan dict
        self._item_loan = {}        # item_id -> active loan_id
        self._next_loan_id = 1

    # ---- helpers -------------------------------------------------------
    def _active_count(self, user_id):
        n = 0
        for loan in self._loans.values():
            if loan["user"] == user_id and loan["status"] == "active":
                n += 1
        return n

    def _owned_or_staff(self, user_id, loan):
        if loan["user"] == user_id:
            return True
        return self._users.get(user_id) == "staff"

    # ---- REQ-1 ---------------------------------------------------------
    def register_user(self, user_id, role):
        if not (_is_nonempty_str(user_id) and role in _ROLES):
            return 400, None
        if user_id in self._users:
            return 409, None
        self._users[user_id] = role
        return 201, {"user_id": user_id, "role": role}

    # ---- REQ-2 ---------------------------------------------------------
    def add_item(self, item_id, name):
        if not (_is_nonempty_str(item_id) and _is_nonempty_str(name)):
            return 400, None
        if item_id in self._items:
            return 409, None
        self._items[item_id] = name
        return 201, {"item_id": item_id, "name": name}

    # ---- REQ-3 ---------------------------------------------------------
    def checkout(self, user_id, item_id):
        if user_id not in self._users:
            return 404, None
        if item_id not in self._items:
            return 404, None
        if item_id in self._item_loan:
            return 409, None
        if self._active_count(user_id) >= self.max_loans:
            return 422, None
        loan_id = self._next_loan_id
        self._next_loan_id += 1
        due_at = self.clock.now() + self.loan_period
        self._loans[loan_id] = {
            "id": loan_id,
            "user": user_id,
            "item": item_id,
            "due_at": due_at,
            "renewals_used": 0,
            "status": "active",
        }
        self._item_loan[item_id] = loan_id
        return 200, {"loan_id": loan_id, "due_at": due_at}

    # ---- REQ-4 ---------------------------------------------------------
    def return_loan(self, user_id, loan_id):
        loan = self._loans.get(loan_id)
        if loan is None:
            return 404, None
        if not self._owned_or_staff(user_id, loan):
            return 403, None
        if loan["status"] == "returned":
            return 409, None
        loan["status"] = "returned"
        self._item_loan.pop(loan["item"], None)
        return 200, {"item_id": loan["item"]}

    # ---- REQ-5 ---------------------------------------------------------
    def renew_loan(self, user_id, loan_id):
        loan = self._loans.get(loan_id)
        if loan is None:
            return 404, None
        if not self._owned_or_staff(user_id, loan):
            return 403, None
        if loan["status"] == "returned":
            return 409, None
        if self.clock.now() > loan["due_at"]:
            return 409, None
        if loan["renewals_used"] >= self.max_renewals:
            return 422, None
        loan["due_at"] = loan["due_at"] + self.loan_period
        loan["renewals_used"] += 1
        return 200, {"due_at": loan["due_at"]}

    # ---- REQ-6 ---------------------------------------------------------
    def list_loans(self, user_id):
        if user_id not in self._users:
            return 404, None
        rows = []
        for loan in self._loans.values():
            if loan["user"] == user_id:
                rows.append({
                    "loan_id": loan["id"],
                    "item_id": loan["item"],
                    "due_at": loan["due_at"],
                    "renewals_used": loan["renewals_used"],
                    "status": loan["status"],
                })
        rows.sort(key=lambda r: r["loan_id"])
        return 200, rows

    # ---- REQ-7 ---------------------------------------------------------
    def item_status(self, item_id):
        if item_id not in self._items:
            return 404, None
        loan_id = self._item_loan.get(item_id)
        return 200, {"available": loan_id is None, "loan_id": loan_id}
