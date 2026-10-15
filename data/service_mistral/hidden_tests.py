"""Hidden suite T_h. Every assertion follows from a sentence of spec.md."""
from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, run_state_machine_as_test

from solution import Service


class Clock:
    def __init__(self, today=0):
        self._today = today

    def today(self):
        return self._today


# ---- REQ-1 ----

def test_req1_invalid_names():
    svc = Service(Clock())
    for bad in ["", " ", " x", "x ", 5, None, True]:
        assert svc.create_room(bad, 5)[0] == 400, bad


def test_req1_capacity_bounds():
    svc = Service(Clock())
    for bad in [0, 51, -1, 2.5, "3", True, False, None]:
        assert svc.create_room("r", bad)[0] == 400, bad
    assert svc.create_room("r", 1) == (201, {"room": "r"})
    assert svc.create_room("big", 50)[0] == 201


def test_req1_duplicate_room():
    svc = Service(Clock())
    assert svc.create_room("r", 5)[0] == 201
    assert svc.create_room("r", 7) == (409, None)


# ---- REQ-2 ----

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


def test_req2_hours():
    svc = Service(Clock())
    svc.create_room("r", 5)
    for day, start, end in [(5, 3, 3), (5, 4, 2), (5, -1, 2), (5, 1, 25), (5, 24, 25)]:
        assert svc.book("ann", "r", day, start, end, 1)[0] == 400, (start, end)
    for bad in ["1", 1.5, None, True]:
        assert svc.book("ann", "r", 5, bad, 2, 1)[0] == 400, bad
    assert svc.book("ann", "r", 5, 23, 24, 1)[0] == 201       # end 24 is allowed
    assert svc.book("ann", "r", 5, 0, 1, 1)[0] == 201        # start 0 is allowed


# ---- REQ-3 ----

def test_req3_unknown_room():
    svc = Service(Clock())
    assert svc.book("ann", "nope", 5, 1, 2, 1) == (404, None)


def test_req3_seats():
    svc = Service(Clock())
    svc.create_room("r", 3)
    for bad in [0, -1, 4, 10, 2.5, "2", None, True]:
        assert svc.book("ann", "r", 5, 1, 2, bad)[0] == 400, bad
    assert svc.book("ann", "r", 5, 1, 2, 3)[0] == 201        # seats == capacity


def test_req3_check_order():
    svc = Service(Clock(7))
    svc.create_room("r", 3)
    # unknown room wins over invalid time and invalid seats
    assert svc.book("ann", "nope", 0, 3, 3, 99)[0] == 404
    # invalid time wins over invalid seats
    assert svc.book("ann", "r", 0, 3, 3, 99)[0] == 400
    # invalid seats wins over capacity conflict
    assert svc.book("ann", "r", 8, 1, 2, 99)[0] == 400


# ---- REQ-4 ----

def test_req4_exact_fill_allowed():
    svc = Service(Clock())
    svc.create_room("r", 4)
    assert svc.book("ann", "r", 5, 9, 11, 4)[0] == 201
    assert svc.book("ann", "r", 5, 11, 13, 4)[0] == 201      # back to back is fine
    assert svc.book("ann", "r", 6, 9, 11, 2)[0] == 201
    assert svc.book("ann", "r", 6, 10, 12, 2)[0] == 201      # 2 + 2 == 4 fits exactly


def test_req4_conflict_at_last_hour():
    svc = Service(Clock())
    svc.create_room("r", 2)
    assert svc.book("ann", "r", 5, 9, 12, 2)[0] == 201
    assert svc.book("bob", "r", 5, 11, 12, 1)[0] == 409      # hour 11 is full
    assert svc.book("bob", "r", 5, 12, 13, 1)[0] == 201


def test_req4_conflict_changes_nothing():
    svc = Service(Clock())
    svc.create_room("r", 2)
    assert svc.book("ann", "r", 5, 9, 11, 2)[0] == 201
    assert svc.book("bob", "r", 5, 10, 12, 1) == (409, None)
    assert svc.book("bob", "r", 5, 11, 12, 2)[0] == 201      # state was untouched


# ---- REQ-5 ----

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


def test_req5_record_shape():
    svc = Service(Clock())
    svc.create_room("r", 5)
    assert svc.book("ann", "r", 5, 1, 3, 2) == (201, {"booking_id": 1, "room": "r",
                                                      "day": 5, "start": 1,
                                                      "end": 3, "seats": 2})


# ---- REQ-6 / REQ-7 ----

