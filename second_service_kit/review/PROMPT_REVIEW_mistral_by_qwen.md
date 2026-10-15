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

      1  # Room reservation service
      2  
      3  A service that manages meeting rooms. Users book seats in a room for a time
      4  interval on a given day. A room's capacity is shared by all overlapping
      5  bookings. Users can cancel or move their bookings and list them.
      6  
      7  The service is stateful and in-process. It never reads the system clock and
      8  never uses randomness: all time information comes from the injected clock.
      9  
     10  ## Interface
     11  
     12  The service is a Python module `solution.py` that defines a class `Service`.
     13  The constructor takes one argument, a clock object with a method `today()`
     14  that returns the current day number as an integer.
     15  
     16  Every public method returns a pair `(status, body)`. `status` is an HTTP-style
     17  integer. `body` is a dict, a list, or None. The body is None for every status
     18  that is not 2xx.
     19  
     20  A booking record is a dict with exactly these keys:
     21  
     22      {"booking_id": int, "room": str, "day": int, "start": int, "end": int, "seats": int}
     23  
     24      class Service:
     25          def __init__(self, clock): ...
     26          def create_room(self, room, capacity): ...
     27              # 201 {"room": str} | 400 None | 409 None
     28          def book(self, user, room, day, start, end, seats): ...
     29              # 201 booking record | 404 None | 400 None | 409 None
     30          def cancel(self, user, booking_id): ...
     31              # 200 {"status": "cancelled"} | 404 None | 409 None
     32          def move(self, user, booking_id, new_day, new_start, new_end): ...
     33              # 200 booking record | 404 None | 400 None | 409 None
     34          def list_bookings(self, user): ...
     35              # 200 list of booking records
     36  
     37  ## Requirements
     38  
     39  **REQ-1 Room creation.** `create_room(room, capacity)` registers a room.
     40  `room` must be a string that is non-empty and has no leading or trailing
     41  whitespace; `capacity` must be an integer with 1 <= capacity <= 50. If either
     42  is invalid the method returns 400. A bool is not an integer anywhere in this
     43  specification. If a room with the same name already exists it returns 409.
     44  Validation (400) is checked before existence (409). On success it returns
     45  201 with body {"room": room}.
     46  
     47  **REQ-2 Time validity.** A time is a triple (day, start, end) where day,
     48  start and end are integers (bools rejected) with 0 <= day <= 365,
     49  day >= clock.today(), 0 <= start < end <= 24. The interval occupied by a
     50  booking is [start, end) in whole hours. Any method given an invalid time
     51  returns 400 and changes nothing.
     52  
     53  **REQ-3 Booking.** `book(user, room, day, start, end, seats)` checks, in this
     54  order: the room must exist, else 404; the time must be valid (REQ-2), else
     55  400; `seats` must be an integer with 1 <= seats <= the room's capacity,
     56  else 400; the capacity constraint (REQ-4) must hold, else 409.
     57  
     58  **REQ-4 Capacity.** For every hour h in [start, end), the sum of the seats of
     59  all active bookings in that room, on that day, covering hour h, must not
     60  exceed the room's capacity. A booking request that would violate this for at
     61  least one hour returns 409 and changes nothing.
     62  
     63  **REQ-5 Identifiers.** Every successful booking receives a `booking_id`:
     64  integers starting at 1, increasing by 1 for each new booking, unique across
     65  all bookings ever made, never reused. On success `book` returns 201 with the
     66  booking record.
     67  
     68  **REQ-6 Ownership.** A booking belongs to the user who created it. For
     69  `cancel`, `move` and `list_bookings`, a booking id that does not exist and a
     70  booking id owned by another user are both handled exactly as a missing
     71  booking: 404 for `cancel` and `move`. `list_bookings(user)` returns only that
     72  user's bookings.
     73  
     74  **REQ-7 Cancellation.** `cancel(user, booking_id)` on an active booking owned
     75  by the user returns 200 with body {"status": "cancelled"}; the booking becomes
     76  cancelled and its seats stop counting for REQ-4. Cancelling a booking that is
     77  already cancelled returns 409.
     78  
     79  **REQ-8 Move.** `move(user, booking_id, new_day, new_start, new_end)` moves
     80  the booking to a new time in the same room with the same seats; it cannot
     81  change the room or the seat count. Checks in this order: the booking must
     82  exist and belong to the user (REQ-6), else 404; it must be active, else 409;
     83  the new time must be valid (REQ-2), else 400; the capacity constraint
     84  (REQ-4) must hold for the new time, else 409. For the capacity check the
     85  booking's own current seats do not count as usage at hours it currently
     86  occupies. On success it returns 200 with the booking record updated to the
     87  new day, start and end. On any failure the booking and all capacity state are
     88  unchanged.
     89  
     90  **REQ-9 Listing.** `list_bookings(user)` returns 200 and a list of the
     91  user's active bookings, each a booking record with exactly the keys of REQ-5,
     92  sorted by (day, start, booking_id) ascending. A user with no active bookings
     93  gets an empty list.
     94  
     95  **REQ-10 Cancelled bookings.** A cancelled booking keeps its identifier, does
     96  not occupy any capacity, does not appear in listings, and can be neither
     97  cancelled again (REQ-7) nor moved (REQ-8).

