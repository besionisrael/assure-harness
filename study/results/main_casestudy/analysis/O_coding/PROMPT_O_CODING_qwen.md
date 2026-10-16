You are coding qualitative data for a software-engineering study. Be careful and literal.

## Context

AI agents worked from a specification of a small service (documents and payments).
"Verifier" agents (conditions A, B, AB, ABp) wrote tests from the specification;
the "builder" agent wrote the program and its own tests (condition SV). Phase A of a
verifier also lists OPEN QUESTIONS: points where it finds the specification unclear.

The specification deliberately leaves five points open:

- O1 administrators: whether an administrator role exists or may read all documents.
- O2 case folding beyond ASCII: what "ignoring case" means for non-ASCII text
  (for example "Straße" vs "STRASSE", lower() vs casefold()).
- O3 key used by a rejected request: whether an idempotency key counts as "used"
  after a payment request that was rejected (for example with 400).
- O4 empty idempotency key: whether an empty string is a valid idempotency key.
- O5 unencodable characters: what happens with characters that cannot be encoded
  (for example lone surrogates in a password), i.e. whether a method may raise.

## What you receive

Below are 38 (run, condition, item) cases. For each, a keyword search found
candidate open questions and/or candidate tests; candidates may be false matches.
Excerpts are grouped by run and condition, then by item. A test tagged
**[still fails on final]** fails on the builder's final program; a test tagged
**[false oracle]** fails on the reference implementation.

## Coding rules (apply literally)

- coder_raised: "yes" if at least one listed open question of that case genuinely
  concerns the item, otherwise "no". Only Phase A produces open questions.
- coder_tested: the number of listed tests of that case that genuinely assert a
  behavior on the item (0 if none). A test that merely mentions a keyword, or
  concerns another point, does not count.
- coder_disputed: "yes" if at least one test you counted in coder_tested is tagged
  [still fails on final], otherwise "no".
- coder_notes: one short sentence when a decision was not obvious; otherwise empty.

## Required answer

Only a CSV block, with this header and exactly these 38 rows in this order, filled in:

```csv
run,condition,item,coder_raised,coder_tested,coder_disputed,coder_notes
0,A,O2,,,,
0,A,O4,,,,
0,AB,O2,,,,
0,AB,O3,,,,
0,AB,O4,,,,
0,AB,O5,,,,
0,ABp,O3,,,,
1,A,O2,,,,
1,A,O4,,,,
1,B,O3,,,,
1,AB,O2,,,,
1,AB,O4,,,,
2,A,O2,,,,
2,B,O2,,,,
2,AB,O2,,,,
2,AB,O3,,,,
2,AB,O4,,,,
2,AB,O5,,,,
2,ABp,O3,,,,
3,A,O3,,,,
3,AB,O2,,,,
3,AB,O3,,,,
3,AB,O4,,,,
3,AB,O5,,,,
3,ABp,O3,,,,
4,A,O2,,,,
4,A,O3,,,,
4,A,O4,,,,
4,B,O2,,,,
4,B,O3,,,,
4,B,O4,,,,
4,B,O5,,,,
4,AB,O2,,,,
4,AB,O3,,,,
4,AB,O4,,,,
4,AB,O5,,,,
4,ABp,O4,,,,
4,ABp,O5,,,,
```

Quote coder_notes with double quotes if it contains a comma.

## Excerpts

## run 0, A
### O2 (case folding beyond ASCII)

- open question: Case-insensitivity for non-ASCII text is not specified, so only ASCII is tested.

### O4 (empty idempotency key)

- open question: Empty or overlong idempotency keys are not specified.

## run 0, AB
### O2 (case folding beyond ASCII)

- open question: The meaning of "ignoring case" for non-ASCII text is unspecified, so tests use ASCII.
- test `test_phase_b::test_unicode_passwords_exact_match_only`

```python
def test_unicode_passwords_exact_match_only(pw):
    """Login succeeds only with the exact registered password, for any unicode password."""
    svc, _, _ = make()
    assert svc.register("alice", pw)[0] == 201, f"input={pw!r} register"
    out = svc.login("alice", pw)
    assert out[0] == 200, f"input={pw!r} output={out!r}"
    out = svc.login("alice", pw + "x")
    assert out[0] == 401, f"input={pw + 'x'!r} output={out!r}"
    out = svc.login("alice", pw[:-1])
    assert out[0] == 401, f"input={pw[:-1]!r} output={out!r}"
```

### O3 (is a key used by a rejected request)

- open question: The precedence between 400 (invalid amount) and 409 or 200 (key replay) is unspecified.
- test `test_phase_b::test_rejected_amount_does_not_consume_the_key`

