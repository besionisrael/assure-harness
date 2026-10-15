"""Visible tests T_v (shown to agents): nominal cases only."""
from solution import Service


class Clock:
    def __init__(self, today=10):
        self._today = today

    def today(self):
        return self._today


def test_create_room_and_book():
    svc = Service(Clock())
    assert svc.create_room("alpha", 10) == (201, {"room": "alpha"})
    status, body = svc.book("ann", "alpha", 20, 9, 11, 4)
    assert status == 201
    assert body["room"] == "alpha"
    assert body["day"] == 20 and body["start"] == 9 and body["end"] == 11
    assert body["seats"] == 4


def test_list_bookings():
    svc = Service(Clock())
    svc.create_room("alpha", 10)
    status, body = svc.book("ann", "alpha", 20, 9, 11, 4)
    status, listings = svc.list_bookings("ann")
    assert status == 200
    assert len(listings) == 1
    assert listings[0]["booking_id"] == body["booking_id"]
    assert listings[0]["room"] == "alpha"


def test_capacity_conflict():
    svc = Service(Clock())
    svc.create_room("beta", 4)
    assert svc.book("ann", "beta", 20, 9, 11, 3)[0] == 201
    assert svc.book("ann", "beta", 20, 10, 12, 3)[0] == 409


def test_move():
    svc = Service(Clock())
    svc.create_room("gamma", 5)
    _, body = svc.book("ann", "gamma", 20, 9, 11, 2)
    bid = body["booking_id"]
    status, moved = svc.move("ann", bid, 21, 12, 14)
    assert status == 200
    assert moved["day"] == 21 and moved["start"] == 12 and moved["end"] == 14
    _, listings = svc.list_bookings("ann")
    assert listings[0]["day"] == 21 and listings[0]["start"] == 12


def test_cancel():
    svc = Service(Clock())
    svc.create_room("alpha", 10)
    _, body = svc.book("ann", "alpha", 20, 9, 11, 4)
    assert svc.cancel("ann", body["booking_id"]) == (200, {"status": "cancelled"})


def test_two_users():
    svc = Service(Clock())
    svc.create_room("beta", 4)
    assert svc.book("ann", "beta", 20, 9, 11, 2)[0] == 201
    assert svc.book("bob", "beta", 20, 11, 13, 2)[0] == 201
    assert len(svc.list_bookings("ann")[1]) == 1
    assert len(svc.list_bookings("bob")[1]) == 1
