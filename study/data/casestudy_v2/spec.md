# Document and payment service

<!-- Version 2 (see DESIGN.md): v1 plus the type D changes. Specification S shown to every agent. Comments like this one are stripped
by the loader. Never mention the seeded faults or the hidden tests here. -->

## Interface

The service is a Python module `solution.py` that defines a class `Service`.
Tests call it in-process; there is no network. Every method returns a pair
`(status, body)`, where `status` is an HTTP-style integer and `body` is a
`dict`, a `list`, or `None`.

    class Service:
        def __init__(self, clock, gateway, token_ttl=3600): ...
        def register(self, username, password): ...                 # 201 | 400 | 409
        def login(self, username, password): ...                    # 200 {"token": str} | 401
        def logout(self, token): ...                                # 204 | 401
        def create_document(self, token, title, content): ...       # 201 {"id": str} | 400 | 401
        def get_document(self, token, doc_id): ...                  # 200 doc | 401 | 404
        def update_document(self, token, doc_id, title, content): ...  # 200 doc | 400 | 401 | 404
        def delete_document(self, token, doc_id): ...               # 204 | 401 | 404
        def list_documents(self, token, page_size=20, cursor=None): ...
            # 200 {"items": [doc, ...], "next_cursor": str | None} | 400 | 401
        def search_documents(self, token, query): ...               # 200 [doc, ...] | 400 | 401
        def export_documents(self, token): ...                      # 200 [doc, ...] | 401
        def pay(self, token, amount_cents, idempotency_key): ...
            # 201 payment | 200 payment | 400 | 401 | 409 | 504
        def list_payments(self, token): ...                         # 200 [payment, ...] | 401

A document is `{"id", "owner", "title", "content", "created_at"}`. A payment is
`{"id", "amount_cents", "idempotency_key", "created_at"}`. In both, `created_at`
is the value of `clock.now()` when the object was created.

`clock` is an object with a method `now()` that returns the current time in
seconds as a float. The service never reads the system time.

`gateway` is an object with a method `charge(reference, amount_cents)`. Calling
it twice with the same `reference` charges at most once. It can raise
`GatewayTimeout` (importable as `from gateway import GatewayTimeout`); the
outcome of the charge is then unknown.

## Requirements

**REQ-14 Authentication.** `register` creates a user. A username is 3 to 32
characters from `[a-z0-9_]`, and a password is at least 8 characters;
otherwise the result is 400. An existing username gives 409. `login` with
correct credentials returns a new token; otherwise 401. A token is valid for
`token_ttl` seconds after its creation: it is accepted while
`clock.now() < created + token_ttl` and rejected from that instant on. Every
method that takes a token returns 401 for a missing, unknown, expired, or
revoked token. The *caller* of a method is the user the token belongs to.

**REQ-15 Logout.** `logout` revokes the given token. A revoked token is
rejected by every method. Other tokens of the same user stay valid.

**REQ-16 Document creation.** `create_document` stores a document owned by
the caller and returns its id. A title is 1 to 200 characters, and content is
at most 100,000 characters; otherwise 400. Ids are unique for the lifetime of
the service and are never reused.

**REQ-17 Ownership.** A user can read only the documents they own. For users
A and B with A != B, no response to a request by A contains a document owned
by B, whatever the method (get, list, search, export, update, delete). A
request by A on a document of B returns 404, exactly as for a document that
does not exist.

**REQ-18 Update and deletion.** Only the owner can update or delete a
document. Update validates title and content as in REQ-16. A deleted document
is never returned again by any method, and further get, update, or delete on
it return 404.

**REQ-19 Listing.** `list_documents` returns the caller's documents in
creation order, oldest first, in pages of `page_size` items (1 to 100,
otherwise 400). `next_cursor` is `None` on the last page. Following the
cursors from the first page returns every document of the caller exactly
once. Documents deleted after a cursor was issued are not returned;
documents created after it appear on later pages; no document is returned
twice and no remaining document is skipped. A cursor that was not issued to
the caller gives 400.

**REQ-20 Search.** `search_documents` returns the caller's documents whose
title or content contains `query`, ignoring case, in creation order. An
empty query gives 400.

**REQ-21 Export.** `export_documents` returns all documents of the caller,
in creation order. Updating a document does not change its position in any
ordering.

**REQ-22 Payments.** `pay` charges `amount_cents` through the gateway and
records a payment for the caller. The amount is an integer from 1 to
1,000,000; otherwise 400. A new payment returns 201. `list_payments` returns
the caller's recorded payments in creation order. If the gateway raises
`GatewayTimeout`, `pay` returns 504 and records no payment.

**REQ-23 Idempotency.** Retrying a payment never creates a second
transaction. Idempotency keys are scoped to the caller. A `pay` with a key
the caller already used and the same amount returns 200 with the original
payment and records nothing new; with a different amount it returns 409.
This holds also when the earlier attempt returned 504: a retry with the same
key and amount completes the payment (status 200 or 201) once the gateway
answers, and results in at most one recorded payment and at most one charge.