```python
def test_rejected_amount_does_not_consume_the_key():
    """A payment rejected with 400 records nothing, so the same key can still make a new payment (201)."""
    svc, _, gw = make()
    tok = user(svc)
    assert svc.pay(tok, 0, "k")[0] == 400, "input=(0,'k')"
    assert svc.pay(tok, 2_000_000, "k")[0] == 400, "input=(2000000,'k')"
    out = svc.pay(tok, 700, "k")
    assert out[0] == 201 and out[1]["amount_cents"] == 700, f"input=(700,'k') output={out!r}"
    assert list(gw.charged.values()) == [700], f"input=(700,'k') charges={gw.charged!r}"
```

### O4 (empty idempotency key)

- open question: Constraints on idempotency keys are unspecified (empty, non-string).

### O5 (unencodable characters)

- test `test_phase_b::test_password_with_lone_surrogates_is_a_valid_password`

```python
def test_password_with_lone_surrogates_is_a_valid_password():
    """A password of at least 8 characters is valid, so registering and logging in with it succeeds."""
    svc, _, _ = make()
    pw = "\ud800" * 8
    out = svc.register("alice", pw)
    assert out[0] == 201, f"input={pw!r} output={out!r}"
    out = svc.login("alice", pw)
    assert out[0] == 200 and isinstance(out[1]["token"], str), f"input={pw!r} output={out!r}"
```
- test `test_phase_b::test_login_with_lone_surrogate_password_is_401_not_error`

```python
def test_login_with_lone_surrogate_password_is_401_not_error():
    """Login with an incorrect password returns 401 whatever characters the password contains."""
    svc, _, _ = make()
    svc.register("alice", PW)
    pw = "bad\udc80password"
    out = svc.login("alice", pw)
    assert out[0] == 401, f"input={pw!r} output={out!r}"
```
- test `test_phase_b::test_surrogate_passwords_register_and_login`

```python
def test_surrogate_passwords_register_and_login(pw):
    """Any password of at least 8 characters registers (201) and then logs in (200)."""
    svc, _, _ = make()
    out = svc.register("alice", pw)
    assert out[0] == 201, f"input={pw!r} output={out!r}"
    out = svc.login("alice", pw)
    assert out[0] == 200, f"input={pw!r} output={out!r}"
```
- test `test_phase_b::test_documents_may_contain_any_characters`

```python
def test_documents_may_contain_any_characters():
    """A title of 1-200 characters and content of at most 100000 characters are accepted whatever they contain."""
    svc, _, _ = make()
    tok = user(svc)
    title, content = "\ud800x\u00e9\u4e2d", "\udfff\n\t\u0000z"
    d = create(svc, tok, title, content)
    out = svc.get_document(tok, d)
    assert out[0] == 200 and out[1]["title"] == title and out[1]["content"] == content, \
        f"input={(title, content)!r} output={out!r}"
```

## run 0, ABp
### O3 (is a key used by a rejected request)

- test `test_phase_b::test_invalid_payment_amounts_and_idempotency_conflicts_do_not_charge_or_record`

```python
def test_invalid_payment_amounts_and_idempotency_conflicts_do_not_charge_or_record():
    """Invalid payment amounts and same-key different-amount retries must not create recorded payments or extra charges."""
    from solution import Service

    clock = ManualClock()
    gateway = RecordingGateway()
    service = Service(clock, gateway)
    token = register_and_login(service)

    for amount in [-1, 0, 1000001, "100"]:
        out = service.pay(token, amount, "invalid-amount")
        assert_status(out, 400, ("pay", amount, "invalid-amount"))

    assert gateway.calls == [], f"input='invalid amounts' output={gateway.calls!r}"

    out = service.list_payments(token)
    assert_status(out, 200, ("list_payments", "after invalid amounts"))
    assert out[1] == [], f"input='after invalid amounts' output={out!r}"

    out = service.pay(token, 10, "same-key")
    assert_status(out, 201, ("pay", 10, "same-key"))
    payment = out[1]

    calls_after_success = list(gateway.calls)
    out = service.pay(token, 11, "same-key")
    assert_status(out, 409, ("pay", 11, "same-key"))

    assert gateway.calls == calls_after_success, (
        f"input=('conflict', 11, 'same-key') output={gateway.calls!r}"
    )

    out = service.list_payments(token)
    assert_status(out, 200, ("list_payments", "after conflict"))
    assert out[1] == [payment], f"input='after conflict' output={out!r}"
```

## run 1, A
### O2 (case folding beyond ASCII)

