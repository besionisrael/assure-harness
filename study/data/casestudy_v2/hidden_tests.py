"""Hidden suite T_h of the case study, version 2 (v1 tests plus the type D tests). Never shown to any agent; used only for
scoring. Tests assert only behavior that the specification (spec.md) fixes:
where S is silent (administrators, the status of a successful retry after a
504, ordering between 400 and 404) no assertion is made."""
from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule, run_state_machine_as_test

from gateway import GatewayTimeout
from solution import Service


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def now(self):
        return self.t


class Gateway:
    """Idempotent per reference. `fail` holds upcoming outcomes:
    'before' = time out without charging, 'after' = charge, then time out."""

    def __init__(self):
        self.charges, self.calls, self.fail = {}, 0, []

    def charge(self, reference, amount_cents):
        self.calls += 1
        mode = self.fail.pop(0) if self.fail else None
        if mode == "before":
            raise GatewayTimeout()
        self.charges.setdefault(reference, amount_cents)
        if mode == "after":
            raise GatewayTimeout()


def make(users=("alice", "bob"), ttl=3600):
    clock, gw = Clock(), Gateway()
    svc = Service(clock, gw, token_ttl=ttl)
    tokens = {}
    for u in users:
        assert svc.register(u, "password-" + u)[0] == 201
        tokens[u] = svc.login(u, "password-" + u)[1]["token"]
    return svc, clock, gw, tokens


def ids(docs):
    return [d["id"] for d in docs]


# ---------------------------------------------------------------- REQ-14
def test_req14_registration_validation():
    svc = Service(Clock(), Gateway())
    for name in ["ab", "a" * 33, "Alice", "al ice", "al-ice", "", None, 42]:
        assert svc.register(name, "longenough")[0] == 400, name
    assert svc.register("abc", "short7!")[0] == 400
    assert svc.register("abc", "exactly8")[0] == 201
    assert svc.register("a" * 32, "longenough")[0] == 201
    assert svc.register("abc", "another-password")[0] == 409


def test_req14_login_failures():
    svc, _, _, _ = make()
    assert svc.login("alice", "wrong")[0] == 401
    assert svc.login("nobody", "password-alice")[0] == 401


def test_req14_token_expiry_boundary():
    svc, clock, _, tokens = make(ttl=100)
    t = tokens["alice"]
    clock.t = 1000.0 + 99.999
    assert svc.export_documents(t)[0] == 200
    clock.t = 1000.0 + 100
    assert svc.export_documents(t)[0] == 401
    clock.t = 1000.0 + 5000
    assert svc.get_document(t, "doc-1")[0] == 401


def test_req14_expired_token_rejected_everywhere():
    svc, clock, _, tokens = make(ttl=10)
    t = tokens["alice"]
    doc_id = svc.create_document(t, "x", "y")[1]["id"]
    clock.t += 10
    calls = [lambda: svc.logout(t), lambda: svc.create_document(t, "a", "b"),
             lambda: svc.get_document(t, doc_id), lambda: svc.update_document(t, doc_id, "a", "b"),
             lambda: svc.delete_document(t, doc_id), lambda: svc.list_documents(t),
             lambda: svc.search_documents(t, "x"), lambda: svc.export_documents(t),
             lambda: svc.pay(t, 100, "k"), lambda: svc.list_payments(t)]
    for call in calls:
        assert call()[0] == 401


def test_req14_unknown_and_missing_tokens():
    svc, _, _, _ = make()
    for t in [None, "", "forged-token"]:
        assert svc.list_documents(t)[0] == 401
        assert svc.pay(t, 100, "k")[0] == 401


def test_req14_token_checked_before_validation():
    svc, _, _, _ = make()
    assert svc.create_document("forged", "", "x")[0] == 401
    assert svc.pay("forged", -5, "k")[0] == 401


# ---------------------------------------------------------------- REQ-15
def test_req15_revoked_token_rejected_everywhere():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    doc_id = svc.create_document(t, "x", "y")[1]["id"]
    assert svc.logout(t)[0] == 204
    calls = [lambda: svc.logout(t), lambda: svc.create_document(t, "a", "b"),
             lambda: svc.get_document(t, doc_id), lambda: svc.update_document(t, doc_id, "a", "b"),
             lambda: svc.delete_document(t, doc_id), lambda: svc.list_documents(t),
             lambda: svc.search_documents(t, "x"), lambda: svc.export_documents(t),
             lambda: svc.pay(t, 100, "k"), lambda: svc.list_payments(t)]
    for call in calls:
        assert call()[0] == 401