def test_req6_cancel_other_users_booking():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 1, 2, 1)
    bid = b["booking_id"]
    assert svc.cancel("bob", bid) == (404, None)             # same as a missing id
    assert svc.cancel("bob", 999) == (404, None)
    assert svc.cancel("ann", bid) == (200, {"status": "cancelled"})


def test_req6_move_other_users_booking():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 1, 2, 1)
    assert svc.move("bob", b["booking_id"], 6, 3, 4) == (404, None)
    assert svc.move("bob", 999, 6, 3, 4) == (404, None)
    assert len(svc.list_bookings("bob")[1]) == 0


def test_req7_double_cancel():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 1, 2, 1)
    assert svc.cancel("ann", b["booking_id"])[0] == 200
    assert svc.cancel("ann", b["booking_id"]) == (409, None)


def test_req7_cancel_releases_capacity():
    svc = Service(Clock())
    svc.create_room("r", 4)
    _, b = svc.book("ann", "r", 5, 9, 11, 4)
    assert svc.cancel("ann", b["booking_id"])[0] == 200
    assert svc.book("bob", "r", 5, 10, 12, 1)[0] == 201     # last hour is free again


# ---- REQ-8 ----

def test_req8_move_self_overlap():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 9, 11, 5)
    status, moved = svc.move("ann", b["booking_id"], 5, 10, 12)
    assert status == 200                                    # own seats do not block
    assert (moved["day"], moved["start"], moved["end"]) == (5, 10, 12)
    assert moved["room"] == "r" and moved["seats"] == 5


def test_req8_move_releases_old_slot():
    svc = Service(Clock())
    svc.create_room("r", 3)
    _, b = svc.book("ann", "r", 5, 9, 11, 3)
    assert svc.move("ann", b["booking_id"], 5, 12, 14)[0] == 200
    assert svc.book("bob", "r", 5, 9, 11, 3)[0] == 201      # old slot is free


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


def test_req8_move_invalid_time():
    svc = Service(Clock(7))
    svc.create_room("r", 4)
    _, b = svc.book("ann", "r", 8, 9, 11, 2)
    assert svc.move("ann", b["booking_id"], 8, 5, 5)[0] == 400
    assert svc.move("ann", b["booking_id"], 6, 9, 10)[0] == 400   # before today
    assert svc.list_bookings("ann")[1][0]["start"] == 9


def test_req8_move_cancelled():
    svc = Service(Clock())
    svc.create_room("r", 4)
    _, b = svc.book("ann", "r", 5, 9, 11, 2)
    svc.cancel("ann", b["booking_id"])
    assert svc.move("ann", b["booking_id"], 5, 12, 14) == (409, None)


# ---- REQ-9 / REQ-10 ----

def test_req9_list_order():
    svc = Service(Clock())
    svc.create_room("a", 5)
    svc.create_room("b", 5)
    _, first = svc.book("ann", "a", 30, 5, 6, 1)
    _, second = svc.book("ann", "b", 20, 8, 9, 1)
    _, listings = svc.list_bookings("ann")
    assert [(x["day"], x["start"]) for x in listings] == [(20, 8), (30, 5)]
    assert listings[0]["booking_id"] == second["booking_id"]


def test_req9_list_tie_break():
    svc = Service(Clock())
    svc.create_room("a", 5)
    svc.create_room("b", 5)
    _, b1 = svc.book("ann", "a", 5, 4, 5, 1)
    _, b2 = svc.book("ann", "b", 5, 4, 5, 1)
    _, listings = svc.list_bookings("ann")
    assert [x["booking_id"] for x in listings] == [b1["booking_id"], b2["booking_id"]]


def test_req9_list_excludes_cancelled():
    svc = Service(Clock())
    svc.create_room("r", 5)
    _, b = svc.book("ann", "r", 5, 1, 2, 1)
    svc.cancel("ann", b["booking_id"])
    assert svc.list_bookings("ann") == (200, [])
    assert svc.list_bookings("nobody") == (200, [])


def test_req10_cancelled_occupies_nothing():
    svc = Service(Clock())
    svc.create_room("r", 2)
    _, b1 = svc.book("ann", "r", 5, 9, 11, 2)
    assert svc.book("bob", "r", 5, 9, 11, 2)[0] == 409
    svc.cancel("ann", b1["booking_id"])
    assert svc.book("bob", "r", 5, 9, 11, 2)[0] == 201


# ---- Model-based stateful test of REQ-2, REQ-4, REQ-5, REQ-7, REQ-8, REQ-9, REQ-10 ----

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