- open question: Is case-insensitivity defined for non-ASCII text? The tests use ASCII only.

### O4 (empty idempotency key)

- open question: What are the key and type rules for `idempotency_key` (empty or non-string), `page_size` and `amount_cents` (bool, float 5.0)? The tests use only plain non-empty string keys, ints, and clearly non-integer amounts (1.5, "100").

## run 1, B
### O3 (is a key used by a rejected request)

- test `test_phase_b::test_failed_validation_does_not_burn_key`

```python
def test_failed_validation_does_not_burn_key():
    """A pay rejected with 400 for a bad amount does not prevent later use of the key."""
    svc, _, _ = make()
    tok = user(svc)
    assert svc.pay(tok, 0, "k")[0] == 400
    s, p = svc.pay(tok, 5, "k")
    assert s == 201 and p["amount_cents"] == 5, f"output={(s, p)!r}"
```

## run 1, AB
### O2 (case folding beyond ASCII)

- open question: Case-insensitivity for non-ASCII text (casefold vs lower) is unspecified, so the tests use ASCII only.
- test `test_phase_b::test_username_with_trailing_newline_or_non_ascii_is_rejected`

```python
def test_username_with_trailing_newline_or_non_ascii_is_rejected():
    """A username must consist only of [a-z0-9_]; trailing newlines and non-ASCII letters or digits give 400."""
    svc, _, _ = make()
    for name in ["abc\n", "ab\n", "\nabc", "ａｂｃ", "١٢٣", "abc\x00", "a\tb"]:
        out = svc.register(name, "password1")
        assert out[0] == 400, f"input={name!r} output={out!r}"
    out = svc.login("abc", "password1")
    assert out[0] == 401, f"input='abc' output={out!r}"
    out = svc.register("abc", "password1")
    assert out[0] == 201, f"input='abc' output={out!r}"
```
- test `test_phase_b::test_unicode_and_whitespace_length_boundaries`

```python
def test_unicode_and_whitespace_length_boundaries():
    """Titles and content are measured in characters: a single space is a valid title, 200 and 100000 characters are accepted and one more is not."""
    svc, _, _ = make()
    tok = user(svc)
    cases = [(" ", "", 201), ("é" * 200, "é", 201), ("é" * 201, "é", 400),
             ("t", "😀" * 100000, 201), ("t", "😀" * 100001, 400), ("\n", "\n", 201)]
    for title, content, exp in cases:
        out = svc.create_document(tok, title, content)
        assert out[0] == exp, f"input={(len(title), len(content))!r} output={out!r}"
```

### O4 (empty idempotency key)

- open question: Non-string or non-integer types for inputs (`bool` amounts, float amounts, non-string titles, non-string queries) and empty or non-string idempotency keys are unspecified and not tested.

## run 2, A
### O2 (case folding beyond ASCII)

- open question: Unicode case folding for search is unspecified, so search tests use ASCII only.

## run 2, B
### O2 (case folding beyond ASCII)

- test `test_phase_b::test_register_username_charset`

```python
def test_register_username_charset():
    """A username with characters outside [a-z0-9_] (uppercase, newline, symbols, non-ASCII) gives 400."""
    svc, _, _ = make()
    for name in ["ABC", "abC", "abc\n", "a b", "a-b", "ab\u00e7", "abc!", "\nabc", "abc "]:
        out = svc.register(name, "password1")
        assert out[0] == 400, f"input={name!r} output={out!r}"
    out = svc.register("a_1", "password1")
    assert out[0] == 201, f"input='a_1' output={out!r}"
```

## run 2, AB
### O2 (case folding beyond ASCII)

- test `test_phase_b::test_usernames_with_other_characters_are_rejected` **[false oracle]** **[still fails on final]**

```python
def test_usernames_with_other_characters_are_rejected(name):
    """A username containing any character outside [a-z0-9_] (including newline or non-ASCII letters) gives 400."""
    svc, _, _ = make()
    out = svc.register(name, "password1")
    assert out[0] == 400, f"input={name!r} output={out!r}"
```
- test `test_phase_b::test_title_and_content_lengths_count_characters`

```python
def test_title_and_content_lengths_count_characters():
    """Title and content limits are in characters, so 200 non-ASCII characters are valid and 201 are not."""
    svc, _, _ = make()
    tok = user(svc)
    assert svc.create_document(tok, "😀" * 200, "é" * 100000)[0] == 201, "input=200/100000 chars output=not 201"
    out = svc.create_document(tok, "😀" * 201, "x")
    assert out[0] == 400, f"input=201 chars output={out!r}"
    out = svc.create_document(tok, "t", "é" * 100001)
    assert out[0] == 400, f"input=100001 chars output={out!r}"
```

