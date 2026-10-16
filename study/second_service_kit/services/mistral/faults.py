"""Seeded faults. Format:

  FAULTS = {fault_id: (requirement, short description, original text, replacement text)}

The original text must occur exactly once in reference.py; the faulty program is
reference.py with that text replaced. Keep the two helper functions below.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent

FAULTS = {
    "F01": ("REQ-4", "off-by-one: filling a room exactly to capacity is rejected",
            '''            if used + seats > self._rooms[room]:''',
            '''            if used + seats >= self._rooms[room]:'''),

    "F02": ("REQ-4", "capacity is checked on all hours except the last one",
            '''        booked = self._grid.setdefault((room, day), [0] * 24)
        for h in range(start, end):''',
            '''        booked = self._grid.setdefault((room, day), [0] * 24)
        for h in range(start, end - 1):'''),

    "F03": ("REQ-2", "zero-length intervals (start == end) are accepted",
            '''        if not (_is_int(start) and _is_int(end) and 0 <= start < end <= 24):''',
            '''        if not (_is_int(start) and _is_int(end) and 0 <= start <= end <= 24):'''),

    "F04": ("REQ-2", "day 365 is wrongly rejected (off-by-one on the upper bound)",
            '''        if not (_is_int(day) and 0 <= day <= 365):''',
            '''        if not (_is_int(day) and 0 <= day < 365):'''),

    "F05": ("REQ-2", "fencepost: booking for today is rejected",
            '''        if day < self.clock.today():''',
            '''        if day <= self.clock.today():'''),

    "F06": ("REQ-7", "cancel never marks the booking as cancelled",
            '''        b["status"] = "cancelled"''',
            '''        pass'''),

    "F07": ("REQ-6", "cancel ignores the user, so anyone can cancel any booking",
            '''    def cancel(self, user, booking_id):
        b = self._bookings.get(booking_id)
        if b is None or b["user"] != user:
            return 404, None''',
            '''    def cancel(self, user, booking_id):
        b = self._bookings.get(booking_id)
        if b is None:
            return 404, None'''),

    "F08": ("REQ-8", "move counts the booking's own current seats against itself",
            '''        if not self._fits(b["room"], new_day, new_start, new_end, b["seats"], exclude_id=booking_id):''',
            '''        if not self._fits(b["room"], new_day, new_start, new_end, b["seats"], exclude_id=None):'''),

    "F09": ("REQ-9", "list is sorted by start hour before day",
            '''        recs.sort(key=lambda b: (b["day"], b["start"], b["booking_id"]))''',
            '''        recs.sort(key=lambda b: (b["start"], b["day"], b["booking_id"]))'''),

    "F10": ("REQ-9", "list includes cancelled bookings",
            '''                if b["user"] == user and b["status"] == "active"]''',
            '''                if b["user"] == user]'''),

    "F11": ("REQ-5", "booking ids start at 0 instead of 1",
            '''        self._next_id = 1''',
            '''        self._next_id = 0'''),

    "F12": ("REQ-3", "seats larger than the room capacity is not rejected as 400",
            '''        if not (_is_int(seats) and 1 <= seats <= self._rooms[room]):''',
            '''        if not (_is_int(seats) and 1 <= seats):'''),

    "F13": ("REQ-1", "bools are accepted where integers are required",
            '''    return isinstance(x, int) and not isinstance(x, bool)''',
            '''    return isinstance(x, int)'''),

    "F14": ("REQ-1", "duplicate room returns 400 instead of 409",
            '''        if room in self._rooms:
            return 409, None''',
            '''        if room in self._rooms:
            return 400, None'''),

    "F15": ("REQ-3", "booking an unknown room returns 400 instead of 404",
            '''        if room not in self._rooms:
            return 404, None''',
            '''        if room not in self._rooms:
            return 400, None'''),

    "F16": ("REQ-7", "cancel forgets to release the last hour of the interval",
            '''        booked = self._grid[(b["room"], b["day"])]
        for h in range(b["start"], b["end"]):
            booked[h] -= b["seats"]''',
            '''        booked = self._grid[(b["room"], b["day"])]
        for h in range(b["start"], b["end"] - 1):
            booked[h] -= b["seats"]'''),

    "F17": ("REQ-8", "move never releases the old time slot",
            '''        old = self._grid[(b["room"], b["day"])]
        for h in range(b["start"], b["end"]):
            old[h] -= b["seats"]''',
            '''        old = self._grid[(b["room"], b["day"])]'''),
}


def reference():
    return (HERE / "reference.py").read_text(encoding="utf-8")


def variant(fault_id):
    _, _, old, new = FAULTS[fault_id]
    src = reference()
    if src.count(old) != 1:
        raise ValueError(f"{fault_id}: original text occurs {src.count(old)} times")
    return src.replace(old, new)
