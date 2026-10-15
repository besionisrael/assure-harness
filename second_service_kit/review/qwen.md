# Relecture : qwen

**Question à trancher, pour chaque test caché :** chaque assertion découle-t-elle
d'une phrase de la spécification ? Un test est **à problème** s'il exige un
comportement que la spécification ne permet pas de déduire : un code d'erreur non
listé, un ordre non spécifié, la priorité entre deux erreurs, un format de
réponse non décrit, une valeur limite ambiguë, etc.

Pour chaque test, inscris les lignes de la spécification qui le justifient, coche
une case, et ajoute une note si besoin. La relecture porte sur les tests, pas sur
la qualité du service.

Réponse attendue en fin de relecture : la liste des tests à problème. Ils seront
signalés au modèle auteur, qui les corrigera (on ne les modifie pas nous-mêmes).

## Spécification (numéros de ligne)

      1  # Equipment Loan Service
      2  
      3  A small in‑process service that models a lab/library lending physical equipment
      4  items to registered users. State evolves through an injected clock.
      5  
      6  ## Interface
      7  
      8  The service is a Python module `solution.py` defining one class `Service`.
      9  Every public method returns a pair `(status, body)` where `status` is an
     10  HTTP‑style integer and `body` is a `dict`, a `list`, or `None`.
     11  
     12      class Service:
     13          def __init__(self, clock, max_loans=3, max_renewals=2, loan_period=7.0): ...
     14          def register_user(self, user_id, role): ...     # 201 | 400 | 409
     15          def add_item(self, item_id, name): ...           # 201 | 400 | 409
     16          def checkout(self, user_id, item_id): ...        # 200 | 404 | 409 | 422
     17          def return_loan(self, user_id, loan_id): ...     # 200 | 404 | 403 | 409
     18          def renew_loan(self, user_id, loan_id): ...      # 200 | 404 | 403 | 409 | 422
     19          def list_loans(self, user_id): ...               # 200 | 404
     20          def item_status(self, item_id): ...              # 200 | 404
     21  
     22  `clock` is any object exposing `now()` returning a float (seconds). All time
     23  decisions use only `clock.now()`; the wall clock is never read.
     24  
     25  Constructor parameters: `max_loans` and `max_renewals` are non‑negative
     26  integers, `loan_period` a positive number. Their exact validation beyond the
     27  stated types/ranges is left open.
     28  
     29  Roles are exactly `"member"` and `"staff"`. An identifier (`user_id`,
     30  `item_id`) or `name` is valid iff it is a non‑empty `str`.
     31  
     32  ## Response bodies
     33  
     34  - `register_user` 201: `{"user_id": str, "role": str}`
     35  - `add_item` 201: `{"item_id": str, "name": str}`
     36  - `checkout` 200: `{"loan_id": int, "due_at": float}`
     37  - `return_loan` 200: `{"item_id": str}`
     38  - `renew_loan` 200: `{"due_at": float}`
     39  - `list_loans` 200: a `list` of loan objects, each
     40    `{"loan_id": int, "item_id": str, "due_at": float,
     41    "renewals_used": int, "status": str}` where `status` is `"active"` or
     42    `"returned"`.
     43  - `item_status` 200: `{"available": bool, "loan_id": int | None}`
     44  
     45  ## Requirements
     46  
     47  **REQ‑1 Register user.** `register_user` creates a user. If `user_id` or
     48  `role` is invalid (see above) return 400. If `user_id` already exists return
     49  409. Otherwise store the role and return 201 with the body above.
     50  
     51  **REQ‑2 Add item.** `add_item` adds catalog inventory keyed by `item_id`.
     52  If `item_id` or `name` is invalid return 400. If `item_id` already exists
     53  return 409. Two distinct items may share the same `name`. Otherwise return
     54  201 with the body above.
     55  
     56  **REQ‑3 Checkout.** Checks run in this order, first match wins:
     57  1. If `user_id` is not registered return 404.
     58  2. If `item_id` is not in the catalog return 404.
     59  3. If the item currently has an active loan return 409.
     60  4. If the user already has `max_loans` or more active loans return 422.
     61  Otherwise create a new loan: assign the next sequential `loan_id` starting at
     62  1, record `user_id`, `item_id`, `due_at = clock.now() + loan_period`,
     63  `renewals_used = 0`, `status = "active"`, mark the item as on loan, and
     64  return 200 with `{"loan_id", "due_at"}`.
     65  
     66  **REQ‑4 Return loan.** Checks run in this order:
     67  1. If `loan_id` is unknown return 404.
     68  2. If the loan is not owned by `user_id` and the caller's role is not
     69     `"staff"` return 403.
     70  3. If the loan's status is already `"returned"` return 409.
     71  Otherwise set its status to `"returned"`, free the item (it becomes available
     72  again), and return 200 with `{"item_id"}`.
     73  
     74  **REQ‑5 Renew loan.** Checks run in this order:
     75  1. If `loan_id` is unknown return 404.
     76  2. If the loan is not owned by `user_id` and the caller's role is not
     77     `"staff"` return 403.
     78  3. If the loan's status is `"returned"` return 409.
     79  4. If `clock.now() > due_at` (strictly overdue) return 409.
     80  5. If `renewals_used >= max_renewals` return 422.
     81  Otherwise set `due_at = due_at + loan_period`, increment `renewals_used`, and
     82  return 200 with `{"due_at"}`.
     83  
     84  **REQ‑6 List loans.** If `user_id` is not registered return 404. Otherwise
     85  return every loan ever created for that user (active and returned), as a list
     86  sorted by `loan_id` ascending, using the loan object shape above.
     87  
     88  **REQ‑7 Item status.** If `item_id` is not in the catalog return 404.
     89  Otherwise `available` is `True` iff the item has no active loan; `loan_id` is
     90  that active loan's id, or `None` if available.
     91  
     92  **REQ‑8 Staff privilege.** A `"staff"` user may call `return_loan` and
     93  `renew_loan` on any loan regardless of ownership. A `"member"` may act only
     94  on loans they own (otherwise 403). This applies to the ownership check in
     95  REQ‑4 step 2 and REQ‑5 step 2.
     96  
     97  **REQ‑9 Limits are configurable.** `max_loans` caps simultaneous active loans
     98  per user (REQ‑3 step 4) and `max_renewals` caps renewals per loan (REQ‑5
     99  step 5). With the defaults (3 and 2) a user may hold at most 3 active loans
    100  and renew a loan at most 2 times.
    101  
    102  **REQ‑10 Time comes from the clock.** Every `due_at` value and every
    103  overdue decision is derived solely from `clock.now()` at the moment of the
    104  relevant call; no other time source is consulted.