## Author's notes

> # Author notes — room reservation service
> 
> ## Design choices
> 
> - Domain: shared-capacity room reservations. Capacity is a *shared* resource
>   (overlapping bookings allowed until the seat sum exceeds capacity), which
>   gives richer state than pure exclusive booking and realistic conflicts.
> - The clock is injected and only used via `clock.today()`; nothing else in the
>   service is time- or randomness-dependent, so all tests are deterministic.
> - Internal model: per (room, day) a 24-slot array of seats in use; per booking
>   a record with user and status.
> - Spec fixes check *order* for `book` (404, 400, 400, 409) and `move`
>   (404, 409, 400, 409) so that ambiguous-input tests are spec-derived, not
>   implementation-derived.
> - Error bodies are always None (stated in the spec).
> - T_v is deliberately nominal: it never asserts exact booking ids, never
>   books for "today", never books to exact capacity, never re-books a released
>   slot, and never tests duplicate rooms, ownership, double cancel, or list
>   ordering — so all 17 faults pass T_v. Each fault is caught by a named
>   deterministic T_h test (plus the stateful machine for several of them).
> 
> ## Fix history (validator rounds 1 and 2)
> 
> - `test_req8_move_conflict_leaves_unchanged` failed twice on the reference for
>   the same root cause: the test's scenario did not actually violate REQ-4.
>   In round 1 Bob's booking (12–14, seats 2) covers hours 12–13 only, so
>   moving Ann to 10–12 conflicted with nothing; in round 2 the same mistake
>   repeated. The reference's 200 was correct per REQ-8. The final test books
>   Bob on 11–13 (hours 11–12, seats 2), so moving Ann (9–11, seats 3) to
>   10–12 really does exceed capacity on hour 11 (3 + 2 > 4) and must return
>   409 per REQ-8; the follow-up bookings verify the capacity grid is
>   unchanged. The spec required no change.
> - Fault F03's original text had the wrong indentation (12 spaces instead of
>   8); it now matches the `_valid_time` line in reference.py character for
>   character and occurs exactly once.
> - After these fixes, each fault was re-checked: it still passes T_v and is
>   caught by a targeted deterministic test (F01 by test_req4_exact_fill_allowed,
>   F02 by test_req4_conflict_at_last_hour, F03 by test_req2_hours, F04/F05 by
>   test_req2_day_bounds, F06 by test_req7_double_cancel, F07 by
>   test_req6_cancel_other_users_booking, F08 by test_req8_move_self_overlap,
>   F09/F10 by test_req9_list_order / test_req9_list_excludes_cancelled, F11 by
>   test_req5_sequential_ids, F12 by test_req3_seats (409 instead of 400), F13
>   by test_req1_capacity_bounds, F14 by test_req1_duplicate_room, F15 by
>   test_req3_unknown_room, F16 by test_req7_cancel_releases_capacity, F17 by
>   test_req8_move_releases_old_slot).
> 
> ## Behaviours deliberately left open (not tested)
> 
> - Creating a duplicate room with *invalid* arguments: spec fixes validation
>   before existence, but the combination is not exercised.
> - `booking_id` arguments that are not integers (e.g. strings): the spec only
>   speaks of integers; any hashable lookup miss behaves as 404 and is untested.
> - What happens when `clock.today() > 365` (no bookable day remains).
> - User values: any value is accepted and compared with `==`; no validation,
>   no test of exotic user values.
> - `move` to the identical time (allowed, 200) is exercised by the stateful
>   machine but not asserted as a dedicated case.
> 
> ## Fault rationale (one sentence each)
> 
> - F01: classic off-by-one on a shared-limit comparison (`>` vs `>=`).
> - F02: interval-end fencepost, forgetting the interval is half-open.
> - F03: half-open interval confusion, allowing `start == end`.
> - F04: off-by-one on an inclusive upper bound.
> - F05: fencepost between "today allowed" and "future only".
> - F06: releasing resources but forgetting to flip the status flag.
> - F07: dropping the ownership check when refactoring a guard clause.
> - F08: forgetting to exclude the moved item from its own conflict check.
> - F09: key tuple built in the wrong order when sorting.
> - F10: filter predicate loses one condition during a rewrite.
> - F11: initializing a counter to 0 instead of 1.
> - F12: forgetting the upper bound on a per-room limit.
> - F13: the classic Python `bool`-is-`int` validation gap.
> - F14: 400 vs 409 confusion on a duplicate resource.
> - F15: 400 vs 404 confusion on a missing resource.
> - F16: release loop fencepost, symmetric to the booking fencepost.
> - F17: updating the record but forgetting to free the old slot.
> 
> ## Model identity
> 
> As far as I know, I am GLM, version glm-5-latest-short, served by Mistral AI
> infrastructure as the Vibe agent.

