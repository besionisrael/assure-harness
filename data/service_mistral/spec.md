# Room reservation service

A service that manages meeting rooms. Users book seats in a room for a time
interval on a given day. A room's capacity is shared by all overlapping
bookings. Users can cancel or move their bookings and list them.

The service is stateful and in-process. It never reads the system clock and
never uses randomness: all time information comes from the injected clock.

## Interface

The service is a Python module `solution.py` that defines a class `Service`.
The constructor takes one argument, a clock object with a method `today()`
that returns the current day number as an integer.

Every public method returns a pair `(status, body)`. `status` is an HTTP-style
integer. `body` is a dict, a list, or None. The body is None for every status
that is not 2xx.

A booking record is a dict with exactly these keys:

    {"booking_id": int, "room": str, "day": int, "start": int, "end": int, "seats": int}

    class Service:
        def __init__(self, clock): ...
        def create_room(self, room, capacity): ...
            # 201 {"room": str} | 400 None | 409 None
        def book(self, user, room, day, start, end, seats): ...
            # 201 booking record | 404 None | 400 None | 409 None
        def cancel(self, user, booking_id): ...
            # 200 {"status": "cancelled"} | 404 None | 409 None
        def move(self, user, booking_id, new_day, new_start, new_end): ...
            # 200 booking record | 404 None | 400 None | 409 None
        def list_bookings(self, user): ...
            # 200 list of booking records

## Requirements

**REQ-1 Room creation.** `create_room(room, capacity)` registers a room.
`room` must be a string that is non-empty and has no leading or trailing
whitespace; `capacity` must be an integer with 1 <= capacity <= 50. If either
is invalid the method returns 400. A bool is not an integer anywhere in this
specification. If a room with the same name already exists it returns 409.
Validation (400) is checked before existence (409). On success it returns
201 with body {"room": room}.

**REQ-2 Time validity.** A time is a triple (day, start, end) where day,
start and end are integers (bools rejected) with 0 <= day <= 365,
day >= clock.today(), 0 <= start < end <= 24. The interval occupied by a
booking is [start, end) in whole hours. Any method given an invalid time
returns 400 and changes nothing.

**REQ-3 Booking.** `book(user, room, day, start, end, seats)` checks, in this
order: the room must exist, else 404; the time must be valid (REQ-2), else
400; `seats` must be an integer with 1 <= seats <= the room's capacity,
else 400; the capacity constraint (REQ-4) must hold, else 409.

**REQ-4 Capacity.** For every hour h in [start, end), the sum of the seats of
all active bookings in that room, on that day, covering hour h, must not
exceed the room's capacity. A booking request that would violate this for at
least one hour returns 409 and changes nothing.

**REQ-5 Identifiers.** Every successful booking receives a `booking_id`:
integers starting at 1, increasing by 1 for each new booking, unique across
all bookings ever made, never reused. On success `book` returns 201 with the
booking record.

**REQ-6 Ownership.** A booking belongs to the user who created it. For
`cancel`, `move` and `list_bookings`, a booking id that does not exist and a
booking id owned by another user are both handled exactly as a missing
booking: 404 for `cancel` and `move`. `list_bookings(user)` returns only that
user's bookings.

**REQ-7 Cancellation.** `cancel(user, booking_id)` on an active booking owned
by the user returns 200 with body {"status": "cancelled"}; the booking becomes
cancelled and its seats stop counting for REQ-4. Cancelling a booking that is
already cancelled returns 409.

**REQ-8 Move.** `move(user, booking_id, new_day, new_start, new_end)` moves
the booking to a new time in the same room with the same seats; it cannot
change the room or the seat count. Checks in this order: the booking must
exist and belong to the user (REQ-6), else 404; it must be active, else 409;
the new time must be valid (REQ-2), else 400; the capacity constraint
(REQ-4) must hold for the new time, else 409. For the capacity check the
booking's own current seats do not count as usage at hours it currently
occupies. On success it returns 200 with the booking record updated to the
new day, start and end. On any failure the booking and all capacity state are
unchanged.

**REQ-9 Listing.** `list_bookings(user)` returns 200 and a list of the
user's active bookings, each a booking record with exactly the keys of REQ-5,
sorted by (day, start, booking_id) ascending. A user with no active bookings
gets an empty list.

**REQ-10 Cancelled bookings.** A cancelled booking keeps its identifier, does
not occupy any capacity, does not appear in listings, and can be neither
cancelled again (REQ-7) nor moved (REQ-8).
