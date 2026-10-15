# Seeded faults (DRAFT v0.1). NEVER shown to any agent.

Each fault is a variant of the reference implementation that changes one
behavior. Acceptance rule for every variant: it passes the visible suite T_v
and fails the hidden suite T_h. Fault classes are fixed before any verifier
output is seen.

| ID | Req. | Class | Change to the reference | Why it is realistic |
|---|---|---|---|---|
| F01 | REQ-17 | missing authorization filter | `search_documents` filters by query but not by owner | the paper's own example: one endpoint forgets the ownership filter |
| F02 | REQ-17 | missing authorization filter | the cursor of `list_documents` is not bound to the caller, so another user's cursor returns their page | IDOR through opaque tokens |
| F03 | REQ-17 | information leak | `get_document` returns 403 instead of 404 for another user's document | existence oracle; violates "exactly as for a document that does not exist" |
| F04 | REQ-14 | boundary error | the token is accepted while `now <= created + ttl` (one instant too long) | classic off-by-one on expiry |
| F05 | REQ-15 | incomplete revocation | `export_documents` checks expiry but not revocation | auth check duplicated per endpoint, one copy outdated |
| F06 | REQ-18 | stale state | `search_documents` still returns deleted documents | soft delete not applied to one read path |
| F07 | REQ-18 | missing authorization check | `update_document` does not check the owner | write path not covered by the read filter |
| F08 | REQ-19 | pagination error | the item at each page boundary is repeated on the next page | off-by-one on the cursor offset |
| F09 | REQ-23 | non-idempotent retry | on `GatewayTimeout` the key is not recorded, so a retry records a second payment | the paper's own example: non-idempotent retry path |
| F10 | REQ-23 | key misuse | reusing a key with a different amount returns the original payment (200) instead of 409 | lenient idempotency lookup |

Coverage: REQ-14, 15, 17 (x3), 18 (x2), 19, 23 (x2). REQ-16, 20, 21, and 22
have no seeded fault; they serve as controls (verifier false oracles there
cost precision without any detection to gain).