def test_req15_other_tokens_stay_valid():
    svc, _, _, tokens = make()
    second = svc.login("alice", "password-alice")[1]["token"]
    assert second != tokens["alice"]
    assert svc.logout(tokens["alice"])[0] == 204
    assert svc.export_documents(second)[0] == 200
    assert svc.export_documents(tokens["bob"])[0] == 200


# ---------------------------------------------------------------- REQ-16
def test_req16_document_validation():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    assert svc.create_document(t, "", "c")[0] == 400
    assert svc.create_document(t, "x" * 201, "c")[0] == 400
    assert svc.create_document(t, None, "c")[0] == 400
    assert svc.create_document(t, "t", "c" * 100_001)[0] == 400
    assert svc.create_document(t, "x" * 200, "c" * 100_000)[0] == 201
    assert svc.create_document(t, "t", "")[0] == 201
    assert svc.export_documents(t)[1].__len__() == 2


def test_req16_ids_unique_and_never_reused():
    svc, _, _, tokens = make()
    seen = set()
    for i in range(20):
        doc_id = svc.create_document(tokens["alice" if i % 2 else "bob"], f"t{i}", "")[1]["id"]
        assert doc_id not in seen
        seen.add(doc_id)
        if i % 3 == 0:
            owner = tokens["alice" if i % 2 else "bob"]
            assert svc.delete_document(owner, doc_id)[0] == 204


def test_req16_document_fields():
    svc, clock, _, tokens = make()
    clock.t = 1234.5
    doc_id = svc.create_document(tokens["alice"], "T", "C")[1]["id"]
    doc = svc.get_document(tokens["alice"], doc_id)[1]
    assert doc == {"id": doc_id, "owner": "alice", "title": "T", "content": "C",
                   "created_at": 1234.5}


# ---------------------------------------------------------------- REQ-17
def _bob_doc(svc, tokens):
    return svc.create_document(tokens["bob"], "Bob secret", "shared word")[1]["id"]


def test_req17_get_other_users_document_is_404():
    svc, _, _, tokens = make()
    doc_id = _bob_doc(svc, tokens)
    assert svc.get_document(tokens["alice"], doc_id) == svc.get_document(tokens["alice"], "doc-999999")
    assert svc.get_document(tokens["alice"], doc_id)[0] == 404


def test_req17_update_and_delete_other_users_document_is_404():
    svc, _, _, tokens = make()
    doc_id = _bob_doc(svc, tokens)
    assert svc.update_document(tokens["alice"], doc_id, "pwned", "x")[0] == 404
    assert svc.delete_document(tokens["alice"], doc_id)[0] == 404
    doc = svc.get_document(tokens["bob"], doc_id)[1]
    assert doc["title"] == "Bob secret" and doc["content"] == "shared word"


def test_req17_search_never_returns_other_users_documents():
    svc, _, _, tokens = make()
    _bob_doc(svc, tokens)
    mine = svc.create_document(tokens["alice"], "Alice", "shared word")[1]["id"]
    status, hits = svc.search_documents(tokens["alice"], "shared")
    assert status == 200 and ids(hits) == [mine]


def test_req17_list_and_export_never_return_other_users_documents():
    svc, _, _, tokens = make()
    _bob_doc(svc, tokens)
    assert svc.list_documents(tokens["alice"])[1]["items"] == []
    assert svc.export_documents(tokens["alice"])[1] == []


def test_req17_cursor_of_another_user_is_rejected():
    svc, _, _, tokens = make()
    for i in range(5):
        svc.create_document(tokens["bob"], f"b{i}", "")
        svc.create_document(tokens["alice"], f"a{i}", "")
    bob_cursor = svc.list_documents(tokens["bob"], page_size=2)[1]["next_cursor"]
    assert bob_cursor is not None
    status, body = svc.list_documents(tokens["alice"], page_size=2, cursor=bob_cursor)
    assert status == 400


