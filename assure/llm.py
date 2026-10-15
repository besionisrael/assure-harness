"""LLM backends. Each backend exposes complete(system, messages, meta) and
returns (text, usage). `meta` carries the role and task context; real
backends ignore it, the mock backend uses it to simulate agents offline."""
import os
import random
import re
import time


class Backend:
    name = "abstract"

    def complete(self, system, messages, meta):
        raise NotImplementedError


def _retry(call, attempts=6):
    delay = 5
    for i in range(attempts):
        try:
            return call()
        except Exception as e:  # noqa: BLE001
            transient = any(s in type(e).__name__ for s in
                            ("RateLimit", "Timeout", "Connection", "InternalServer", "Overloaded",
                             "APIStatus", "ServiceUnavailable"))
            if not transient or i == attempts - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 120)


DEFAULT_MAX_TOKENS = 64000   # thinking/reasoning tokens count against this limit


class IncompleteResponse(RuntimeError):
    """The model stopped before producing a usable answer (output limit reached,
    refusal, or no text). Raised so that the unit fails visibly instead of
    continuing with empty evidence."""

    def __init__(self, message, text="", usage=None):
        super().__init__(message)
        self.text, self.usage = text, usage or {}


def _check_complete(name, text, stop, usage):
    if stop in ("max_tokens", "length", "refusal") or not text.strip():
        raise IncompleteResponse(f"{name}: stop={stop} text_chars={len(text)} usage={usage}",
                                 text, usage)


class ReplayMismatch(RuntimeError):
    """A rerun diverged from the recorded calls it was replaying."""


class Replay:
    """Responses already obtained, and paid for, in an interrupted run of the
    same unit, served back in order. The unit restarts from the beginning, and
    each call must match the recorded one exactly (backend, role, condition,
    phase, prompt), otherwise the rerun stops. Once the record is exhausted,
    calls go to the real backends. Incomplete responses are never replayed."""

    def __init__(self, entries):
        self.entries = [e for e in entries if not e.get("incomplete")]
        self.pos = 0

    def wrap(self, backend):
        return _Replaying(backend, self)


class _Replaying(Backend):
    def __init__(self, inner, replay):
        self.inner, self.replay, self.name = inner, replay, inner.name

    def complete(self, system, messages, meta):
        r = self.replay
        if r.pos >= len(r.entries):
            return self.inner.complete(system, messages, meta)
        e = r.entries[r.pos]
        got = (self.name, meta["role"], meta.get("condition"), meta.get("phase"))
        exp = (e["backend"], e["role"], e["condition"], e["phase"])
        if got != exp or messages[-1]["content"] != e["prompt"]:
            what = "prompt differs" if got == exp else f"expected {exp}, got {got}"
            raise ReplayMismatch(f"replayed call {r.pos}: {what}")
        r.pos += 1
        return e["response"], dict(e["usage"], replayed=True)


class AnthropicBackend(Backend):
    def __init__(self, model, max_tokens=DEFAULT_MAX_TOKENS, temperature=None,
                 api_key_env="ANTHROPIC_API_KEY"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ.get(api_key_env))
        self.model, self.max_tokens, self.temperature = model, max_tokens, temperature
        self.name = f"anthropic:{model}"

    def _stream(self, kwargs):
        # streaming avoids HTTP timeouts on large max_tokens
        with self.client.messages.stream(**kwargs) as stream:
            return stream.get_final_message()

    def complete(self, system, messages, meta):
        kwargs = dict(model=self.model, max_tokens=self.max_tokens, system=system,
                      messages=messages)
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        resp = _retry(lambda: self._stream(kwargs))
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        usage = {"input_tokens": resp.usage.input_tokens,
                 "output_tokens": resp.usage.output_tokens,
                 "stop_reason": resp.stop_reason,
                 "blocks": [getattr(b, "type", "?") for b in resp.content]}
        _check_complete(self.name, text, resp.stop_reason, usage)
        return text, usage


class OpenAICompatibleBackend(Backend):
    """OpenAI API or any OpenAI-compatible endpoint (set base_url)."""

    def __init__(self, model, max_tokens=DEFAULT_MAX_TOKENS, temperature=None, base_url=None,
                 api_key_env="OPENAI_API_KEY"):
        import openai
        self.client = openai.OpenAI(api_key=os.environ.get(api_key_env), base_url=base_url)
        self.model, self.max_tokens, self.temperature = model, max_tokens, temperature
        self.name = f"openai:{model}"

    def complete(self, system, messages, meta):
        kwargs = dict(model=self.model, max_completion_tokens=self.max_tokens,
                      messages=[{"role": "system", "content": system}] + messages)
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        try:
            resp = _retry(lambda: self.client.chat.completions.create(**kwargs))
        except Exception as e:  # noqa: BLE001  some compatible endpoints use max_tokens
            if "max_completion_tokens" not in str(e):
                raise
            kwargs["max_tokens"] = kwargs.pop("max_completion_tokens")
            resp = _retry(lambda: self.client.chat.completions.create(**kwargs))
        u = resp.usage
        text = resp.choices[0].message.content or ""
        details = getattr(u, "completion_tokens_details", None)
        usage = {"input_tokens": getattr(u, "prompt_tokens", 0),
                 "output_tokens": getattr(u, "completion_tokens", 0),
                 "reasoning_tokens": getattr(details, "reasoning_tokens", None),
                 "stop_reason": resp.choices[0].finish_reason}
        _check_complete(self.name, text, usage["stop_reason"], usage)
        return text, usage