## Hidden tests (27)

### 1. `test_req1_invalid_names`

```python
def test_req1_invalid_names():
    svc = Service(Clock())
    for bad in ["", " ", " x", "x ", 5, None, True]:
        assert svc.create_room(bad, 5)[0] == 400, bad
```


### 2. `test_req1_capacity_bounds`

```python
def test_req1_capacity_bounds():
    svc = Service(Clock())
    for bad in [0, 51, -1, 2.5, "3", True, False, None]:
        assert svc.create_room("r", bad)[0] == 400, bad
    assert svc.create_room("r", 1) == (201, {"room": "r"})
    assert svc.create_room("big", 50)[0] == 201
```


### 3. `test_req1_duplicate_room`

```python
def test_req1_duplicate_room():
    svc = Service(Clock())
    assert svc.create_room("r", 5)[0] == 201
    assert svc.create_room("r", 7) == (409, None)
```


### 4. `test_req2_day_bounds`

```python
def test_req2_day_bounds():
    svc = Service(Clock(7))
    svc.create_room("r", 5)
    for bad in [-1, 366, 1000, 2.5, "5", True, None]:
        assert svc.book("ann", "r", bad, 1, 2, 1)[0] == 400, bad
    assert svc.book("ann", "r", 7, 1, 2, 1)[0] == 201       # today is allowed
    assert svc.book("ann", "r", 6, 1, 2, 1)[0] == 400       # before today
    svc2 = Service(Clock(0))
    svc2.create_room("r", 5)
    assert svc2.book("ann", "r", 365, 1, 2, 1)[0] == 201     # upper bound is inclusive
```


### 5. `test_req2_hours`

```python
def test_req2_hours():
    svc = Service(Clock())
    svc.create_room("r", 5)
    for day, start, end in [(5, 3, 3), (5, 4, 2), (5, -1, 2), (5, 1, 25), (5, 24, 25)]:
        assert svc.book("ann", "r", day, start, end, 1)[0] == 400, (start, end)
    for bad in ["1", 1.5, None, True]:
        assert svc.book("ann", "r", 5, bad, 2, 1)[0] == 400, bad
    assert svc.book("ann", "r", 5, 23, 24, 1)[0] == 201       # end 24 is allowed
    assert svc.book("ann", "r", 5, 0, 1, 1)[0] == 201        # start 0 is allowed
```


### 6. `test_req3_unknown_room`

```python
def test_req3_unknown_room():
    svc = Service(Clock())
    assert svc.book("ann", "nope", 5, 1, 2, 1) == (404, None)
```


