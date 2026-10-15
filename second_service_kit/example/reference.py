"""Reference implementation of the toy counter service."""


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


class Service:
    def __init__(self, clock):
        self.clock = clock
        self._counters = {}      # (user, name) -> {"value", "limit", "created_at"}

    def create_counter(self, user, name, limit):
        if not (_is_int(limit) and 1 <= limit <= 1000):
            return 400, None
        if (user, name) in self._counters:
            return 409, None
        self._counters[(user, name)] = {"value": 0, "limit": limit,
                                        "created_at": self.clock.now()}
        return 201, {"name": name}

    def increment(self, user, name):
        c = self._counters.get((user, name))
        if c is None:
            return 404, None
        if c["value"] >= c["limit"]:
            return 429, None
        c["value"] += 1
        return 200, {"value": c["value"]}

    def read(self, user, name):
        c = self._counters.get((user, name))
        if c is None:
            return 404, None
        return 200, {"value": c["value"], "created_at": c["created_at"]}
