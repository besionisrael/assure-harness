You are reviewing the hidden test suite of a small software benchmark. You did not
write it. Be strict and precise.

## The rule being checked

The hidden tests may require only behavior that the specification fixes. An
assertion is a PROBLEM if its expected value cannot be derived from the text of the
specification: the author decided something that is not written. A program that
follows the specification to the letter could then fail the test.

Check every assertion, and pay particular attention to these four cases:
1. Two error conditions hold in the same call (for example two different reasons
   to reject): does the specification say which status wins?
2. An ordering of results (list order, sort key, ties) that the specification does
   not state.
3. A computation or rounding (for example partial days, floor or ceiling,
   float precision) whose rule is not stated.
4. A response format detail (field name, type, None vs empty list, extra fields)
   that the interface does not describe.

Behaviors that the author's notes say were deliberately left open must not be
tested; an assertion on one of them is a PROBLEM.

## Required answer format

1. A table with one row per test function:
   | # | test | spec lines that justify each assertion | verdict (OK / PROBLEM) | reason if PROBLEM |
   For a test marked OK, the line numbers must justify every assertion of the
   test, not just one.
2. Then a section `PROBLEMS:` listing, for each PROBLEM, the test name, the
   exact assertion (copied), and one sentence on what the specification fails to
   fix. Write `PROBLEMS: none` only if every assertion is justified by cited lines.

Do not rewrite the tests, and do not suggest fixes: only review.

## Material

The specification is shown with line numbers, then the author's notes, then each
hidden test.

## Specification (with line numbers)

      1  # Tool Lending Library Service Specification
      2  
      3  ## Interface
      4  
      5  The service is a Python module `solution.py` that defines a class `Service`.
      6  Every public method returns a pair `(status, body)` where `status` is an HTTP-style integer and `body` is a `dict`, `list`, or `None`.
      7  
      8      class Service:
      9          def __init__(self, clock): ...
     10          def register_member(self, username, tier): ...                # 201 {"username": str, "tier": str} | 400 | 409
     11          def add_item(self, item_id, name, category, total_qty, duration_days): ... # 201 {"item_id": str} | 400 | 409
     12          def borrow_item(self, username, item_id): ...                # 201 {"loan_id": str, "due_date": float} | 400 | 404 | 403 | 409
     13          def return_item(self, loan_id, condition): ...               # 200 {"fine": float, "status": str} | 400 | 404
     14          def renew_loan(self, loan_id): ...                           # 200 {"due_date": float} | 400 | 404 | 409
     15          def reserve_item(self, username, item_id): ...               # 201 {"reservation_id": str} | 400 | 404 | 409
     16          def pay_fine(self, username, amount): ...                    # 200 {"balance": float} | 400 | 404
     17          def get_item(self, item_id): ...                             # 200 {"item_id": str, "name": str, "available": int, ...} | 404
     18          def get_member_summary(self, username): ...                  # 200 {"username": str, "tier": str, "loans": list, "fines": float} | 404
     19  
     20  `clock` has a method `now()` returning the current time in seconds (float).
     21  
     22  ## Requirements
     23  
     24  **REQ-1 Member Registration.** `register_member` registers a member with `username` (string) and `tier` ("standard" or "premium"). Invalid tier or empty username returns 400. If `username` already exists, returns 409. Standard members have a maximum concurrent loan limit of 3; premium members have a limit of 10.
     25  
     26  **REQ-2 Item Cataloging.** `add_item` adds an item with `item_id`, `name`, `category`, `total_qty` (positive integer), and `duration_days` (positive integer). If `total_qty` <= 0 or `duration_days` <= 0, returns 400. If `item_id` already exists, returns 409. Initial available quantity equals `total_qty`.
     27  
     28  **REQ-3 Borrowing Validation & Limits.** `borrow_item` allows a member to borrow an available item if: (a) member and item exist (otherwise 404); (b) member has no unpaid fines of 10.0 or greater (otherwise 403); (c) member has not reached their tier concurrent borrowing limit (otherwise 409); (d) item available quantity > 0 (otherwise 409). Successful borrow returns 201 with unique `loan_id` and calculated `due_date`.
     29  
     30  **REQ-4 Due Date Calculation.** The `due_date` for a loan is calculated as `clock.now() + (duration_days * 86400.0)`.
     31  
     32  **REQ-5 Returning Items.** `return_item` processes the return of a loan by `loan_id`. If `condition` is not one of "good", "damaged", or "lost", returns 400. If loan does not exist or is already returned, returns 404. Returning increments the item's available quantity by 1 (unless lost). If `clock.now()` exceeds `due_date`, a late fine of 2.0 per overdue calendar day (rounded up via ceiling of days) is added.
     33  
     34  **REQ-6 Reservations.** `reserve_item` lets a member reserve an item if it exists (otherwise 404) and is currently out of stock (available == 0). If available > 0, reservation is rejected with 400. If member already has an active reservation for this item, returns 409. Returns 201 with `reservation_id`.
     35  
     36  **REQ-7 Fines Management.** Members accumulate fines upon late returns or damaged/lost items. `pay_fine` reduces a member's fine balance by `amount` (> 0, otherwise 400). If member not found, returns 404. Returns remaining fine balance.
     37  
     38  **REQ-8 Loan Renewal.** `renew_loan` extends an active loan's `due_date` by adding `duration_days * 86400.0` to the *current* due date. Can only be done once per loan. If loan does not exist or already returned, returns 404. If item has active reservations or loan was already renewed, renewal is rejected with 409.
     39  
     40  **REQ-9 Condition and Damage Penalties.** When an item is returned as "damaged", a 15.0 fine is added to the member. When returned as "lost", a 50.0 fine is added, and `total_qty` of the item is permanently reduced by 1.
     41  
     42  **REQ-10 Summaries and Queries.** `get_item` returns item details and availability (200) or 404. `get_member_summary` returns member details, active loans, reservation count, and current unpaid fines balance (200) or 404.
     43  