### 7. `test_req3_seats`

```python
def test_req3_seats():
    svc = Service(Clock())
    svc.create_room("r", 3)
    for bad in [0, -1, 4, 10, 2.5, "2", None, True]:
        assert svc.book("ann", "r", 5, 1, 2, bad)[0] == 400, bad
    assert svc.book("ann", "r", 5, 1, 2, 3)[0] == 201        # seats == capacity
```


### 8. `test_req3_check_order`

```python
def test_req3_check_order():
    svc = Service(Clock(7))
    svc.create_room("r", 3)
    # unknown room wins over invalid time and invalid seats
    assert svc.book("ann", "nope", 0, 3, 3, 99)[0] == 404
    # invalid time wins over invalid seats
    assert svc.book("ann", "r", 0, 3, 3, 99)[0] == 400
    # invalid seats wins over capacity conflict
    assert svc.book("ann", "r", 8, 1, 2, 99)[0] == 400
```


### 9. `test_req4_exact_fill_allowed`

```python
def test_req4_exact_fill_allowed():
    svc = Service(Clock())
    svc.create_room("r", 4)
    assert svc.book("ann", "r", 5, 9, 11, 4)[0] == 201
    assert svc.book("ann", "r", 5, 11, 13, 4)[0] == 201      # back to back is fine
    assert svc.book("ann", "r", 6, 9, 11, 2)[0] == 201
    assert svc.book("ann", "r", 6, 10, 12, 2)[0] == 201      # 2 + 2 == 4 fits exactly
```


### 10. `test_req4_conflict_at_last_hour`

```python
def test_req4_conflict_at_last_hour():
    svc = Service(Clock())
    svc.create_room("r", 2)
    assert svc.book("ann", "r", 5, 9, 12, 2)[0] == 201
    assert svc.book("bob", "r", 5, 11, 12, 1)[0] == 409      # hour 11 is full
    assert svc.book("bob", "r", 5, 12, 13, 1)[0] == 201
```


### 11. `test_req4_conflict_changes_nothing`

```python
def test_req4_conflict_changes_nothing():
    svc = Service(Clock())
    svc.create_room("r", 2)
    assert svc.book("ann", "r", 5, 9, 11, 2)[0] == 201
    assert svc.book("bob", "r", 5, 10, 12, 1) == (409, None)
    assert svc.book("bob", "r", 5, 11, 12, 2)[0] == 201      # state was untouched
```


### 12. `test_req5_sequential_ids`

```python
def test_req5_sequential_ids():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b1 = svc.book("ann", "r", 5, 1, 2, 1)
    _, b2 = svc.book("bob", "r", 5, 2, 3, 1)
    assert b1["booking_id"] == 1
    assert b2["booking_id"] == 2
    svc.cancel("ann", 1)
    _, b3 = svc.book("ann", "r", 5, 3, 4, 1)
    assert b3["booking_id"] == 3                            # ids are never reused
```


### 13. `test_req5_record_shape`

```python
def test_req5_record_shape():
    svc = Service(Clock())
    svc.create_room("r", 5)
    assert svc.book("ann", "r", 5, 1, 3, 2) == (201, {"booking_id": 1, "room": "r",
                                                      "day": 5, "start": 1,
                                                      "end": 3, "seats": 2})
```


### 14. `test_req6_cancel_other_users_booking`

```python
def test_req6_cancel_other_users_booking():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 1, 2, 1)
    bid = b["booking_id"]
    assert svc.cancel("bob", bid) == (404, None)             # same as a missing id
    assert svc.cancel("bob", 999) == (404, None)
    assert svc.cancel("ann", bid) == (200, {"status": "cancelled"})
```


### 15. `test_req6_move_other_users_booking`

```python
def test_req6_move_other_users_booking():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 1, 2, 1)
    assert svc.move("bob", b["booking_id"], 6, 3, 4) == (404, None)
    assert svc.move("bob", 999, 6, 3, 4) == (404, None)
    assert len(svc.list_bookings("bob")[1]) == 0
```


### 16. `test_req7_double_cancel`

```python
def test_req7_double_cancel():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 1, 2, 1)
    assert svc.cancel("ann", b["booking_id"])[0] == 200
    assert svc.cancel("ann", b["booking_id"]) == (409, None)
```