### O3 (is a key used by a rejected request)

- test `test_phase_b::test_invalid_amount_has_no_effect_on_a_later_valid_payment_with_same_key`

```python
def test_invalid_amount_has_no_effect_on_a_later_valid_payment_with_same_key():
    """A rejected (400) pay does not consume the idempotency key, so the same key can later be used with a valid amount."""
    svc, _, gw = make()
    tok = user(svc)
    for bad in (0, 1000001, -1, True, 2.0, "5"):
        out = svc.pay(tok, bad, "k")
        assert out[0] == 400, f"input={bad!r} output={out!r}"
    assert gw.calls == [], f"output=gateway called {gw.calls!r}"
    out = svc.pay(tok, 5, "k")
    assert out[0] == 201 and out[1]["amount_cents"] == 5, f"input=(5,'k') output={out!r}"
```
- test `test_phase_b_mutants::test_property_pay_rejects_arbitrary_unissued_tokens_with_401`

```python
def test_property_pay_rejects_arbitrary_unissued_tokens_with_401(token, amount, key):
    """pay with any token string that was never issued returns 401 and has no effect."""
    svc, clock, gw = setup(ttl=3600)
    valid = login(svc)
    if token == valid:
        return
    out = svc.pay(token, amount, key)
    assert out[0] == 401, f"input={(token, amount, key)!r} output={out!r}"
    assert gw.calls == [], f"input={(token, amount, key)!r} output=gateway calls {gw.calls!r}"
    assert svc.list_payments(valid) == (200, []), f"input={(token, amount, key)!r} output=payment recorded"
```

### O4 (empty idempotency key)

- open question: Behavior for a `bool` or non-`int` numeric amount such as `5.0`, and for empty idempotency keys, is unspecified.

### O5 (unencodable characters)

- test `test_phase_b::test_password_with_lone_surrogates_is_a_valid_password` **[still fails on final]**

```python
def test_password_with_lone_surrogates_is_a_valid_password():
    """Any string of at least 8 characters is a valid password, so registration and login must not fail on unusual characters."""
    svc, _, _ = make()
    pw = "\ud800" * 8
    out = svc.register("alice", pw)
    assert out[0] == 201, f"input={pw!r} output={out!r}"
    out = svc.login("alice", pw)
    assert out[0] == 200, f"input={pw!r} output={out!r}"
```

## run 2, ABp
### O3 (is a key used by a rejected request)

- test `test_phase_a::test_payments_validation_idempotency_scoping_timeouts_and_listing` **[false oracle]**

```python
def test_payments_validation_idempotency_scoping_timeouts_and_listing():
    """Payments must validate amounts, record successful charges in creation order, scope idempotency keys to the caller, and safely retry timed-out attempts."""
    clock = FakeClock(10.0)
    gateway = FakeGateway()
    service = make_service(clock=clock, gateway=gateway)
    register_user(service, "alice")
    register_user(service, "bob")
    alice = login_user(service, "alice")
    bob = login_user(service, "bob")

    for amount in [0, -1, 1000001, 1.5, "10"]:
        out = service.pay(alice, amount, "invalid-amount-key")
        assert out[0] == 400, f"input={(alice, amount, 'invalid-amount-key')!r} output={out!r}"

    out = service.list_payments(alice)
    assert out[0] == 200, f"input={alice!r} output={out!r}"
    assert out[1] == [], f"input={alice!r} output={out!r}"

    out = service.pay(alice, 123, "key-1")
    assert out[0] == 201, f"input={(alice, 123, 'key-1')!r} output={out!r}"
    first_payment = out[1]
    assert_payment(first_payment, {"amount_cents": 123, "idempotency_key": "key-1", "created_at": 10.0}, ("alice", 123, "key-1"))

    out = service.pay(alice, 123, "key-1")
    assert out[0] == 200, f"input={(alice, 123, 'key-1')!r} output={out!r}"
    assert out[1] == first_payment, f"input={(alice, 123, 'key-1')!r} output={out!r}"

    out = service.pay(alice, 124, "key-1")
    assert out[0] == 409, f"input={(alice, 124, 'key-1')!r} output={out!r}"

    out = service.list_payments(al
```
- test `test_phase_b::test_payment_timeout_key_rejects_different_amount_and_invalid_amount_does_not_use_key`

