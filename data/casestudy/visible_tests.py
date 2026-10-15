"""Visible acceptance tests T_v of the case study (shown to the builder)."""
from gateway import GatewayTimeout  # noqa: F401  (documents the module name)
from solution import Service


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def now(self):
        return self.t


class Gateway:
    def __init__(self):
        self.charges = {}

    def charge(self, reference, amount_cents):
        self.charges.setdefault(reference, amount_cents)


def make():
    clock, gw = Clock(), Gateway()
    svc = Service(clock, gw)
    assert svc.register("alice", "password1")[0] == 201
    status, body = svc.login("alice", "password1")
    assert status == 200
    return svc, clock, gw, body["token"]


def test_register_and_login():
    svc, _, _, token = make()
    assert isinstance(token, str)
    assert svc.register("alice", "password2")[0] == 409
    assert svc.login("alice", "wrong-password")[0] == 401


def test_create_and_get_document():
    svc, _, _, token = make()
    status, body = svc.create_document(token, "Notes", "hello")
    assert status == 201
    status, doc = svc.get_document(token, body["id"])
    assert status == 200
    assert doc["title"] == "Notes" and doc["content"] == "hello" and doc["owner"] == "alice"


def test_update_and_delete_document():
    svc, _, _, token = make()
    doc_id = svc.create_document(token, "Draft", "v1")[1]["id"]
    status, doc = svc.update_document(token, doc_id, "Final", "v2")
    assert status == 200 and doc["title"] == "Final"
    assert svc.delete_document(token, doc_id)[0] == 204
    assert svc.get_document(token, doc_id)[0] == 404


def test_list_single_page():
    svc, _, _, token = make()
    ids = [svc.create_document(token, f"t{i}", "")[1]["id"] for i in range(3)]
    status, page = svc.list_documents(token)
    assert status == 200
    assert [d["id"] for d in page["items"]] == ids and page["next_cursor"] is None


def test_search_and_export():
    svc, _, _, token = make()
    svc.create_document(token, "Budget 2026", "numbers")
    svc.create_document(token, "Holidays", "beach")
    status, hits = svc.search_documents(token, "budget")
    assert status == 200 and [d["title"] for d in hits] == ["Budget 2026"]
    status, docs = svc.export_documents(token)
    assert status == 200 and len(docs) == 2


def test_payment_and_listing():
    svc, _, gw, token = make()
    status, payment = svc.pay(token, 1500, "order-1")
    assert status == 201 and payment["amount_cents"] == 1500
    assert len(gw.charges) == 1
    status, payments = svc.list_payments(token)
    assert status == 200 and [p["id"] for p in payments] == [payment["id"]]


def test_invalid_token_rejected():
    svc, _, _, _ = make()
    assert svc.get_document("not-a-token", "doc-1")[0] == 401
    assert svc.export_documents(None)[0] == 401
