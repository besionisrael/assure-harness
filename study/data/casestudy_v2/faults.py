"""Seeded faults of the case study, version 2 (F01-F10 as in v1, F11-F14 from DESIGN.md). Never shown to any agent.

Each fault is one local edit of reference.py: `old` must occur exactly once."""
from pathlib import Path

HERE = Path(__file__).resolve().parent

_SEARCH = '''        hits = [d for d in self._visible(user)
                if q in d["title"].lower() or q in d["content"].lower()]'''

FAULTS = {
    "F01": ("REQ-17", "search_documents does not filter by owner", _SEARCH,
            '''        live = sorted((d for d in self._docs.values() if d["id"] not in self._deleted),
                      key=lambda d: d["_seq"])
        hits = [d for d in live
                if q in d["title"].lower() or q in d["content"].lower()]'''),

    "F02": ("REQ-17", "list cursor not bound to the caller",
            '''            if issued is None or issued[0] != user:
                return 400, None
            after = issued[1]''',
            '''            if issued is None:
                return 400, None
            user, after = issued'''),

    "F03": ("REQ-17", "403 instead of 404 for another user's document",
            '''    def get_document(self, token, doc_id):
        user = self._auth(token)
        if user is None:
            return 401, None
        doc = self._own(user, doc_id)
        if doc is None:
            return 404, None''',
            '''    def get_document(self, token, doc_id):
        user = self._auth(token)
        if user is None:
            return 401, None
        doc = self._own(user, doc_id)
        if doc is None:
            exists = isinstance(doc_id, str) and doc_id in self._docs \\
                and doc_id not in self._deleted
            return (403 if exists else 404), None'''),

    "F04": ("REQ-14", "token accepted at the exact expiry instant",
            "        if not self.clock.now() < created + self.token_ttl:",
            "        if self.clock.now() > created + self.token_ttl:"),

    "F05": ("REQ-15", "export_documents ignores revocation",
            '''    def export_documents(self, token):
        user = self._auth(token)''',
            '''    def export_documents(self, token):
        entry = self._tokens.get(token) if isinstance(token, str) else None
        expired = entry is None or not self.clock.now() < entry[1] + self.token_ttl
        user = None if expired else entry[0]'''),

    "F06": ("REQ-18", "search_documents returns deleted documents", _SEARCH,
            '''        owned = sorted((d for d in self._docs.values() if d["owner"] == user),
                       key=lambda d: d["_seq"])
        hits = [d for d in owned
                if q in d["title"].lower() or q in d["content"].lower()]'''),

    "F07": ("REQ-18", "update_document does not check the owner",
            '''    def update_document(self, token, doc_id, title, content):
        user = self._auth(token)
        if user is None:
            return 401, None
        doc = self._own(user, doc_id)''',
            '''    def update_document(self, token, doc_id, title, content):
        user = self._auth(token)
        if user is None:
            return 401, None
        doc = self._docs.get(doc_id) if isinstance(doc_id, str) else None
        if doc is not None and doc_id in self._deleted:
            doc = None'''),

    "F08": ("REQ-19", "last item of a page repeated on the next page",
            '''        rest = [d for d in self._visible(user) if d["_seq"] > after]''',
            '''        rest = [d for d in self._visible(user) if d["_seq"] >= after]'''),

    "F09": ("REQ-23", "key forgotten after a gateway timeout",
            '''        except GatewayTimeout:
            return 504, None''',
            '''        except GatewayTimeout:
            del self._keys[(user, idempotency_key)]
            return 504, None'''),

    "F10": ("REQ-23", "reused key with a different amount is not rejected",
            '''            if attempt["amount_cents"] != amount_cents:
                return 409, None
''',
            ""),

    # v2: natural misreadings of the type D items (DESIGN.md)
    "F11": ("REQ-23/D1", "idempotency keys scoped to the token instead of the user",
            '        attempt = self._keys.get((user, idempotency_key))\n        if attempt is not None:\n            if attempt["amount_cents"] != amount_cents:\n                return 409, None\n            if attempt["payment"] is not None:\n                return 200, dict(attempt["payment"])\n        else:\n            attempt = {"amount_cents": amount_cents, "payment": None,\n                       "reference": secrets.token_hex(12)}\n            self._keys[(user, idempotency_key)] = attempt',
            '        attempt = self._keys.get((token, idempotency_key))\n        if attempt is not None:\n            if attempt["amount_cents"] != amount_cents:\n                return 409, None\n            if attempt["payment"] is not None:\n                return 200, dict(attempt["payment"])\n        else:\n            attempt = {"amount_cents": amount_cents, "payment": None,\n                       "reference": secrets.token_hex(12)}\n            self._keys[(token, idempotency_key)] = attempt'),

    "F12": ("REQ-19/D2", "cursor bound to the token instead of the user",
            '            if issued is None or issued[0] != user:\n                return 400, None\n            after = issued[1]\n        rest = [d for d in self._visible(user) if d["_seq"] > after]\n        page = rest[:page_size]\n        next_cursor = None\n        if len(rest) > page_size:\n            next_cursor = secrets.token_urlsafe(16)\n            self._cursors[next_cursor] = (user, page[-1]["_seq"])',
            '            if issued is None or issued[0] != token:\n                return 400, None\n            after = issued[1]\n        rest = [d for d in self._visible(user) if d["_seq"] > after]\n        page = rest[:page_size]\n        next_cursor = None\n        if len(rest) > page_size:\n            next_cursor = secrets.token_urlsafe(16)\n            self._cursors[next_cursor] = (token, page[-1]["_seq"])'),

    "F13": ("REQ-19/D3", "cursor stores an offset into the list",
            '        rest = [d for d in self._visible(user) if d["_seq"] > after]\n        page = rest[:page_size]\n        next_cursor = None\n        if len(rest) > page_size:\n            next_cursor = secrets.token_urlsafe(16)\n            self._cursors[next_cursor] = (user, page[-1]["_seq"])',
            '        rest = self._visible(user)[after:]\n        page = rest[:page_size]\n        next_cursor = None\n        if len(rest) > page_size:\n            next_cursor = secrets.token_urlsafe(16)\n            self._cursors[next_cursor] = (user, after + len(page))'),

    "F14": ("REQ-21/D4", "update moves the document to the end of every ordering",
            '        doc["title"], doc["content"] = title, content\n',
            '        doc["title"], doc["content"] = title, content\n        doc["_seq"] = self._next()\n'),
}


def reference():
    return (HERE / "reference.py").read_text()


def variant(fault_id):
    _, _, old, new = FAULTS[fault_id]
    src = reference()
    n = src.count(old)
    if n != 1:
        raise ValueError(f"{fault_id}: target occurs {n} times in reference.py")
    return src.replace(old, new)
