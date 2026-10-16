"""Pre-fill the coding grid for the type O items of DESIGN.md (run inside the container):

  python data/casestudy_v2/o_coding.py results/pilot_casestudy_v2

For every (run, condition, item) it writes one row with:
  * raised    Phase A open questions that match the item (keyword candidates, to confirm)
  * tested    verifier or builder tests whose source matches the item, and whether each
              one fails on the reference (a false oracle by the current definition)
  * builder   behavior of the final program on the item, measured by a probe, and
              whether it matches the recorded intent R
  * disputed  matching tests that still fail on the final program, i.e. the builder
              kept its behavior against them

Keyword matches are candidates only: the coder confirms or corrects them in the
coder_* columns. Outputs: <campaign>/analysis/O_coding/grid.csv and excerpts.md."""
import ast
import csv
import json
import re
import sys
from pathlib import Path

from assure import data, sandbox

ITEMS = {
    "O1": ("administrators", r"admin|superuser|privileged|\brole"),
    "O2": ("case folding beyond ASCII", r"casefold|ß|stra(ss|ß)e|unicode|non-ascii|accent|turkish|locale"),
    "O3": ("is a key used by a rejected request", r"(key|idempoten)[^\n]{0,120}(400|invalid|reject|consum)"
                                                  r"|(400|invalid|reject)[^\n]{0,120}(key|idempoten)"),
    "O4": ("empty idempotency key", r"empty[^\n]{0,30}key|key[^\n]{0,30}empty|pay\([^)\n]*,\s*(\"\"|'')\s*\)"),
    "O5": ("unencodable characters", r"surrogate|\\ud8|unencod|encod|emoji|non-utf"),
}
INTENT = {"O1": "no admin role", "O2": "casefold", "O3": "a rejected request does not consume the key",
          "O4": "empty key gives 400", "O5": "always return a status, never raise"}

PROBES = r'''
from solution import Service


class Clock:
    def now(self):
        return 1000.0


class Gateway:
    def charge(self, reference, amount_cents):
        pass


def make():
    svc = Service(Clock(), Gateway())
    svc.register("alice", "password-alice")
    return svc, svc.login("alice", "password-alice")[1]["token"]


def _obs(f):
    try:
        return f()
    except BaseException as e:  # noqa: BLE001
        return "raised " + type(e).__name__


def test_probe_O2():
    svc, t = make()
    svc.create_document(t, "Straße", "")
    r = _obs(lambda: svc.search_documents(t, "STRASSE"))
    obs = r if isinstance(r, str) else (r[0], len(r[1]) if r[0] == 200 else None)
    assert False, repr(("O2", obs))


def test_probe_O3():
    svc, t = make()
    first = _obs(lambda: svc.pay(t, 0, "k1"))
    second = _obs(lambda: svc.pay(t, 100, "k1"))
    status = lambda r: r if isinstance(r, str) else r[0]  # noqa: E731
    assert False, repr(("O3", (status(first), status(second))))


def test_probe_O4():
    svc, t = make()
    r = _obs(lambda: svc.pay(t, 100, ""))
    assert False, repr(("O4", r if isinstance(r, str) else r[0]))


def test_probe_O5():
    svc = Service(Clock(), Gateway())
    r = _obs(lambda: svc.register("bob", "\ud800" * 8))
    assert False, repr(("O5", r if isinstance(r, str) else r[0]))
'''


def matches_intent(item, obs):
    if obs is None:
        return ""
    if item == "O2":
        return obs == (200, 1)
    if item == "O3":
        return obs[1] == 201
    if item == "O4":
        return obs == 400
    if item == "O5":
        return isinstance(obs, int)
    return ""