```python
def test_payment_timeout_key_rejects_different_amount_and_invalid_amount_does_not_use_key():
    """A timed-out payment attempt must record no payment, reserve the idempotency key for only the same amount, and an invalid amount must not consume the key."""
    service = make_service(clock=FakeClock(5.0), gateway=RecordingGateway())
    register_user(service)
    token = login_user(service)

    out = service.pay(token, 0, "later-valid")
    assert out[0] == 400, f"input={(token, 0, 'later-valid')!r} output={out!r}"

    out = service.pay(token, 10, "later-valid")
    assert out[0] == 201, f"input={(token, 10, 'later-valid')!r} output={out!r}"

    clock = FakeClock(10.0)
    gateway = TimeoutThenSuccessGateway(timeout_count=1)
    timeout_service = make_service(clock=clock, gateway=gateway)
    register_user(timeout_service, "bob")
    bob = login_user(timeout_service, "bob")

    out = timeout_service.pay(bob, 500, "retry-key")
    assert out[0] == 504, f"input={(bob, 500, 'retry-key', 'timeout')!r} output={out!r}"

    out = timeout_service.list_payments(bob)
    assert out[0] == 200, f"input={bob!r} output={out!r}"
    assert out[1] == [], f"input={bob!r} output={out!r}"

    out = timeout_service.pay(bob, 501, "retry-key")
    assert out[0] == 409, f"input={(bob, 501, 'retry-key')!r} output={out!r}"
    assert len(gateway.effective_charges) == 1, f"input={(bob, 'after-conflict')!r} output={gateway.effective_charges!r}"

    clock.set(20.0)
    out = timeout_service.pay(bo
```

## run 3, A
### O3 (is a key used by a rejected request)

- open question: Precedence between 400 validation, 401 auth, and 404 is not defined for combined failures (e.g. bad `page_size` with a bad token, an invalid title on a nonexistent document, an invalid amount with a reused key). Not tested.

## run 3, AB
### O2 (case folding beyond ASCII)

- test `test_phase_b::test_password_length_counts_characters_not_bytes`

```python
def test_password_length_counts_characters_not_bytes():
    """A password of 8 non-ASCII characters must be accepted and one of 7 rejected with 400."""
    svc, _, _ = make()
    cases = (("userone", "\u00e9" * 8, 201), ("usertwo", "\u00e9" * 7, 400),
             ("userthree", "\U0001F600" * 8, 201), ("userfour", "\U0001F600" * 7, 400),
             ("userfive", "\u65e5\u672c\u8a9e" * 3, 201))
    for name, pw, exp in cases:
        r = svc.register(name, pw)
        assert r[0] == exp, f"input={(name, pw)!r} output={r!r}"
    r = svc.login("userthree", "\U0001F600" * 8)
    assert r[0] == 200, f"output={r!r}"
    r = svc.login("userthree", "\U0001F600" * 7 + "x")
    assert r[0] == 401, f"output={r!r}"
```

### O3 (is a key used by a rejected request)

- test `test_phase_b::test_invalid_amount_with_new_key_does_not_consume_the_key`

```python
def test_invalid_amount_with_new_key_does_not_consume_the_key():
    """A pay rejected with 400 for its amount must record nothing, so the same key can later be used with a valid amount for a 201."""
    svc, _, gw = make()
    tok = signup(svc)
    assert svc.pay(tok, 0, "k")[0] == 400
    assert svc.pay(tok, 1000001, "k")[0] == 400
    r = svc.pay(tok, 250, "k")
    assert r[0] == 201 and r[1]["amount_cents"] == 250, f"output={r!r}"
    assert list(gw.charged.values()) == [250], f"charged={gw.charged!r}"
```

### O4 (empty idempotency key)

- open question: Types such as `bool` or integral floats for the amount, empty or non-string idempotency keys, and non-string titles or content are not specified.

### O5 (unencodable characters)

- test `test_phase_b::test_password_with_lone_surrogates_is_accepted`

```python
def test_password_with_lone_surrogates_is_accepted():
    """A password of at least 8 characters must be accepted with 201 and usable for login whatever characters it contains."""
    svc, _, _ = make()
    pw = "\ud800" * 8
    try:
        r = svc.register("alice", pw)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"input={pw!r} raised {e!r}")
    assert r[0] == 201, f"input={pw!r} output={r!r}"
    try:
        r = svc.login("alice", pw)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"login input={pw!r} raised {e!r}")
    assert r[0] == 200, f"input={pw!r} output={r!r}"
```
- test `test_phase_b::test_login_with_lone_surrogate_password_is_401_not_error`