## Author's notes

> # Author Notes
> 
> ## Design Choices
> - **Domain**: Tool Lending Library service managing members, item catalog, loans, reservations, and fines.
> - **State management**: Kept entirely in-memory using dictionaries indexed by IDs and usernames, injected with a `clock` object for time-dependent calculations.
> - **Fines & Penalties**: Overdue returns accrue fines per day (calculated via ceiling of overdue seconds divided by 86400.0). Damage and loss incur flat penalties and inventory adjustments.
> 
> ## Behaviors Deliberately Left Open
> - The exact tie-breaking order when multiple members reserve the same out-of-stock item is not specified (reservations are stored in a dictionary and checked generically).
> - Whether partial seconds of overdue time should trigger a full day fine immediately (handled via `math.ceil`).
> 
> ## Seeded Fault Rationales
> - **F01**: A developer might validate only that a username is present and forget to validate the membership tier string against allowed values.
> - **F02**: A developer might check that parameters are integers but forget to enforce that quantities and durations must be strictly positive (> 0).
> - **F03**: A developer might use a strict greater-than operator (`> 10.0`) instead of greater-than-or-equal (`>= 10.0`) when checking unpaid fines.
> - **F04**: A developer might hardcode the maximum concurrent loan limit to 10 for all tiers during a quick prototype and forget to implement tier-based limits.
> - **F05**: A developer might use `math.floor` instead of `math.ceil` when calculating overdue days, undercharging members for partial overdue days.
> - **F06**: A developer might mistype the fine amount for damaged items, charging a nominal $5.0 instead of the required $15.0 fee.
> - **F07**: A developer might mistakenly increment available quantity instead of reducing `total_qty` when an item is reported lost.
> - **F08**: A developer might omit checking for active reservations when renewing a loan under time pressure.
> - **F09**: A developer might forget to check the `renewed` flag, allowing members to renew loans infinitely.
> - **F10**: A developer might invert the availability check during item reservation, allowing reservations when items are still in stock.
> - **F11**: A developer might omit checking whether the payment amount is strictly positive, allowing zero or negative fine payments.
> - **F12**: A developer might forget to check if `available <= 0` when borrowing an item, leading to negative available quantities.
> 
> ## Model Identification
> - Model: Gemini (Google)

## Hidden tests (14)

### 1. `test_req1_member_validation`

```python
def test_req1_member_validation():
    svc = Service(Clock())
    assert svc.register_member("", "standard")[0] == 400
    assert svc.register_member("alice", "invalid")[0] == 400
    assert svc.register_member("alice", "standard")[0] == 201
    assert svc.register_member("alice", "premium")[0] == 409
```