# ---------------------------------------------------------------- REQ-18
def test_req18_deleted_document_never_returned():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    keep = svc.create_document(t, "keep findme", "")[1]["id"]
    gone = svc.create_document(t, "gone findme", "")[1]["id"]
    assert svc.delete_document(t, gone)[0] == 204
    assert svc.get_document(t, gone)[0] == 404
    assert svc.update_document(t, gone, "x", "y")[0] == 404
    assert svc.delete_document(t, gone)[0] == 404
    assert ids(svc.list_documents(t)[1]["items"]) == [keep]
    assert ids(svc.search_documents(t, "findme")[1]) == [keep]
    assert ids(svc.export_documents(t)[1]) == [keep]


def test_req18_update_validates():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    doc_id = svc.create_document(t, "ok", "ok")[1]["id"]
    assert svc.update_document(t, doc_id, "", "x")[0] == 400
    assert svc.update_document(t, doc_id, "t", "c" * 100_001)[0] == 400
    assert svc.get_document(t, doc_id)[1]["title"] == "ok"


# ---------------------------------------------------------------- REQ-19
def _walk(svc, token, page_size):
    seen, cursor, pages = [], None, 0
    while True:
        status, body = svc.list_documents(token, page_size=page_size, cursor=cursor)
        assert status == 200
        assert len(body["items"]) <= page_size
        seen += ids(body["items"])
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            return seen, pages
        assert pages < 1000


def test_req19_pagination_returns_each_document_once_in_order():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    created = [svc.create_document(t, f"t{i}", "")[1]["id"] for i in range(23)]
    for size in [1, 2, 5, 7, 22, 23, 24, 100]:
        seen, _ = _walk(svc, t, size)
        assert seen == created, size


def test_req19_page_size_bounds():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    for bad in [0, 101, -1, 2.5, "3", None]:
        assert svc.list_documents(t, page_size=bad)[0] == 400, bad
    assert svc.list_documents(t, page_size=1)[0] == 200
    assert svc.list_documents(t, page_size=100)[0] == 200


def test_req19_unknown_cursor_rejected():
    svc, _, _, tokens = make()
    assert svc.list_documents(tokens["alice"], cursor="forged")[0] == 400


def test_req19_last_page_has_no_cursor():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    assert svc.list_documents(t)[1] == {"items": [], "next_cursor": None}
    for i in range(4):
        svc.create_document(t, f"t{i}", "")
    body = svc.list_documents(t, page_size=4)[1]
    assert len(body["items"]) == 4 and body["next_cursor"] is None


# ---------------------------------------------------------------- REQ-20
def test_req20_search_case_insensitive_title_or_content_in_order():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    a = svc.create_document(t, "Quarterly REPORT", "")[1]["id"]
    svc.create_document(t, "Other", "nothing")
    c = svc.create_document(t, "Misc", "see the report here")[1]["id"]
    assert ids(svc.search_documents(t, "rEpOrT")[1]) == [a, c]
    assert svc.search_documents(t, "absent")[1] == []
    assert svc.search_documents(t, "")[0] == 400


# ---------------------------------------------------------------- REQ-21
def test_req21_export_in_creation_order_with_current_content():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    first = svc.create_document(t, "b", "1")[1]["id"]
    second = svc.create_document(t, "a", "2")[1]["id"]
    svc.update_document(t, first, "b2", "1b")
    docs = svc.export_documents(t)[1]
    assert ids(docs) == [first, second]
    assert docs[0]["title"] == "b2" and docs[0]["content"] == "1b"


# ---------------------------------------------------------------- REQ-22
def test_req22_amount_validation():
    svc, _, gw, tokens = make()
    t = tokens["alice"]
    for i, bad in enumerate([0, -1, 1_000_001, 10.5, "100", None]):
        assert svc.pay(t, bad, f"bad-{i}")[0] == 400, bad
    assert gw.calls == 0
    assert svc.pay(t, 1, "min")[0] == 201
    assert svc.pay(t, 1_000_000, "max")[0] == 201


def test_req22_payments_listed_per_user_in_order():
    svc, clock, _, tokens = make()
    p1 = svc.pay(tokens["alice"], 100, "k1")[1]
    svc.pay(tokens["bob"], 200, "k1")
    clock.t += 1
    p2 = svc.pay(tokens["alice"], 300, "k2")[1]
    listed = svc.list_payments(tokens["alice"])[1]
    assert [p["id"] for p in listed] == [p1["id"], p2["id"]]
    assert [p["amount_cents"] for p in listed] == [100, 300]
    assert listed[0]["idempotency_key"] == "k1"