```python
def test_login_with_lone_surrogate_password_is_401_not_error():
    """Login with an incorrect password must return 401 whatever characters the password contains."""
    svc, _, _ = make()
    svc.register("alice", "password1")
    pw = "\ud800" * 8
    try:
        r = svc.login("alice", pw)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"input={pw!r} raised {e!r}")
    assert r[0] == 401, f"input={pw!r} output={r!r}"
```
- test `test_phase_b::test_title_and_content_lengths_count_characters`

```python
def test_title_and_content_lengths_count_characters():
    """Title and content limits must count characters, so 200 emoji are a valid title and 201 are not."""
    svc, _, _ = make()
    tok = signup(svc)
    emoji = "\U0001F600"
    for title, content, exp in ((emoji * 200, "", 201), (emoji * 201, "", 400),
                                ("t", "\u00e9" * 100000, 201), ("t", "\u00e9" * 100001, 400)):
        r = svc.create_document(tok, title, content)
        assert r[0] == exp, f"input_lens={(len(title), len(content))!r} output={r!r}"
```

## run 3, ABp
### O3 (is a key used by a rejected request)

- test `test_phase_a::test_payment_validation_and_idempotency_conflict_do_not_create_new_payment`

```python
def test_payment_validation_and_idempotency_conflict_do_not_create_new_payment():
    """Invalid payment amounts must return 400 and same-key different-amount retries must return 409 without recording a new payment."""
    gateway = FakeGateway()
    service, _clock, gateway = make_service(gateway=gateway)
    token = register_and_login(service, "alice", "password123")

    invalid_amounts = [0, -1, 1000001, "100"]
    for amount in invalid_amounts:
        out = service.pay(token, amount, f"bad-{amount}")
        assert_status(out, 400, {"method": "pay", "amount_cents": amount})

    assert gateway.calls == [], f"input={{'method': 'pay', 'invalid_amounts': {invalid_amounts!r}}} output={gateway.calls!r}"

    out = service.pay(token, 100, "same-key")
    payment = assert_status(out, 201, {"method": "pay", "amount_cents": 100, "idempotency_key": "same-key"})

    out = service.pay(token, 101, "same-key")
    assert_status(out, 409, {"method": "pay", "amount_cents": 101, "idempotency_key": "same-key"})

    out = service.list_payments(token)
    payments = assert_status(out, 200, {"method": "list_payments"})
    assert payments == [payment], f"input={{'method': 'list_payments', 'after_conflict': True}} output={payments!r}"
    assert len(gateway.charges) == 1, (
        f"input={{'method': 'pay', 'conflicting_retry': True}} output={{'charges': {gateway.charges!r}, 'calls': {gateway.calls!r}}}"
    )
```

## run 4, A
### O2 (case folding beyond ASCII)

- open question: Case-insensitivity for non-ASCII text is not specified. Search tests use ASCII only.

### O3 (is a key used by a rejected request)

- open question: Whether a rejected `pay` (400) consumes its idempotency key is not specified. Whether an empty or odd idempotency key is valid is not specified either.

### O4 (empty idempotency key)

- open question: Whether a rejected `pay` (400) consumes its idempotency key is not specified. Whether an empty or odd idempotency key is valid is not specified either.

## run 4, B
### O2 (case folding beyond ASCII)

- test `test_phase_b::test_register_password_length_boundary`

```python
def test_register_password_length_boundary():
    """A password of at least 8 characters is accepted and 7 characters gives 400."""
    svc = Service(Clock(), FakeGateway())
    out7 = svc.register("user1", "1234567")
    assert out7[0] == 400, f"input=7-char output={out7!r}"
    assert svc.login("user1", "1234567")[0] == 401, "rejected registration must not create user"
    out8 = svc.register("user1", "12345678")
    assert out8[0] == 201, f"input=8-char output={out8!r}"
    out = svc.register("user2", "é" * 8)
    assert out[0] == 201, f"input=8 non-ascii chars output={out!r}"
```

### O3 (is a key used by a rejected request)

- test `test_phase_b::test_rejected_amount_does_not_consume_idempotency_key`

```python
def test_rejected_amount_does_not_consume_idempotency_key():
    """A pay rejected with 400 does not use up its key; the key can later be used with a valid amount."""
    svc, _, _, (tok,) = make()
    assert svc.pay(tok, 0, "k")[0] == 400
    out = svc.pay(tok, 700, "k")
    assert out[0] == 201 and out[1]["amount_cents"] == 700, f"output={out!r}"
```
- test `test_phase_b::test_key_used_in_timed_out_attempt_rejects_different_amount`