### 2. `test_req2_item_validation`

```python
def test_req2_item_validation():
    svc = Service(Clock())
    assert svc.add_item("", "Hammer", "Tools", 5, 7)[0] == 400
    assert svc.add_item("i1", "Hammer", "Tools", 0, 7)[0] == 400
    assert svc.add_item("i1", "Hammer", "Tools", 5, 0)[0] == 400
    assert svc.add_item("i1", "Hammer", "Tools", 5, 7)[0] == 201
    assert svc.add_item("i1", "Saw", "Tools", 2, 7)[0] == 409
```


### 3. `test_req3_borrow_restrictions`

```python
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
```


### 4. `test_req3_borrow_limits_tier`

```python
def test_req3_borrow_limits_tier():
    svc = Service(Clock())
    svc.register_member("std", "standard")
    for i in range(4):
        svc.add_item(f"item{i}", f"Tool {i}", "Tools", 5, 7)
    
    for i in range(3):
        assert svc.borrow_item("std", f"item{i}")[0] == 201
    assert svc.borrow_item("std", "item3")[0] == 409
```


### 5. `test_req3_unpaid_fines_block_borrow`

```python
def test_req3_unpaid_fines_block_borrow():
    svc = Service(Clock())
    svc.register_member("debtor", "standard")
    svc.members["debtor"]["fines"] = 10.0
    svc.add_item("i1", "Hammer", "Tools", 5, 7)
    assert svc.borrow_item("debtor", "i1")[0] == 403
```


### 6. `test_req5_return_and_fines`

```python
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
```


### 7. `test_req5_overdue_fines`

```python
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
```


### 8. `test_req5_fractional_overdue_ceiling`

```python
def test_req5_fractional_overdue_ceiling():
    clock = Clock(0.0)
    svc = Service(clock)
    svc.register_member("alice", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 1)
    _, body = svc.borrow_item("alice", "i1")
    loan_id = body["loan_id"]
    
    clock.t = (1 * 86400.0) + 1.0  # 1 second past due date
    res = svc.return_item(loan_id, "good")
    assert res[0] == 200
    assert res[1]["fine"] == 2.0  # Ceiling of 1/86400 days is 1 day * 2.0
```


### 9. `test_req6_reservations`

```python
def test_req6_reservations():
    svc = Service(Clock())
    svc.register_member("alice", "standard")
    svc.register_member("bob", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 7)
    
    assert svc.reserve_item("bob", "i1")[0] == 400
    svc.borrow_item("alice", "i1")
    assert svc.reserve_item("bob", "i1")[0] == 201
    assert svc.reserve_item("bob", "i1")[0] == 409
```


### 10. `test_req7_pay_fine_validation`

```python
def test_req7_pay_fine_validation():
    svc = Service(Clock())
    svc.register_member("alice", "standard")
    assert svc.pay_fine("alice", 0)[0] == 400
    assert svc.pay_fine("alice", -5.0)[0] == 400
```


### 11. `test_req8_renew_loan`

```python
def test_req8_renew_loan():
    svc = Service(Clock(0.0))
    svc.register_member("alice", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 7)
    _, body = svc.borrow_item("alice", "i1")
    loan_id = body["loan_id"]
    
    assert svc.renew_loan(loan_id)[0] == 200
    assert svc.renew_loan(loan_id)[0] == 409
```


### 12. `test_req8_renew_blocked_by_reservation`

```python
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
```


### 13. `test_req9_damaged_and_lost`

```python
def test_req9_damaged_and_lost():
    svc = Service(Clock())
    svc.register_member("alice", "standard")
    svc.add_item("i1", "Hammer", "Tools", 1, 7)
    _, b1 = svc.borrow_item("alice", "i1")
    
    svc.add_item("i2", "Saw", "Tools", 1, 7)
    _, b2 = svc.borrow_item("alice", "i2")
    
    r1 = svc.return_item(b1["loan_id"], "damaged")
    assert r1[1]["fine"] == 15.0
    assert svc.items["i1"]["available"] == 1
    
    r2 = svc.return_item(b2["loan_id"], "lost")
    assert r2[1]["fine"] == 50.0
    assert svc.items["i2"]["total_qty"] == 0
```


### 14. `test_stateful_library`

```python
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
```

