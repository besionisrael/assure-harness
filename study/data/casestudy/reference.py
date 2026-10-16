"""Reference implementation of the case-study service (never shown to agents).

Seeded faults (faults.py) are single, local edits of this file, so keep the
lines they target unchanged or update faults.py at the same time."""
import re
import secrets

from gateway import GatewayTimeout

USERNAME = re.compile(r"[a-z0-9_]{3,32}")
MAX_TITLE, MAX_CONTENT = 200, 100_000
MAX_AMOUNT = 1_000_000


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


class Service:
    def __init__(self, clock, gateway, token_ttl=3600):
        self.clock, self.gateway, self.token_ttl = clock, gateway, token_ttl
        self._users = {}         # username -> password
        self._tokens = {}        # token -> (username, created)
        self._revoked = set()
        self._docs = {}          # id -> document (including deleted ones)
        self._deleted = set()
        self._seq = 0            # creation sequence shared by documents and payments
        self._cursors = {}       # cursor -> (username, seq of the last item returned)
        self._payments = []      # recorded payments, (username, payment)
        self._keys = {}          # (username, key) -> attempt record

    # ------------------------------------------------------------ helpers
    def _next(self):
        self._seq += 1
        return self._seq

    def _auth(self, token):
        entry = self._tokens.get(token) if isinstance(token, str) else None
        if entry is None or token in self._revoked:
            return None
        user, created = entry
        if not self.clock.now() < created + self.token_ttl:
            return None
        return user

    def _own(self, user, doc_id):
        doc = self._docs.get(doc_id) if isinstance(doc_id, str) else None
        if doc is None or doc["owner"] != user or doc_id in self._deleted:
            return None
        return doc

    def _visible(self, user):
        docs = [d for d in self._docs.values()
                if d["owner"] == user and d["id"] not in self._deleted]
        return sorted(docs, key=lambda d: d["_seq"])

    @staticmethod
    def _out(doc):
        return {k: v for k, v in doc.items() if not k.startswith("_")}

    @staticmethod
    def _valid_doc(title, content):
        return (isinstance(title, str) and 1 <= len(title) <= MAX_TITLE
                and isinstance(content, str) and len(content) <= MAX_CONTENT)

    # ------------------------------------------------------------ accounts
    def register(self, username, password):
        if not (isinstance(username, str) and USERNAME.fullmatch(username)
                and isinstance(password, str) and len(password) >= 8):
            return 400, None
        if username in self._users:
            return 409, None
        self._users[username] = password
        return 201, {"username": username}

    def login(self, username, password):
        if not isinstance(username, str) or self._users.get(username) != password:
            return 401, None
        token = secrets.token_urlsafe(24)
        self._tokens[token] = (username, self.clock.now())
        return 200, {"token": token}

    def logout(self, token):
        user = self._auth(token)
        if user is None:
            return 401, None
        self._revoked.add(token)
        return 204, None

    # ------------------------------------------------------------ documents
    def create_document(self, token, title, content):
        user = self._auth(token)
        if user is None:
            return 401, None
        if not self._valid_doc(title, content):
            return 400, None
        seq = self._next()
        doc_id = f"doc-{seq}"
        self._docs[doc_id] = {"id": doc_id, "owner": user, "title": title,
                              "content": content, "created_at": self.clock.now(), "_seq": seq}
        return 201, {"id": doc_id}

    def get_document(self, token, doc_id):
        user = self._auth(token)
        if user is None:
            return 401, None
        doc = self._own(user, doc_id)
        if doc is None:
            return 404, None
        return 200, self._out(doc)

    def update_document(self, token, doc_id, title, content):
        user = self._auth(token)
        if user is None:
            return 401, None
        doc = self._own(user, doc_id)
        if doc is None:
            return 404, None
        if not self._valid_doc(title, content):
            return 400, None
        doc["title"], doc["content"] = title, content
        return 200, self._out(doc)

    def delete_document(self, token, doc_id):
        user = self._auth(token)
        if user is None:
            return 401, None
        doc = self._own(user, doc_id)
        if doc is None:
            return 404, None
        self._deleted.add(doc_id)
        return 204, None

    def list_documents(self, token, page_size=20, cursor=None):
        user = self._auth(token)
        if user is None:
            return 401, None
        if not (_is_int(page_size) and 1 <= page_size <= 100):
            return 400, None
        after = 0
        if cursor is not None:
            issued = self._cursors.get(cursor) if isinstance(cursor, str) else None
            if issued is None or issued[0] != user:
                return 400, None
            after = issued[1]
        rest = [d for d in self._visible(user) if d["_seq"] > after]
        page = rest[:page_size]
        next_cursor = None
        if len(rest) > page_size:
            next_cursor = secrets.token_urlsafe(16)
            self._cursors[next_cursor] = (user, page[-1]["_seq"])
        return 200, {"items": [self._out(d) for d in page], "next_cursor": next_cursor}

    def search_documents(self, token, query):
        user = self._auth(token)
        if user is None:
            return 401, None
        if not isinstance(query, str) or query == "":
            return 400, None
        q = query.lower()
        hits = [d for d in self._visible(user)
                if q in d["title"].lower() or q in d["content"].lower()]
        return 200, [self._out(d) for d in hits]

    def export_documents(self, token):
        user = self._auth(token)
        if user is None:
            return 401, None
        return 200, [self._out(d) for d in self._visible(user)]

    # ------------------------------------------------------------ payments
    def pay(self, token, amount_cents, idempotency_key):
        user = self._auth(token)
        if user is None:
            return 401, None
        if not (_is_int(amount_cents) and 1 <= amount_cents <= MAX_AMOUNT):
            return 400, None
        attempt = self._keys.get((user, idempotency_key))
        if attempt is not None:
            if attempt["amount_cents"] != amount_cents:
                return 409, None
            if attempt["payment"] is not None:
                return 200, dict(attempt["payment"])
        else:
            attempt = {"amount_cents": amount_cents, "payment": None,
                       "reference": secrets.token_hex(12)}
            self._keys[(user, idempotency_key)] = attempt
        try:
            self.gateway.charge(attempt["reference"], amount_cents)
        except GatewayTimeout:
            return 504, None
        seq = self._next()
        payment = {"id": f"pay-{seq}", "amount_cents": amount_cents,
                   "idempotency_key": idempotency_key, "created_at": self.clock.now()}
        attempt["payment"] = payment
        self._payments.append((user, payment))
        return 201, dict(payment)

    def list_payments(self, token):
        user = self._auth(token)
        if user is None:
            return 401, None
        return 200, [dict(p) for u, p in self._payments if u == user]
