# Tool Lending Library Service Specification

## Interface

The service is a Python module `solution.py` that defines a class `Service`.
Every public method returns a pair `(status, body)` where `status` is an HTTP-style integer and `body` is a `dict`, `list`, or `None`.

    class Service:
        def __init__(self, clock): ...
        def register_member(self, username, tier): ...                # 201 {"username": str, "tier": str} | 400 | 409
        def add_item(self, item_id, name, category, total_qty, duration_days): ... # 201 {"item_id": str} | 400 | 409
        def borrow_item(self, username, item_id): ...                # 201 {"loan_id": str, "due_date": float} | 400 | 404 | 403 | 409
        def return_item(self, loan_id, condition): ...               # 200 {"fine": float, "status": str} | 400 | 404
        def renew_loan(self, loan_id): ...                           # 200 {"due_date": float} | 400 | 404 | 409
        def reserve_item(self, username, item_id): ...               # 201 {"reservation_id": str} | 400 | 404 | 409
        def pay_fine(self, username, amount): ...                    # 200 {"balance": float} | 400 | 404
        def get_item(self, item_id): ...                             # 200 {"item_id": str, "name": str, "available": int, ...} | 404
        def get_member_summary(self, username): ...                  # 200 {"username": str, "tier": str, "loans": list, "fines": float} | 404

`clock` has a method `now()` returning the current time in seconds (float).

## Requirements

**REQ-1 Member Registration.** `register_member` registers a member with `username` (string) and `tier` ("standard" or "premium"). If `username` is empty/whitespace or `tier` is invalid, returns 400. If `username` already exists, returns 409. Standard members have a maximum concurrent loan limit of 3; premium members have a limit of 10.

**REQ-2 Item Cataloging.** `add_item` adds an item with `item_id`, `name`, `category`, `total_qty` (positive integer), and `duration_days` (positive integer). If `item_id` is empty/whitespace, or `total_qty` <= 0, or `duration_days` <= 0, returns 400. If `item_id` already exists, returns 409. Initial available quantity equals `total_qty`.

**REQ-3 Borrowing Validation & Limits.** `borrow_item` allows a member to borrow an available item if: (a) member and item exist (otherwise 404); (b) member has no unpaid fines of 10.0 or greater (otherwise 403); (c) member has not reached their tier concurrent borrowing limit (otherwise 409); (d) item available quantity > 0 (otherwise 409). Successful borrow returns 201 with unique `loan_id` and calculated `due_date`.

**REQ-4 Due Date Calculation.** The `due_date` for a loan is calculated as `clock.now() + (duration_days * 86400.0)`.

**REQ-5 Returning Items.** `return_item` processes the return of a loan by `loan_id`. If `condition` is not one of "good", "damaged", or "lost", returns 400. If loan does not exist or is already returned, returns 404. Returning increments the item's available quantity by 1 (unless lost). If `clock.now()` exceeds `due_date`, a late fine of 2.0 per overdue calendar day (rounded up via ceiling of days) is added. Successful return returns 200 with `{"fine": float, "status": str}` where `status` is the exact condition string passed in (`"good"`, `"damaged"`, or `"lost"`).

**REQ-6 Reservations.** `reserve_item` lets a member reserve an item if it exists (otherwise 404) and is currently out of stock (available == 0). If available > 0, reservation is rejected with 400. If member already has an active reservation for this item, returns 409. Returns 201 with `reservation_id`.

**REQ-7 Fines Management.** Members accumulate fines upon late returns or damaged/lost items. `pay_fine` reduces a member's fine balance by `amount` (> 0, otherwise 400). If member not found, returns 404. Returns remaining fine balance.

**REQ-8 Loan Renewal.** `renew_loan` extends an active loan's `due_date` by adding `duration_days * 86400.0` to the *current* due date. Can only be done once per loan. If loan does not exist or already returned, returns 404. If item has active reservations or loan was already renewed, renewal is rejected with 409.

**REQ-9 Condition and Damage Penalties.** When an item is returned as "damaged", a 15.0 fine is added to the member. When returned as "lost", a 50.0 fine is added, and `total_qty` of the item is permanently reduced by 1.

**REQ-10 Summaries and Queries.** `get_item` returns item details and availability (200) or 404. `get_member_summary` returns member details, active loans, reservation count, and current unpaid fines balance (200) or 404.

