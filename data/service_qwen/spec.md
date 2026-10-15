# Equipment Loan Service

A small in‑process service that models a lab/library lending physical equipment
items to registered users. State evolves through an injected clock.

## Interface

The service is a Python module `solution.py` defining one class `Service`.
Every public method returns a pair `(status, body)` where `status` is an
HTTP‑style integer and `body` is a `dict`, a `list`, or `None`.

    class Service:
        def __init__(self, clock, max_loans=3, max_renewals=2, loan_period=7.0): ...
        def register_user(self, user_id, role): ...     # 201 | 400 | 409
        def add_item(self, item_id, name): ...           # 201 | 400 | 409
        def checkout(self, user_id, item_id): ...        # 200 | 404 | 409 | 422
        def return_loan(self, user_id, loan_id): ...     # 200 | 404 | 403 | 409
        def renew_loan(self, user_id, loan_id): ...      # 200 | 404 | 403 | 409 | 422
        def list_loans(self, user_id): ...               # 200 | 404
        def item_status(self, item_id): ...              # 200 | 404

`clock` is any object exposing `now()` returning a float (seconds). All time
decisions use only `clock.now()`; the wall clock is never read.

Constructor parameters: `max_loans` and `max_renewals` are non‑negative
integers, `loan_period` a positive number. Their exact validation beyond the
stated types/ranges is left open.

Roles are exactly `"member"` and `"staff"`. An identifier (`user_id`,
`item_id`) or `name` is valid iff it is a non‑empty `str`.

## Response bodies

- `register_user` 201: `{"user_id": str, "role": str}`
- `add_item` 201: `{"item_id": str, "name": str}`
- `checkout` 200: `{"loan_id": int, "due_at": float}`
- `return_loan` 200: `{"item_id": str}`
- `renew_loan` 200: `{"due_at": float}`
- `list_loans` 200: a `list` of loan objects, each
  `{"loan_id": int, "item_id": str, "due_at": float,
  "renewals_used": int, "status": str}` where `status` is `"active"` or
  `"returned"`.
- `item_status` 200: `{"available": bool, "loan_id": int | None}`

## Requirements

**REQ‑1 Register user.** `register_user` creates a user. If `user_id` or
`role` is invalid (see above) return 400. If `user_id` already exists return
409. Otherwise store the role and return 201 with the body above.

**REQ‑2 Add item.** `add_item` adds catalog inventory keyed by `item_id`.
If `item_id` or `name` is invalid return 400. If `item_id` already exists
return 409. Two distinct items may share the same `name`. Otherwise return
201 with the body above.

**REQ‑3 Checkout.** Checks run in this order, first match wins:
1. If `user_id` is not registered return 404.
2. If `item_id` is not in the catalog return 404.
3. If the item currently has an active loan return 409.
4. If the user already has `max_loans` or more active loans return 422.
Otherwise create a new loan: assign the next sequential `loan_id` starting at
1, record `user_id`, `item_id`, `due_at = clock.now() + loan_period`,
`renewals_used = 0`, `status = "active"`, mark the item as on loan, and
return 200 with `{"loan_id", "due_at"}`.

**REQ‑4 Return loan.** Checks run in this order:
1. If `loan_id` is unknown return 404.
2. If the loan is not owned by `user_id` and the caller's role is not
   `"staff"` return 403.
3. If the loan's status is already `"returned"` return 409.
Otherwise set its status to `"returned"`, free the item (it becomes available
again), and return 200 with `{"item_id"}`.

**REQ‑5 Renew loan.** Checks run in this order:
1. If `loan_id` is unknown return 404.
2. If the loan is not owned by `user_id` and the caller's role is not
   `"staff"` return 403.
3. If the loan's status is `"returned"` return 409.
4. If `clock.now() > due_at` (strictly overdue) return 409.
5. If `renewals_used >= max_renewals` return 422.
Otherwise set `due_at = due_at + loan_period`, increment `renewals_used`, and
return 200 with `{"due_at"}`.

**REQ‑6 List loans.** If `user_id` is not registered return 404. Otherwise
return every loan ever created for that user (active and returned), as a list
sorted by `loan_id` ascending, using the loan object shape above.

**REQ‑7 Item status.** If `item_id` is not in the catalog return 404.
Otherwise `available` is `True` iff the item has no active loan; `loan_id` is
that active loan's id, or `None` if available.

**REQ‑8 Staff privilege.** A `"staff"` user may call `return_loan` and
`renew_loan` on any loan regardless of ownership. A `"member"` may act only
on loans they own (otherwise 403). This applies to the ownership check in
REQ‑4 step 2 and REQ‑5 step 2.

**REQ‑9 Limits are configurable.** `max_loans` caps simultaneous active loans
per user (REQ‑3 step 4) and `max_renewals` caps renewals per loan (REQ‑5
step 5). With the defaults (3 and 2) a user may hold at most 3 active loans
and renew a loan at most 2 times.

**REQ‑10 Time comes from the clock.** Every `due_at` value and every
overdue decision is derived solely from `clock.now()` at the moment of the
relevant call; no other time source is consulted.