```python
def test_key_used_in_timed_out_attempt_rejects_different_amount():
    """A key already used by a timed-out attempt with one amount gives 409 for a different amount and never charges twice."""
    svc, _, gw, (tok,) = make()
    gw.fail_next = "after"
    assert svc.pay(tok, 100, "k")[0] == 504
    out = svc.pay(tok, 200, "k")
    assert out[0] == 409, f"output={out!r}"
    assert svc.list_payments(tok) == (200, [])
    assert sorted(gw.charged.values()) == [100], f"charged={gw.charged!r}"
```

### O4 (empty idempotency key)

- test `test_phase_b_mutants::test_pay_empty_key_with_valid_token_is_not_401`

```python
def test_pay_empty_key_with_valid_token_is_not_401():
    """401 is reserved for bad tokens, so pay with a valid token never returns 401."""
    svc, tok = make()
    out = svc.pay(tok, 100, "")
    assert out[0] in (201, 400), f"input=(100, '') output={out!r}"
```
- test `test_phase_b_mutants::test_property_pay_empty_key_never_401`

```python
def test_property_pay_empty_key_never_401(amount):
    """With a valid token and a valid amount, pay does not return 401 whatever the key."""
    svc, tok = make()
    out = svc.pay(tok, amount, "")
    assert out[0] in (201, 400), f"input=({amount!r}, '') output={out!r}"
```

### O5 (unencodable characters)

- test `test_phase_b_mutants::test_login_with_unencodable_wrong_password_is_401`

```python
def test_login_with_unencodable_wrong_password_is_401():
    """Login with anything other than the correct credentials returns 401, including a password of lone surrogates."""
    svc, _ = make()
    pw = "\ud800" * 8
    out = svc.login("alice", pw)
    assert out == (401, None), f"input={pw!r} output={out!r}"
```
- test `test_phase_b_mutants::test_property_login_with_surrogate_password_is_401`

```python
def test_property_login_with_surrogate_password_is_401(pw):
    """Login with a password that is not the registered one returns 401, whatever characters it contains."""
    svc, _ = make()
    out = svc.login("alice", pw)
    assert out == (401, None), f"input={pw!r} output={out!r}"
```
- test `test_phase_b_mutants::test_register_with_surrogate_password_status_is_specified`

```python
def test_register_with_surrogate_password_status_is_specified():
    """Register returns only 201, 400 or 409, even for an 8-character password of lone surrogates."""
    svc = Service(Clock(), Gateway())
    pw = "\ud800" * 8
    out = svc.register("carol", pw)
    assert out[0] in (201, 400), f"input={pw!r} output={out!r}"
```

## run 4, AB
### O2 (case folding beyond ASCII)

- open question: Case folding for non-ASCII text in search is unspecified, so only ASCII is tested.

### O3 (is a key used by a rejected request)

- open question: Precedence between 401, 400, 404, and 409 when several apply is not specified (for example an invalid token plus invalid input, an update of a missing document with an invalid title, or an invalid amount with an already-used key). Such combinations are not tested. The only exception is 401 for bad tokens, which is stated to apply for every method and is tested with otherwise valid inputs.
- test `test_phase_b::test_pay_amount_invalid_types_and_values_leave_no_trace`

```python
def test_pay_amount_invalid_types_and_values_leave_no_trace():
    """An amount that is not an integer from 1 to 1,000,000 must give 400 and cause no charge and no recorded payment."""
    svc, _, gw = make()
    tok = user(svc)
    for amount in (0, -5, 1000001, 10 ** 9, 12.5, "5", None):
        out = svc.pay(tok, amount, "k")
        assert out[0] == 400, f"input={amount!r} output={out!r}"
    assert gw.charged == {} and gw.calls == 0, f"output={gw.charged!r} calls={gw.calls!r}"
    assert svc.list_payments(tok) == (200, [])
    ok = svc.pay(tok, 10, "k")
    assert ok[0] == 201, f"input=key reuse after 400s output={ok!r}"
```
- test `test_phase_b::test_failed_attempts_with_409_and_400_do_not_disturb_original_payment`

```python
def test_failed_attempts_with_409_and_400_do_not_disturb_original_payment():
    """After a 409 or 400 for a used key the original payment must still be returned unchanged by retry and list."""
    svc, _, gw = make()
    tok = user(svc)
    first = svc.pay(tok, 40, "k")
    assert svc.pay(tok, 41, "k")[0] == 409
    assert svc.pay(tok, 0, "k")[0] in (400, 409)  # precedence unspecified; only state is checked below
    again = svc.pay(tok, 40, "k")
    assert again == (200, first[1]), f"output={again!r}"
    assert svc.list_payments(tok) == (200, [first[1]])
    assert list(gw.charged.values()) == [40], f"output={gw.charged!r}"
```