### 17. `test_req7_cancel_releases_capacity`

```python
def test_req7_cancel_releases_capacity():
    svc = Service(Clock())
    svc.create_room("r", 4)
    _, b = svc.book("ann", "r", 5, 9, 11, 4)
    assert svc.cancel("ann", b["booking_id"])[0] == 200
    assert svc.book("bob", "r", 5, 10, 12, 1)[0] == 201     # last hour is free again
```


### 18. `test_req8_move_self_overlap`

```python
def test_req8_move_self_overlap():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 9, 11, 5)
    status, moved = svc.move("ann", b["booking_id"], 5, 10, 12)
    assert status == 200                                    # own seats do not block
    assert (moved["day"], moved["start"], moved["end"]) == (5, 10, 12)
    assert moved["room"] == "r" and moved["seats"] == 5
```


### 19. `test_req8_move_releases_old_slot`

```python
def test_req8_move_releases_old_slot():
    svc = Service(Clock())
    svc.create_room("r", 3)
    _, b = svc.book("ann", "r", 5, 9, 11, 3)
    assert svc.move("ann", b["booking_id"], 5, 12, 14)[0] == 200
    assert svc.book("bob", "r", 5, 9, 11, 3)[0] == 201      # old slot is free
```


### 20. `test_req8_move_conflict_leaves_unchanged`

```python
def test_req8_move_conflict_leaves_unchanged():
    svc = Service(Clock())
    svc.create_room("r", 4)
    _, b1 = svc.book("ann", "r", 5, 9, 11, 3)
    assert svc.book("bob", "r", 5, 11, 13, 2)[0] == 201
    # moving b1 to 10-12 would put 3 + 2 seats on hour 11 (capacity 4)
    assert svc.move("ann", b1["booking_id"], 5, 10, 12)[0] == 409
    _, listings = svc.list_bookings("ann")
    assert listings[0]["start"] == 9 and listings[0]["end"] == 11
    # the old slot still holds its seats ...
    assert svc.book("bob", "r", 5, 9, 10, 4)[0] == 409
    # ... and hour 12 only holds bob's seats at its old booking
    assert svc.book("bob", "r", 5, 12, 13, 2)[0] == 201
```


### 21. `test_req8_move_invalid_time`

```python
def test_req8_move_invalid_time():
    svc = Service(Clock(7))
    svc.create_room("r", 4)
    _, b = svc.book("ann", "r", 8, 9, 11, 2)
    assert svc.move("ann", b["booking_id"], 8, 5, 5)[0] == 400
    assert svc.move("ann", b["booking_id"], 6, 9, 10)[0] == 400   # before today
    assert svc.list_bookings("ann")[1][0]["start"] == 9
```


### 22. `test_req8_move_cancelled`

```python
def test_req8_move_cancelled():
    svc = Service(Clock())
    svc.create_room("r", 4)
    _, b = svc.book("ann", "r", 5, 9, 11, 2)
    svc.cancel("ann", b["booking_id"])
    assert svc.move("ann", b["booking_id"], 5, 12, 14) == (409, None)
```


### 23. `test_req9_list_order`

```python
def test_req9_list_order():
    svc = Service(Clock())
    svc.create_room("a", 5)
    svc.create_room("b", 5)
    _, first = svc.book("ann", "a", 30, 5, 6, 1)
    _, second = svc.book("ann", "b", 20, 8, 9, 1)
    _, listings = svc.list_bookings("ann")
    assert [(x["day"], x["start"]) for x in listings] == [(20, 8), (30, 5)]
    assert listings[0]["booking_id"] == second["booking_id"]
```


### 24. `test_req9_list_tie_break`

```python
def test_req9_list_tie_break():
    svc = Service(Clock())
    svc.create_room("a", 5)
    svc.create_room("b", 5)
    _, b1 = svc.book("ann", "a", 5, 4, 5, 1)
    _, b2 = svc.book("ann", "b", 5, 4, 5, 1)
    _, listings = svc.list_bookings("ann")
    assert [x["booking_id"] for x in listings] == [b1["booking_id"], b2["booking_id"]]
```


