# Type O coding: excerpts (keyword candidates, to confirm)

Reference behavior on the probes: {'O2': (200, 0), 'O3': (400, 201), 'O4': 201, 'O5': 201}

Intent R: O1: no admin role; O2: casefold; O3: a rejected request does not consume the key; O4: empty key gives 400; O5: always return a status, never raise


## run 0, SV


## run 0, A


### O4 (empty idempotency key)

- open question: The validity of idempotency keys (empty or non-string) and of non-integer, bool, or non-string arguments is not defined, so these are not tested.

## run 0, B


### O3 (is a key used by a rejected request)

- test `test_phase_b::test_conflict_with_invalid_amount_is_400_not_conflict`

```python
def test_conflict_with_invalid_amount_is_400_not_conflict():
    """An out-of-range amount is rejected with 400 even when the key was already used."""
    svc, _, _ = mk()
    tok = user(svc)
    svc.pay(tok, 500, "key")
    out = svc.pay(tok, 0, "key")
    assert out[0] == 400, f"output={out!r}"
```

## run 0, AB


### O2 (case folding beyond ASCII)

- open question: Unicode case folding for search is unspecified, so I use ASCII only.
- test `test_phase_b::test_password_length_counts_characters` **[false oracle]** **[still fails on final]**

```python
def test_password_length_counts_characters(n, expected):
    """A password must have at least 8 characters, counted as characters and not bytes."""
    svc, _, _ = make()
    pw = "\u00e9" * n
    r = svc.register("validname", pw)
    assert r[0] == expected, f"input=password of {n} e-acute output={r!r}"
    if expected == 201:
        lr = svc.login("validname", pw)
        assert lr[0] == 200, f"input=login with unicode password output={lr!r}"
```

### O3 (is a key used by a rejected request)

- test `test_phase_b::test_invalid_amount_rejected_without_side_effects`

```python
def test_invalid_amount_rejected_without_side_effects(amount):
    """An amount outside 1 to 1,000,000 must give 400, charge nothing and record nothing."""
    svc, _, gw = make()
    tok = new_user(svc)
    r = svc.pay(tok, amount, "k")
    assert r[0] == 400, f"input=amount={amount!r} output={r!r}"
    assert gw.charges == {}, f"input=amount={amount!r} output=charges {gw.charges!r}"
    lp = svc.list_payments(tok)
    assert lp[0] == 200 and lp[1] == [], f"input=amount={amount!r} output={lp!r}"
    ok = svc.pay(tok, 5, "k")
    assert ok[0] == 201, f"input=valid pay with same key after rejected output={ok!r}"
```

### O4 (empty idempotency key)

- open question: Non-string and non-integer inputs (`bool`, `5.0`, and so on) and the validity of `idempotency_key` values (empty or very long) are unspecified.

## run 0, ABp


### O2 (case folding beyond ASCII)

- test `test_phase_b::test_register_accepts_boundary_usernames_and_arbitrary_long_unicode_passwords`

```python
def test_register_accepts_boundary_usernames_and_arbitrary_long_unicode_passwords():
    """Register must accept usernames at the 3-character and 32-character boundaries and any password of at least 8 characters."""
    service = Service(FakeClock(), RecordingGateway())

    cases = [
        ("abc", "密码密码密码密码"),
        ("u" * 32, "pässwörd😊"),
    ]
    for username, password in cases:
        inp = ("register boundary", username, password, len(password))
        out = service.register(username, password)
        assert_status(out, 201, inp)

        inp = ("login boundary", username, password)
        out = service.login(username, password)
        body = assert_status(out, 200, inp)
        assert isinstance(body, dict) and isinstance(body.get("token"), str), (
            f"input={inp!r} output={out!r}"
        )
```

## run 1, SV


## run 1, A


## run 1, B


## run 1, AB


### O2 (case folding beyond ASCII)

- open question: Case folding for non-ASCII text in search is unspecified.
- test `test_phase_b::test_username_with_characters_outside_class_is_rejected` **[false oracle]** **[still fails on final]**

