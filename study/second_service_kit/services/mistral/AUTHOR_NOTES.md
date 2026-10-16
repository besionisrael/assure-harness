# Author notes — room reservation service

## Design choices

- Domain: shared-capacity room reservations. Capacity is a *shared* resource
  (overlapping bookings allowed until the seat sum exceeds capacity), which
  gives richer state than pure exclusive booking and realistic conflicts.
- The clock is injected and only used via `clock.today()`; nothing else in the
  service is time- or randomness-dependent, so all tests are deterministic.
- Internal model: per (room, day) a 24-slot array of seats in use; per booking
  a record with user and status.
- Spec fixes check *order* for `book` (404, 400, 400, 409) and `move`
  (404, 409, 400, 409) so that ambiguous-input tests are spec-derived, not
  implementation-derived.
- Error bodies are always None (stated in the spec).
- T_v is deliberately nominal: it never asserts exact booking ids, never
  books for "today", never books to exact capacity, never re-books a released
  slot, and never tests duplicate rooms, ownership, double cancel, or list
  ordering — so all 17 faults pass T_v. Each fault is caught by a named
  deterministic T_h test (plus the stateful machine for several of them).

## Fix history (validator rounds 1 and 2)

- `test_req8_move_conflict_leaves_unchanged` failed twice on the reference for
  the same root cause: the test's scenario did not actually violate REQ-4.
  In round 1 Bob's booking (12–14, seats 2) covers hours 12–13 only, so
  moving Ann to 10–12 conflicted with nothing; in round 2 the same mistake
  repeated. The reference's 200 was correct per REQ-8. The final test books
  Bob on 11–13 (hours 11–12, seats 2), so moving Ann (9–11, seats 3) to
  10–12 really does exceed capacity on hour 11 (3 + 2 > 4) and must return
  409 per REQ-8; the follow-up bookings verify the capacity grid is
  unchanged. The spec required no change.
- Fault F03's original text had the wrong indentation (12 spaces instead of
  8); it now matches the `_valid_time` line in reference.py character for
  character and occurs exactly once.
- After these fixes, each fault was re-checked: it still passes T_v and is
  caught by a targeted deterministic test (F01 by test_req4_exact_fill_allowed,
  F02 by test_req4_conflict_at_last_hour, F03 by test_req2_hours, F04/F05 by
  test_req2_day_bounds, F06 by test_req7_double_cancel, F07 by
  test_req6_cancel_other_users_booking, F08 by test_req8_move_self_overlap,
  F09/F10 by test_req9_list_order / test_req9_list_excludes_cancelled, F11 by
  test_req5_sequential_ids, F12 by test_req3_seats (409 instead of 400), F13
  by test_req1_capacity_bounds, F14 by test_req1_duplicate_room, F15 by
  test_req3_unknown_room, F16 by test_req7_cancel_releases_capacity, F17 by
  test_req8_move_releases_old_slot).

## Behaviours deliberately left open (not tested)

- Creating a duplicate room with *invalid* arguments: spec fixes validation
  before existence, but the combination is not exercised.
- `booking_id` arguments that are not integers (e.g. strings): the spec only
  speaks of integers; any hashable lookup miss behaves as 404 and is untested.
- What happens when `clock.today() > 365` (no bookable day remains).
- User values: any value is accepted and compared with `==`; no validation,
  no test of exotic user values.
- `move` to the identical time (allowed, 200) is exercised by the stateful
  machine but not asserted as a dedicated case.

## Fault rationale (one sentence each)

- F01: classic off-by-one on a shared-limit comparison (`>` vs `>=`).
- F02: interval-end fencepost, forgetting the interval is half-open.
- F03: half-open interval confusion, allowing `start == end`.
- F04: off-by-one on an inclusive upper bound.
- F05: fencepost between "today allowed" and "future only".
- F06: releasing resources but forgetting to flip the status flag.
- F07: dropping the ownership check when refactoring a guard clause.
- F08: forgetting to exclude the moved item from its own conflict check.
- F09: key tuple built in the wrong order when sorting.
- F10: filter predicate loses one condition during a rewrite.
- F11: initializing a counter to 0 instead of 1.
- F12: forgetting the upper bound on a per-room limit.
- F13: the classic Python `bool`-is-`int` validation gap.
- F14: 400 vs 409 confusion on a duplicate resource.
- F15: 400 vs 404 confusion on a missing resource.
- F16: release loop fencepost, symmetric to the booking fencepost.
- F17: updating the record but forgetting to free the old slot.

## Model identity

As far as I know, I am GLM, version glm-5-latest-short, served by Mistral AI
infrastructure as the Vibe agent.
