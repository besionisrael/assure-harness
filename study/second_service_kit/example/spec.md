# Counter service (toy example of the format)

<!-- Author notes may go in comments like this one; agents never see them. -->

## Interface

The service is a Python module `solution.py` that defines a class `Service`.
Every method returns a pair `(status, body)`.

    class Service:
        def __init__(self, clock): ...
        def create_counter(self, user, name, limit): ...   # 201 {"name": str} | 400 | 409
        def increment(self, user, name): ...               # 200 {"value": int} | 404 | 429
        def read(self, user, name): ...                    # 200 {"value": int, "created_at": float} | 404

`clock` has a method `now()` returning the current time in seconds.

## Requirements

**REQ-1 Creation.** `create_counter` creates a counter with value 0 for the
given user. `limit` is an integer from 1 to 1000; otherwise 400. A user who
already has a counter with that name gets 409. `created_at` is `clock.now()`
at creation.

**REQ-2 Increment.** `increment` adds 1 to the counter and returns the new
value. A counter never exceeds its limit: when the value equals the limit,
`increment` returns 429 and the value does not change.

**REQ-3 Ownership.** Counters are private: a user cannot increment or read
another user's counter, and gets 404 exactly as for a missing counter. Two
users may have counters with the same name.