### 25. `test_req9_list_excludes_cancelled`

```python
def test_req9_list_excludes_cancelled():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 1, 2, 1)
    svc.cancel("ann", b["booking_id"])
    assert svc.list_bookings("ann") == (200, [])
    assert svc.list_bookings("nobody") == (200, [])
```


### 26. `test_req10_cancelled_occupies_nothing`

```python
def test_req10_cancelled_occupies_nothing():
    svc = Service(Clock())
    svc.create_room("r", 2)
    _, b1 = svc.book("ann", "r", 5, 9, 11, 2)
    assert svc.book("bob", "r", 5, 9, 11, 2)[0] == 409
    svc.cancel("ann", b1["booking_id"])
    assert svc.book("bob", "r", 5, 9, 11, 2)[0] == 201
```


### 27. `test_stateful_reservations`

```python
class Reservations(RuleBasedStateMachine):
    CAP = 6

    def __init__(self):
        super().__init__()
        self.svc = Service(Clock(0))
        assert self.svc.create_room("r", self.CAP)[0] == 201
        self.usage = {}     # (day, hour) -> seats in use
        self.recs = {}      # booking_id -> {"day", "start", "end", "seats"}
        self.dead = set()   # cancelled booking ids
        self.next_id = 1

    def _expected_list(self):
        active = [i for i in self.recs if i not in self.dead]
        active.sort(key=lambda i: (self.recs[i]["day"], self.recs[i]["start"], i))
        return [{"booking_id": i, "room": "r", "day": self.recs[i]["day"],
                 "start": self.recs[i]["start"], "end": self.recs[i]["end"],
                 "seats": self.recs[i]["seats"]} for i in active]

    @invariant()
    def list_matches_model(self):
        assert self.svc.list_bookings("ann") == (200, self._expected_list())

    @rule(day=st.sampled_from([5, 6]), start=st.integers(0, 21),
          length=st.integers(1, 3), seats=st.integers(1, 6))
    def book(self, day, start, length, seats):
        end = start + length
        status, body = self.svc.book("ann", "r", day, start, end, seats)
        conflict = any(self.usage.get((day, h), 0) + seats > self.CAP
                       for h in range(start, end))
        if conflict:
            assert status == 409
        else:
            assert status == 201
            assert body["booking_id"] == self.next_id
            self.next_id += 1
            for h in range(start, end):
                self.usage[(day, h)] = self.usage.get((day, h), 0) + seats
            self.recs[body["booking_id"]] = {"day": day, "start": start,
                                             "end": end, "seats": seats}

    @rule(bid=st.integers(1, 20))
    def cancel(self, bid):
        status, body = self.svc.cancel("ann", bid)
        r = self.recs.get(bid)
        if r is None:
            assert status == 404
        elif bid in self.dead:
            assert status == 409
        else:
            assert status == 200 and body == {"status": "cancelled"}
            for h in range(r["start"], r["end"]):
                self.usage[(r["day"], h)] -= r["seats"]
            self.dead.add(bid)

    @rule(bid=st.integers(1, 20), day=st.sampled_from([5, 6]),
          start=st.integers(0, 21), length=st.integers(1, 3))
    def move(self, bid, day, start, length):
        end = start + length
        r = self.recs.get(bid)
        status, body = self.svc.move("ann", bid, day, start, end)
        if r is None:
            assert status == 404
        elif bid in self.dead:
            assert status == 409
        else:
            conflict = False
            for h in range(start, end):
                used = self.usage.get((day, h), 0)
                if r["day"] == day and r["start"] <= h < r["end"]:
                    used -= r["seats"]
                if used + r["seats"] > self.CAP:
                    conflict = True
            if conflict:
                assert status == 409
            else:
                assert status == 200
                for h in range(r["start"], r["end"]):
                    self.usage[(r["day"], h)] -= r["seats"]
                for h in range(start, end):
                    self.usage[(day, h)] = self.usage.get((day, h), 0) + r["seats"]
                r["day"], r["start"], r["end"] = day, start, end


def test_stateful_reservations():
    run_state_machine_as_test(Reservations, settings=settings(
        max_examples=40, stateful_step_count=25, deadline=None,
        database=None, derandomize=True))
```