def test_req22_gateway_timeout_returns_504():
    svc, _, gw, tokens = make()
    gw.fail = ["before"]
    assert svc.pay(tokens["alice"], 100, "k")[0] == 504
    assert svc.list_payments(tokens["alice"])[1] == []


# ---------------------------------------------------------------- REQ-23
def test_req23_retry_returns_original_and_records_nothing():
    svc, _, gw, tokens = make()
    t = tokens["alice"]
    status, first = svc.pay(t, 500, "order-9")
    assert status == 201
    status, again = svc.pay(t, 500, "order-9")
    assert status == 200 and again == first
    assert len(svc.list_payments(t)[1]) == 1 and len(gw.charges) == 1


def test_req23_same_key_different_amount_is_409():
    svc, _, gw, tokens = make()
    t = tokens["alice"]
    svc.pay(t, 500, "order-9")
    assert svc.pay(t, 501, "order-9")[0] == 409
    assert len(svc.list_payments(t)[1]) == 1 and len(gw.charges) == 1


def test_req23_keys_are_scoped_per_user():
    svc, _, gw, tokens = make()
    assert svc.pay(tokens["alice"], 500, "shared-key")[0] == 201
    assert svc.pay(tokens["bob"], 700, "shared-key")[0] == 201
    assert len(gw.charges) == 2
    assert len(svc.list_payments(tokens["bob"])[1]) == 1


def test_req23_retry_after_timeout_charges_at_most_once():
    for mode in ["after", "before"]:
        svc, _, gw, tokens = make()
        t = tokens["alice"]
        gw.fail = [mode]
        assert svc.pay(t, 900, "order-1")[0] == 504
        status, payment = svc.pay(t, 900, "order-1")
        assert status in (200, 201) and payment["amount_cents"] == 900, mode
        svc.pay(t, 900, "order-1")
        assert len(gw.charges) == 1, mode
        assert len(svc.list_payments(t)[1]) == 1, mode


def test_req23_different_amount_after_timeout_is_409():
    svc, _, gw, tokens = make()
    t = tokens["alice"]
    gw.fail = ["after"]
    assert svc.pay(t, 900, "order-1")[0] == 504
    assert svc.pay(t, 901, "order-1")[0] == 409
    assert len(gw.charges) == 1


# ---------------------------------------------------------------- v2, type D items (DESIGN.md)
def test_v2_d1_keys_scoped_to_user_across_sessions():
    svc, _, gw, tokens = make()
    t1 = tokens["alice"]
    status, first = svc.pay(t1, 700, "order-x")
    assert status == 201
    assert svc.logout(t1)[0] == 204
    t2 = svc.login("alice", "password-alice")[1]["token"]
    status, again = svc.pay(t2, 700, "order-x")
    assert status == 200 and again == first
    t3 = svc.login("alice", "password-alice")[1]["token"]
    assert svc.pay(t3, 701, "order-x")[0] == 409
    assert len(gw.charges) == 1 and len(svc.list_payments(t3)[1]) == 1


def test_v2_d1_retry_after_timeout_in_a_new_session_charges_once():
    svc, _, gw, tokens = make()
    gw.fail = ["after"]
    assert svc.pay(tokens["alice"], 900, "order-y")[0] == 504
    t2 = svc.login("alice", "password-alice")[1]["token"]
    status, payment = svc.pay(t2, 900, "order-y")
    assert status in (200, 201) and payment["amount_cents"] == 900
    assert len(gw.charges) == 1 and len(svc.list_payments(t2)[1]) == 1


def test_v2_d2_cursor_valid_with_another_token_of_the_same_user():
    svc, _, _, tokens = make()
    t1 = tokens["alice"]
    created = [svc.create_document(t1, f"t{i}", "")[1]["id"] for i in range(5)]
    cursor = svc.list_documents(t1, page_size=2)[1]["next_cursor"]
    t2 = svc.login("alice", "password-alice")[1]["token"]
    assert svc.logout(t1)[0] == 204
    status, body = svc.list_documents(t2, page_size=2, cursor=cursor)
    assert status == 200 and ids(body["items"]) == created[2:4]


def _walk_from(svc, token, page_size, cursor):
    seen = []
    while cursor is not None:
        status, body = svc.list_documents(token, page_size=page_size, cursor=cursor)
        assert status == 200
        seen += ids(body["items"])
        cursor = body["next_cursor"]
        assert len(seen) < 1000
    return seen