def probe(programs, task):
    res = sandbox.run_tests(programs, {"probes": PROBES}, support=task.support)
    out = []
    for r in res:
        obs = {}
        for name, t in r.get("modules", {}).get("probes", {}).get("tests", {}).items():
            msg = t["message"].split("AssertionError: ", 1)[-1]
            try:
                value = ast.literal_eval(msg)
                if isinstance(value, str):  # the runner quotes the assertion message
                    value = ast.literal_eval(value)
                item, value = value
                obs[item] = value
            except (ValueError, SyntaxError):
                obs[name[-2:]] = f"unreadable: {t['message'][:80]}"
        out.append(obs)
    return out


def test_functions(source):
    """name -> source of each top-level test function (and the module docstring)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    lines = source.splitlines()
    return {n.name: "\n".join(lines[n.lineno - 1:n.end_lineno]) for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test")}


def main(campaign):
    campaign = Path(campaign)
    task = data.load_casestudy("casestudy_v2")
    scores = {(r["run"], r["condition"]): r
              for r in map(json.loads, (campaign / "scores.jsonl").read_text().splitlines())
              if r["benchmark"] == "casestudy_v2"}      # a campaign may hold other services
    units = sorted((campaign / "units" / "casestudy_v2").rglob("run*.json"))
    units = [json.loads(p.read_text()) for p in units if not p.name.endswith(".transcript.json")]
    out_dir = campaign / "analysis" / "O_coding"
    out_dir.mkdir(parents=True, exist_ok=True)
    ref_obs = probe([task.canonical], task)[0]
    rows, excerpts = [], ["# Type O coding: excerpts (keyword candidates, to confirm)\n",
                          f"Reference behavior on the probes: {ref_obs}\n",
                          "Intent R: " + "; ".join(f"{k}: {v}" for k, v in INTENT.items()) + "\n"]
    for u in sorted(units, key=lambda u: u["run"]):
        conds = u["conditions"]
        finals = [conds[c]["final"] for c in conds]
        obs = dict(zip(conds, probe(finals, task)))
        for cond, c in conds.items():
            modules = {m: s for part in c["evidence"].values() for m, s in part.items()}
            valid = {m: set(ts) for p in scores[(u["run"], cond)]["parts"].values()
                     for m, ts in p["valid"].items()}
            on_final = sandbox.run_tests([c["final"]], modules, support=task.support,
                                         max_examples=50)[0]
            final_status = {(m, n): t["status"] for m, mr in on_final.get("modules", {}).items()
                            for n, t in mr.get("tests", {}).items()}
            excerpts.append(f"\n## run {u['run']}, {cond}\n")
            for item, (label, rx) in ITEMS.items():
                pat = re.compile(rx, re.I)
                raised = [q for q in c.get("open_questions", []) if pat.search(q)]
                tested = [(m, n, src) for m, s in modules.items()
                          for n, src in test_functions(s).items() if pat.search(src)]
                false_or = [f"{m}::{n}" for m, n, _ in tested if n not in valid.get(m, set())]
                disputed = [f"{m}::{n}" for m, n, _ in tested
                            if final_status.get((m, n), "pass") != "pass"]
                b = obs[cond].get(item)
                rows.append({
                    "run": u["run"], "condition": cond, "item": item, "label": label,
                    "raised_auto": len(raised) > 0,
                    "tested_auto": len(tested), "tested_false_oracles_auto": len(false_or),
                    "builder_behavior": b, "builder_matches_R": matches_intent(item, b),
                    "disputed_auto": len(disputed),
                    "coder_raised": "", "coder_tested": "", "coder_disputed": "", "coder_notes": ""})
                if raised or tested:
                    excerpts.append(f"\n### {item} ({label})\n")
                    for q in raised:
                        excerpts.append(f"- open question: {q}")
                    for m, n, src in tested:
                        tag = " **[false oracle]**" if f"{m}::{n}" in false_or else ""
                        tag += " **[still fails on final]**" if f"{m}::{n}" in disputed else ""
                        excerpts.append(f"- test `{m}::{n}`{tag}\n\n```python\n{src[:1500]}\n```")
    with open(out_dir / "grid.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out_dir / "excerpts.md").write_text("\n".join(excerpts) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows -> {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1])