class MockBackend(Backend):
    """Offline stand-in used to validate the pipeline. The builder returns the
    canonical solution, seeded with a mutant with some probability; the
    verifier returns tests built from hidden inputs, occasionally with a wrong
    oracle. Its numbers carry no scientific meaning."""

    def __init__(self, seed=0, p_buggy=0.6, p_fix=0.6, p_false_oracle=0.25, label="mock"):
        self.seed, self.p_buggy, self.p_fix, self.p_false = seed, p_buggy, p_fix, p_false_oracle
        self.name = label

    def _rng(self, meta, salt):
        return random.Random(f"{self.seed}|{meta['task'].task_id}|{meta.get('run')}|"
                             f"{meta.get('condition')}|{salt}")

    def complete(self, system, messages, meta):
        from . import mutation
        task, role, rng = meta["task"], meta["role"], self._rng(meta, len(messages))
        usage = {"input_tokens": sum(len(m["content"]) for m in messages) // 4,
                 "output_tokens": 400}
        ep = task.entry_point
        if task.kind == "suite":
            return self._complete_suite(task, role, meta, rng, first=len(messages) == 1), usage
        if role == "builder":
            first = len(messages) == 1
            code = task.canonical
            if rng.random() < (self.p_buggy if first else 1 - self.p_fix):
                ms = mutation.generate(task.canonical, 10, seed=rng.randint(0, 99))
                if ms:
                    code = ms[0]["code"]
            tests = "from solution import *\n\n"
            for i, (inp, exp) in enumerate(zip(task.visible_inputs, task.visible_expected)):
                tests += f"def test_example_{i}():\n    assert {ep}(*{inp!r}) == {exp!r}\n\n"
            return (f"```python file=solution.py\n{code}\n```\n"
                    f"```python file=test_solution.py\n{tests}```\n"), usage
        # verifier
        k = 4 if meta.get("phase") == "A" else 3
        offset = {"A": 0, "B": 4, "B-mut": 7}[meta["phase"]]
        idx = list(range(len(task.hidden_inputs)))
        random.Random(f"{task.task_id}|{offset}").shuffle(idx)
        tests = "from solution import *\n\n"
        for j, i in enumerate(idx[offset:offset + k]):
            exp = task.hidden_expected[i]
            if rng.random() < self.p_false:
                exp = "__wrong__"
            tests += (f"def test_{meta['phase'].replace('-', '_')}_{j}():\n"
                      f"    \"\"\"Guarantee {j}: output matches the specification.\"\"\"\n"
                      f"    inp = {task.hidden_inputs[i]!r}\n"
                      f"    out = {ep}(*inp)\n"
                      f"    assert out == {exp!r}, f'input={{inp!r}} output={{out!r}}'\n\n")
        extra = "OPEN QUESTIONS:\n- none\n" if meta["phase"] == "A" else ""
        return f"{extra}```python file=tests.py\n{tests}```\n", usage

    def _complete_suite(self, task, role, meta, rng, first):
        """Suite tasks: the builder returns the reference or one of its seeded
        faults; Phase A returns the hidden suite, later phases one test that is
        sometimes a false oracle."""
        if role == "builder":
            code = task.canonical
            if task.seeded and rng.random() < (self.p_buggy if first else 1 - self.p_fix):
                code = task.seeded[sorted(task.seeded)[rng.randrange(len(task.seeded))]]
            return (f"```python file=solution.py\n{code}\n```\n"
                    f"```python file=test_solution.py\n{task.visible_suite}\n```\n")
        if meta["phase"] == "A":
            return f"OPEN QUESTIONS:\n- none\n```python file=tests.py\n{task.hidden_suite}\n```\n"
        verdict = "False" if rng.random() < self.p_false else "True"
        test = (f"from solution import {task.entry_point}\n\n"
                f"def test_mock_{meta['phase'].replace('-', '_')}():\n"
                f"    \"\"\"Mock guarantee.\"\"\"\n"
                f"    assert {verdict}, 'input=() output=None'\n")
        return f"```python file=tests.py\n{test}```\n"


def make_backend(cfg):
    kind = cfg["provider"]
    common = {k: cfg[k] for k in ("max_tokens", "temperature") if k in cfg}
    if kind == "anthropic":
        return AnthropicBackend(cfg["model"], api_key_env=cfg.get("api_key_env", "ANTHROPIC_API_KEY"), **common)
    if kind == "openai":
        return OpenAICompatibleBackend(cfg["model"], base_url=cfg.get("base_url"),
                                       api_key_env=cfg.get("api_key_env", "OPENAI_API_KEY"), **common)
    if kind == "mock":
        return MockBackend(seed=cfg.get("seed", 0), label=cfg.get("label", "mock"))
    raise ValueError(f"unknown provider {kind}")


# ---------------------------------------------------------------- parsing
_BLOCK = re.compile(r"```([^\n]*)\n(.*?)```", re.S)
_FILE = re.compile(r"file\s*=\s*[\"']?([\w./-]+)")


def extract_files(text):
    """Return {filename: code} from fenced blocks. The file name is read from
    the info string (```python file=solution.py); unnamed blocks get block<i>."""
    files = {}
    for i, m in enumerate(_BLOCK.finditer(text)):
        info = m.group(1)
        named = _FILE.search(info)
        name = named.group(1) if named else f"block{i}"
        files[name] = m.group(2).strip() + "\n"
    return files


def extract_open_questions(text):
    m = re.search(r"OPEN QUESTIONS:\s*\n(.*?)(?:```|\Z)", text, re.S)
    if not m:
        return []
    items = [l.strip("-* \t") for l in m.group(1).splitlines() if l.strip().startswith(("-", "*"))]
    return [q for q in items if q and q.lower() not in ("none", "none.", "n/a")]