def test_v2_d3_pagination_with_deletions_and_creations_between_pages():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    d = [svc.create_document(t, f"t{i}", "")[1]["id"] for i in range(6)]
    first = svc.list_documents(t, page_size=2)[1]
    assert ids(first["items"]) == d[:2]
    assert svc.delete_document(t, d[0])[0] == 204      # already returned
    assert svc.delete_document(t, d[3])[0] == 204      # not yet returned
    d6 = svc.create_document(t, "t6", "")[1]["id"]
    rest = _walk_from(svc, t, 2, first["next_cursor"])
    assert rest == [d[2], d[4], d[5], d6]


def test_v2_d3_deleting_the_last_returned_item_does_not_skip_the_next():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    d = [svc.create_document(t, f"t{i}", "")[1]["id"] for i in range(4)]
    first = svc.list_documents(t, page_size=2)[1]
    assert svc.delete_document(t, d[1])[0] == 204
    assert _walk_from(svc, t, 2, first["next_cursor"]) == d[2:]


def test_v2_d4_update_keeps_position_in_every_ordering():
    svc, _, _, tokens = make()
    t = tokens["alice"]
    d = [svc.create_document(t, f"key {i}", "")[1]["id"] for i in range(3)]
    assert svc.update_document(t, d[0], "key updated", "new")[0] == 200
    assert ids(svc.list_documents(t)[1]["items"]) == d
    assert ids(svc.search_documents(t, "key")[1]) == d
    assert ids(svc.export_documents(t)[1]) == d
    assert _walk_from(svc, t, 1, svc.list_documents(t, page_size=1)[1]["next_cursor"]) == d[1:]


# ---------------------------------------------------------------- stateful model
class TwoUsers(RuleBasedStateMachine):
    """Model-based check of REQ-17, REQ-18, REQ-19, REQ-20, and REQ-21."""

    def __init__(self):
        super().__init__()
        self.svc, _, _, self.tokens = make()
        self.model = {"alice": [], "bob": []}   # ordered list of (id, title, content)

    @rule(user=st.sampled_from(["alice", "bob"]), title=st.sampled_from(["a", "b", "ab"]),
          content=st.sampled_from(["", "x", "ab"]))
    def create(self, user, title, content):
        status, body = self.svc.create_document(self.tokens[user], title, content)
        assert status == 201
        self.model[user].append((body["id"], title, content))

    @rule(user=st.sampled_from(["alice", "bob"]), owner=st.sampled_from(["alice", "bob"]),
          i=st.integers(0, 50))
    def delete(self, user, owner, i):
        docs = self.model[owner]
        if not docs:
            return
        doc_id = docs[i % len(docs)][0]
        status, _ = self.svc.delete_document(self.tokens[user], doc_id)
        if user == owner:
            assert status == 204
            docs.pop(i % len(docs))
        else:
            assert status == 404

    @rule(user=st.sampled_from(["alice", "bob"]), owner=st.sampled_from(["alice", "bob"]),
          i=st.integers(0, 50), title=st.sampled_from(["n", "m"]))
    def update(self, user, owner, i, title):
        docs = self.model[owner]
        if not docs:
            return
        k = i % len(docs)
        doc_id = docs[k][0]
        status, _ = self.svc.update_document(self.tokens[user], doc_id, title, "u")
        if user == owner:
            assert status == 200
            docs[k] = (doc_id, title, "u")
        else:
            assert status == 404

    @rule(user=st.sampled_from(["alice", "bob"]), size=st.integers(1, 4))
    def paginate(self, user, size):
        seen, _ = _walk(self.svc, self.tokens[user], size)
        assert seen == [d[0] for d in self.model[user]]

    @rule(user=st.sampled_from(["alice", "bob"]), q=st.sampled_from(["a", "B", "x", "u"]))
    def search(self, user, q):
        hits = self.svc.search_documents(self.tokens[user], q)[1]
        expected = [d[0] for d in self.model[user]
                    if q.lower() in d[1].lower() or q.lower() in d[2].lower()]
        assert ids(hits) == expected

    @invariant()
    def export_matches_model(self):
        for user in ("alice", "bob"):
            docs = self.svc.export_documents(self.tokens[user])[1]
            assert [(d["id"], d["title"], d["content"]) for d in docs] == self.model[user]


def test_stateful_two_users():
    run_state_machine_as_test(TwoUsers, settings=settings(max_examples=60, stateful_step_count=25,
                                                          deadline=None, database=None))