### O4 (empty idempotency key)

- open question: The empty idempotency key, the payment id format and uniqueness, and `created_at` for a payment completed on retry after a 504 are all unspecified. None is tested.

### O5 (unencodable characters)

- test `test_phase_b::test_password_with_lone_surrogates_is_accepted_by_length` **[still fails on final]**

```python
def test_password_with_lone_surrogates_is_accepted_by_length():
    """A password of at least 8 characters must be accepted by register and work for login, whatever its characters."""
    svc, _, _ = make()
    pw = "\ud800" * 8
    r = svc.register("surr", pw)
    assert r[0] == 201, f"input={pw!r} output={r!r}"
    l = svc.login("surr", pw)
    assert l[0] == 200, f"input={pw!r} output={l!r}"
    bad = svc.login("surr", "\ud801" * 8)
    assert bad[0] == 401, f"input=other surrogate password output={bad!r}"
```
- test `test_phase_b::test_prop_surrogate_passwords_of_valid_length_register_and_login` **[still fails on final]**

```python
def test_prop_surrogate_passwords_of_valid_length_register_and_login(pw):
    """Any password of at least 8 characters must register with 201 and then log in with 200."""
    svc, _, _ = make()
    r = svc.register("surr", pw)
    assert r[0] == 201, f"input={pw!r} output={r!r}"
    l = svc.login("surr", pw)
    assert l[0] == 200, f"input={pw!r} output={l!r}"
```
- test `test_phase_b_mutants::test_login_with_unencodable_wrong_password_gives_401`

```python
def test_login_with_unencodable_wrong_password_gives_401():
    """Login with a password that differs from the registered one must return 401, whatever its characters."""
    svc = _svc()
    assert svc.register("sam", PW)[0] == 201
    bad = "\ud800" * 8
    out = svc.login("sam", bad)
    assert out[0] == 401, f"input={bad!r} output={out!r}"
    out = svc.login("sam", "\udfff")
    assert out[0] == 401, f"input='\\udfff' output={out!r}"
    ok = svc.login("sam", PW)
    assert ok[0] == 200, f"input=correct password output={ok!r}"
```
- test `test_phase_b_mutants::test_prop_login_with_surrogate_password_never_succeeds_for_ordinary_account`

```python
def test_prop_login_with_surrogate_password_never_succeeds_for_ordinary_account(pw):
    """Login with any password different from the registered one must return 401."""
    svc = _svc()
    assert svc.register("tess", PW)[0] == 201
    out = svc.login("tess", pw)
    assert out[0] == 401, f"input={pw!r} output={out!r}"
```

## run 4, ABp
### O4 (empty idempotency key)

- test `test_phase_b_mutants::test_empty_string_is_a_caller_scoped_idempotency_key_for_payment`

```python
def test_empty_string_is_a_caller_scoped_idempotency_key_for_payment():
    """A payment with a valid token and valid amount must treat the supplied idempotency key, including an empty string key, as caller-scoped."""
    from solution import Service

    clock = ManualClock(start=10.0)
    gateway = RecordingGateway()
    service = Service(clock, gateway)
    token = register_and_login(service)

    inp = ("pay", token, 123, "")
    payment = expect_status(service.pay(token, 123, ""), 201, inp)
    assert payment["amount_cents"] == 123, f"input={inp!r} output={payment!r}"
    assert payment["idempotency_key"] == "", f"input={inp!r} output={payment!r}"
    assert payment["created_at"] == 10.0, f"input={inp!r} output={payment!r}"

    inp = ("pay retry same amount", token, 123, "")
    retry = expect_status(service.pay(token, 123, ""), 200, inp)
    assert retry == payment, f"input={inp!r} output={retry!r}"

    inp = ("pay retry different amount", token, 124, "")
    expect_status(service.pay(token, 124, ""), 409, inp)

    inp = ("list_payments", token)
    payments = expect_status(service.list_payments(token), 200, inp)
    assert payments == [payment], f"input={inp!r} output={payments!r}"
    assert gateway.charge_count == 1, f"input={inp!r} output={gateway.charge_count!r}"
```

### O5 (unencodable characters)

- test `test_phase_b_mutants::test_register_returns_only_declared_registration_status_codes`

```python
def test_register_returns_only_declared_registration_status_codes():
    """Register must return only one of its specified statuses: 201, 400, or 409."""
    from solution import Service

    service = Service(ManualClock(), RecordingGateway())
    password = "\ud800" * 8

    inp = ("register", "alice", password)
    expect_status(service.register("alice", password), {201, 400, 409}, inp)
```
