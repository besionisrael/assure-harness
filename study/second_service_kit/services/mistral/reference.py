"""Reference implementation of the room reservation service."""


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


class Service:
    def __init__(self, clock):
        self.clock = clock
        self._rooms = {}       # room -> capacity
        self._bookings = {}    # booking_id -> record
        self._grid = {}        # (room, day) -> list of 24 seat counts
        self._next_id = 1

    def create_room(self, room, capacity):
        if not (isinstance(room, str) and room != "" and room.strip() == room):
            return 400, None
        if not (_is_int(capacity) and 1 <= capacity <= 50):
            return 400, None
        if room in self._rooms:
            return 409, None
        self._rooms[room] = capacity
        return 201, {"room": room}

    def _valid_time(self, day, start, end):
        if not (_is_int(day) and 0 <= day <= 365):
            return False
        if day < self.clock.today():
            return False
        if not (_is_int(start) and _is_int(end) and 0 <= start < end <= 24):
            return False
        return True

    def _fits(self, room, day, start, end, seats, exclude_id=None):
        booked = self._grid.setdefault((room, day), [0] * 24)
        for h in range(start, end):
            used = booked[h]
            if exclude_id is not None:
                own = self._bookings[exclude_id]
                if own["room"] == room and own["day"] == day and own["start"] <= h < own["end"]:
                    used -= own["seats"]
            if used + seats > self._rooms[room]:
                return False
        return True

    def book(self, user, room, day, start, end, seats):
        if room not in self._rooms:
            return 404, None
        if not self._valid_time(day, start, end):
            return 400, None
        if not (_is_int(seats) and 1 <= seats <= self._rooms[room]):
            return 400, None
        if not self._fits(room, day, start, end, seats):
            return 409, None
        grid = self._grid.setdefault((room, day), [0] * 24)
        for h in range(start, end):
            grid[h] += seats
        booking_id = self._next_id
        self._next_id += 1
        rec = {"booking_id": booking_id, "room": room, "day": day,
               "start": start, "end": end, "seats": seats,
               "user": user, "status": "active"}
        self._bookings[booking_id] = rec
        return 201, {"booking_id": booking_id, "room": room, "day": day,
                     "start": start, "end": end, "seats": seats}

    def cancel(self, user, booking_id):
        b = self._bookings.get(booking_id)
        if b is None or b["user"] != user:
            return 404, None
        if b["status"] != "active":
            return 409, None
        booked = self._grid[(b["room"], b["day"])]
        for h in range(b["start"], b["end"]):
            booked[h] -= b["seats"]
        b["status"] = "cancelled"
        return 200, {"status": "cancelled"}

    def move(self, user, booking_id, new_day, new_start, new_end):
        b = self._bookings.get(booking_id)
        if b is None or b["user"] != user:
            return 404, None
        if b["status"] != "active":
            return 409, None
        if not self._valid_time(new_day, new_start, new_end):
            return 400, None
        if not self._fits(b["room"], new_day, new_start, new_end, b["seats"], exclude_id=booking_id):
            return 409, None
        old = self._grid[(b["room"], b["day"])]
        for h in range(b["start"], b["end"]):
            old[h] -= b["seats"]
        new = self._grid.setdefault((b["room"], new_day), [0] * 24)
        for h in range(new_start, new_end):
            new[h] += b["seats"]
        b["day"], b["start"], b["end"] = new_day, new_start, new_end
        return 200, {"booking_id": booking_id, "room": b["room"], "day": new_day,
                     "start": new_start, "end": new_end, "seats": b["seats"]}

    def list_bookings(self, user):
        recs = [b for b in self._bookings.values()
                if b["user"] == user and b["status"] == "active"]
        recs.sort(key=lambda b: (b["day"], b["start"], b["booking_id"]))
        return 200, [{"booking_id": b["booking_id"], "room": b["room"],
                      "day": b["day"], "start": b["start"], "end": b["end"],
                      "seats": b["seats"]} for b in recs]