```python
def test_username_with_characters_outside_class_is_rejected(name):
    """A username containing any character outside [a-z0-9_] (including a trailing newline or non-ASCII letters and digits) is rejected with 400."""
    svc, _, _ = make()
    out = svc.register(name, "password1")
    assert out[0] == 400, f"input={name!r} output={out!r}"
    out = svc.login(name, "password1")
    assert out[0] == 401, f"input={name!r} (login) output={out!r}"
```

### O4 (empty idempotency key)

- open question: Constraints on idempotency keys (empty or very long) are unspecified.

## run 1, ABp


### O4 (empty idempotency key)

- test `test_phase_b_mutants::test_pay_with_empty_idempotency_key_returns_only_a_specified_pay_status`

```python
def test_pay_with_empty_idempotency_key_returns_only_a_specified_pay_status():
    """The pay method must return only one of the statuses specified for pay for every in-process call."""
    from solution import Service

    service = Service(FakeClock(0.0), RecordingGateway())
    token = register_and_login(service)
    allowed_statuses = {200, 201, 400, 401, 409, 504}

    out = service.pay(token, 1, "")
    assert out[0] in allowed_statuses, f"input={(token, 1, '')!r} output={out!r}"
```

## run 2, SV


## run 2, A


### O2 (case folding beyond ASCII)

- open question: Validation of non-string titles, usernames, or keys, of non-integer `page_size`, and of float amounts such as `10.0` is not specified. Case-folding of non-ASCII text is also not specified. Tests use ASCII text and non-integer amounts like `1.5` and `"100"`.

## run 2, B


### O3 (is a key used by a rejected request)

- test `test_phase_b::test_invalid_amount_does_not_consume_key`

```python
def test_invalid_amount_does_not_consume_key():
    """A rejected (400) payment records nothing, so the key can still be used."""
    svc, _, _ = make()
    tok = user(svc)
    assert svc.pay(tok, 0, "k")[0] == 400
    assert svc.pay(tok, 5, "k")[0] == 201
```

### O4 (empty idempotency key)

- test `test_phase_b_mutants::test_empty_idempotency_key_with_valid_token_is_not_401`

```python
def test_empty_idempotency_key_with_valid_token_is_not_401():
    """401 is reserved for bad tokens, so pay with a valid token and an empty key must not return 401."""
    svc, _, _ = make()
    tok = user(svc)
    out = svc.pay(tok, 100, "")
    assert out[0] in (201, 400), f"input=(100, '') output={out!r}"
```

## run 2, AB


### O2 (case folding beyond ASCII)

- open question: Non-integer amounts (floats, strings, bools), non-string arguments, and Unicode case-folding for search are unspecified.
- test `test_phase_b::test_username_with_newline_unicode_or_whitespace_is_rejected` **[false oracle]** **[still fails on final]**

```python
def test_username_with_newline_unicode_or_whitespace_is_rejected(name):
    """A username must consist only of characters from [a-z0-9_], so newlines, NUL and non-ASCII digits give 400."""
    svc, _, _ = make()
    out = svc.register(name, "password1")
    assert out[0] == 400, f"input={name!r} output={out!r}"
```

### O3 (is a key used by a rejected request)

- test `test_phase_b::test_rejected_amount_does_not_consume_the_idempotency_key`

```python
def test_rejected_amount_does_not_consume_the_idempotency_key():
    """A pay rejected with 400 records nothing, so the key can then be used with a different valid amount."""
    svc, _, gw = make()
    tok = user(svc)
    assert svc.pay(tok, 0, "k")[0] == 400
    assert svc.pay(tok, 1_000_001, "k")[0] == 400
    s, p = svc.pay(tok, 250, "k")
    assert s == 201 and p["amount_cents"] == 250, f"output={(s, p)!r}"
    assert list(gw.charged.values()) == [250], f"charged={gw.charged!r}"
```

### O4 (empty idempotency key)

- open question: The idempotency-key format is unspecified, including empty keys. Tests use non-empty ASCII keys.

## run 2, ABp