## Notes de l'auteur (comportements laissés ouverts, etc.)

> # Author notes
> 
> ## Design choices
> 
> - Domain: physical equipment loans (catalog + users + loans). Chosen because it
>   exercises shared mutable resources, per-user quotas, time-based rules, and a
>   role-based override, while staying in-process and deterministic.
> - Status codes follow the usual REST-ish convention: 200/201 success, 400 bad
>   input, 403 forbidden, 404 not found, 409 conflict, 422 unprocessable.
> - Check-order precedence (REQ-3/4/5) is spelled out in the spec so hidden tests
>   can rely on a single observable code for overlapping conditions.
> 
> ## Behaviors deliberately left open (NOT tested)
> 
> - Exact validation of the constructor arguments (`max_loans`, `max_renewals`,
>   `loan_period`) beyond the documented types/ranges.
> - Whether `return_loan`/`renew_loan` of a *nonexistent* id is reported before
>   or after an ownership failure — the spec fixes existence first, so only that
>   order is tested; nothing else about error precedence outside the listed steps.
> - Internal representation of `loan_id` (only the sequence-from-1 property is
>   specified).
> - Tie-breaking is impossible (ids unique), so ordering stability is unspecified.
> - Behavior of registering with a name identical to another user's id is not a
>   concept here; ids are global keys.
> 
> ## Why each fault is plausible (one line each)
> 
> - **F01**: copy-pasting a longer role list from another product's docs.
> - **F02**: "just overwrite" convenience that quietly kills the conflict code.
> - **F03**: confusing business-level uniqueness (by name) with key uniqueness.
> - **F04**: using `* 2` instead of `+ period` when wiring the extension formula.
> - **F05**: zero-based indexing habit leaking into a public id sequence.
> - **F06**: forgetting the side-effect line that reserves the resource.
> - **F07**: `>=` vs `>` boundary mistake on a quota check.
> - **F08**: removing a guard during a refactor that assumed callers were trusted.
> - **F09**: updating status but forgetting the companion release of the lock.
> - **F10**: inclusive-vs-exclusive comparison on a deadline.
> - **F11**: resetting a counter instead of incrementing it.
> - **F12**: mirror-image boundary slip on the renewal cap.
> - **F13**: dropping a filter predicate while optimizing iteration.
> - **F14**: forgetting to forward the loan id into the response dict.
> - **F15**: stubbing out a permission branch and leaving the stub in place.

