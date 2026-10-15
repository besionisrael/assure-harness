"""Seeded faults of the toy example. Format required by validate.py:

  FAULTS = {fault_id: (requirement, short description, original text, replacement text)}

The original text must occur exactly once in reference.py; the faulty program is
reference.py with that text replaced. Keep the two helper functions below."""
from pathlib import Path

HERE = Path(__file__).resolve().parent

FAULTS = {
    "F01": ("REQ-2", "off-by-one: the counter can reach limit + 1",
            '''        if c["value"] >= c["limit"]:''',
            '''        if c["value"] > c["limit"]:'''),

    "F02": ("REQ-3", "read looks counters up by name only, ignoring the user",
            '''    def read(self, user, name):
        c = self._counters.get((user, name))''',
            '''    def read(self, user, name):
        c = next((v for (u, n), v in self._counters.items() if n == name), None)'''),
}


def reference():
    return (HERE / "reference.py").read_text(encoding="utf-8")


def variant(fault_id):
    _, _, old, new = FAULTS[fault_id]
    src = reference()
    if src.count(old) != 1:
        raise ValueError(f"{fault_id}: original text occurs {src.count(old)} times")
    return src.replace(old, new)