## Tests cachés (27)

### 1. `test_req1_invalid_inputs` (REQ-1 d'après son nom)

```python
def test_req1_invalid_inputs():
    svc = Service(Clock())
    for bad_id in ["", None, 5, True]:
        assert svc.register_user(bad_id, "member")[0] == 400, bad_id
    for bad_role in ["", "guest", "MEMBER", None, 1]:
        assert svc.register_user("u", bad_role)[0] == 400, bad_role
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 2. `test_req1_duplicate_user` (REQ-1 d'après son nom)

```python
def test_req1_duplicate_user():
    svc = Service(Clock())
    assert svc.register_user("ann", "member") == (201, {"user_id": "ann", "role": "member"})
    assert svc.register_user("ann", "staff")[0] == 409
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 3. `test_req2_invalid_inputs` (REQ-2 d'après son nom)

```python
def test_req2_invalid_inputs():
    svc = Service(Clock())
    for bad in ["", None, 3]:
        assert svc.add_item(bad, "n")[0] == 400, bad
        assert svc.add_item("i", bad)[0] == 400, bad
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 4. `test_req2_duplicate_id_but_shared_name` (REQ-2 d'après son nom)

```python
def test_req2_duplicate_id_but_shared_name():
    svc = Service(Clock())
    assert svc.add_item("a", "Hammer")[0] == 201
    assert svc.add_item("b", "Hammer")[0] == 201          # same name ok
    assert svc.add_item("a", "Saw")[0] == 409             # same id clash
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 5. `test_req3_check_order_and_codes` (REQ-3 d'après son nom)

```python
def test_req3_check_order_and_codes():
    svc = Service(Clock())
    assert svc.checkout("ghost", "x")[0] == 404           # user missing first
    svc.register_user("ann", "member")
    assert svc.checkout("ann", "ghost")[0] == 404         # item missing
    svc.add_item("tool", "Tool")
    assert svc.checkout("ann", "tool")[0] == 200
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 6. `test_req3_due_at_uses_clock_plus_period` (REQ-3 d'après son nom)

```python
def test_req3_due_at_uses_clock_plus_period():
    clk = Clock(50.0)
    svc = Service(clk, loan_period=4.0)
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    st, b = svc.checkout("ann", "t")
    assert st == 200 and b["due_at"] == 54.0
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 7. `test_req3_loan_ids_sequential_from_one` (REQ-3 d'après son nom)

```python
def test_req3_loan_ids_sequential_from_one():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    for i in range(3):
        svc.add_item(f"t{i}", "T")
    ids = [svc.checkout("ann", f"t{i}")[1]["loan_id"] for i in range(3)]
    assert ids == [1, 2, 3]
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 8. `test_req3_item_on_loan_conflict` (REQ-3 d'après son nom)

```python
def test_req3_item_on_loan_conflict():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("bob", "member")
    svc.add_item("t", "T")
    assert svc.checkout("ann", "t")[0] == 200
    assert svc.checkout("bob", "t")[0] == 409
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 9. `test_req3_max_loans_boundary` (REQ-3 d'après son nom)

```python
def test_req3_max_loans_boundary():
    svc = Service(Clock(), max_loans=2)
    svc.register_user("ann", "member")
    for i in range(3):
        svc.add_item(f"t{i}", "T")
    assert svc.checkout("ann", "t0")[0] == 200
    assert svc.checkout("ann", "t1")[0] == 200
    assert svc.checkout("ann", "t2")[0] == 422            # already at limit
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 10. `test_req4_unknown_loan_404` (REQ-4 d'après son nom)

```python
def test_req4_unknown_loan_404():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    assert svc.return_loan("ann", 999)[0] == 404
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 11. `test_req4_not_owner_member_forbidden` (REQ-4 d'après son nom)

```python
def test_req4_not_owner_member_forbidden():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("bob", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.return_loan("bob", lid)[0] == 403
    # still active for ann
    assert svc.item_status("t")[1]["available"] is False
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 12. `test_req4_already_returned_conflict` (REQ-4 d'après son nom)

```python
def test_req4_already_returned_conflict():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.return_loan("ann", lid)[0] == 200
    assert svc.return_loan("ann", lid)[0] == 409
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 13. `test_req4_return_frees_item` (REQ-4 d'après son nom)

```python
def test_req4_return_frees_item():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.item_status("t") == (200, {"available": False, "loan_id": lid})
    assert svc.return_loan("ann", lid)[0] == 200
    assert svc.item_status("t") == (200, {"available": True, "loan_id": None})
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 14. `test_req5_unknown_and_forbidden` (REQ-5 d'après son nom)

```python
def test_req5_unknown_and_forbidden():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("bob", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.renew_loan("ann", 999)[0] == 404
    assert svc.renew_loan("bob", lid)[0] == 403
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 15. `test_req5_returned_cannot_renew` (REQ-5 d'après son nom)

```python
def test_req5_returned_cannot_renew():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    svc.return_loan("ann", lid)
    assert svc.renew_loan("ann", lid)[0] == 409
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 16. `test_req5_overdue_boundary_strict` (REQ-5 d'après son nom)

```python
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
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 17. `test_req5_renewal_cap_boundary` (REQ-5 d'après son nom)

```python
def test_req5_renewal_cap_boundary():
    svc = Service(Clock(), loan_period=10.0, max_renewals=2)
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.renew_loan("ann", lid)[0] == 200       # used 1
    assert svc.renew_loan("ann", lid)[0] == 200       # used 2
    assert svc.renew_loan("ann", lid)[0] == 422       # at cap
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 18. `test_req5_renew_extends_by_period` (REQ-5 d'après son nom)

```python
def test_req5_renew_extends_by_period():
    clk = Clock(0.0)
    svc = Service(clk, loan_period=8.0, max_renewals=3)
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]      # due 8
    st, b = svc.renew_loan("ann", lid)
    assert st == 200 and b["due_at"] == 16.0
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 19. `test_req6_unknown_user_404` (REQ-6 d'après son nom)

```python
def test_req6_unknown_user_404():
    svc = Service(Clock())
    assert svc.list_loans("ghost")[0] == 404
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 20. `test_req6_only_own_loans_sorted_with_statuses` (REQ-6 d'après son nom)

```python
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
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 21. `test_req7_unknown_item_404` (REQ-7 d'après son nom)

```python
def test_req7_unknown_item_404():
    svc = Service(Clock())
    assert svc.item_status("ghost")[0] == 404
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 22. `test_req7_availability_tracks_active_loan` (REQ-7 d'après son nom)

```python
def test_req7_availability_tracks_active_loan():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    assert svc.item_status("t") == (200, {"available": True, "loan_id": None})
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.item_status("t") == (200, {"available": False, "loan_id": lid})
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 23. `test_req8_staff_can_act_on_others` (REQ-8 d'après son nom)

```python
def test_req8_staff_can_act_on_others():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("admin", "staff")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.renew_loan("admin", lid)[0] == 200
    assert svc.return_loan("admin", lid)[0] == 200
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 24. `test_req8_member_still_forbidden_after_staff_rule` (REQ-8 d'après son nom)

```python
def test_req8_member_still_forbidden_after_staff_rule():
    svc = Service(Clock())
    svc.register_user("ann", "member")
    svc.register_user("bob", "member")
    svc.add_item("t", "T")
    lid = svc.checkout("ann", "t")[1]["loan_id"]
    assert svc.renew_loan("bob", lid)[0] == 403
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 25. `test_req9_custom_limits` (REQ-9 d'après son nom)

```python
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
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 26. `test_req10_no_wall_clock_dependency` (REQ-10 d'après son nom)

```python
def test_req10_no_wall_clock_dependency():
    # two clocks give independent timelines
    svc = Service(Clock(10.0), loan_period=5.0)
    svc.register_user("ann", "member")
    svc.add_item("t", "T")
    assert svc.checkout("ann", "t")[1]["due_at"] == 15.0
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……

### 27. `test_stateful_model`

```python
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
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……
