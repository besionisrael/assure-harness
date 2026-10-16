"""Scoring of a finished campaign (Section V-D of the paper).

For every task:
  * every distinct program produced in any run or condition is evaluated on
    the visible suite T_v and the hidden suite T_h;
  * the FAULT POOL is the set of distinct programs that fail T_v or T_h;
    for the case study it also contains the seeded faulty variants of the
    reference, whose detection is reported per fault;
  * KILLABLE MUTANTS are mutants of the canonical solution detected by T_h
    (mutants that T_h cannot distinguish are treated as likely equivalent);
  * every evidence set (builder tests for SV, Phase A / Phase B tests for the
    verifier conditions) is validated on the canonical solution: tests that
    fail on it are FALSE ORACLES and are excluded from detection metrics;
  * valid tests are run on the fault pool and on the killable mutants.

One JSON line per (task, run, condition) is written to scores.jsonl.
"""
import ast
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import data, mutation, sandbox


def norm_hash(code):
    try:
        code = ast.unparse(ast.parse(code))
    except SyntaxError:
        pass
    return hashlib.sha1(code.encode()).hexdigest()[:12]


def _failed_any(record):
    if record["load_error"]:
        return True
    return any(r["status"] != "pass" for m in record["modules"].values()
               for r in m["tests"].values()) or any(
        m.get("collect_error") for m in record["modules"].values())


class TaskScorer:
    def __init__(self, task, units, cfg):
        self.task, self.units, self.cfg = task, units, cfg
        self.mx = cfg.get("scoring_max_examples", 50)
        # exploratory option (PROTOCOL.md, deviation log): run pytest.mark.parametrize tests
        self.expand = bool(cfg.get("scoring_expand_parametrize", False))

    # ------------------------------------------------------------ programs
    def evaluate_programs(self):
        t = self.task
        codes = {}
        for u in self.units:
            codes[norm_hash(u["p0"])] = u["p0"]
            for c in u["conditions"].values():
                for p in c["programs"] + [c["final"]]:
                    codes[norm_hash(p)] = p
        self.seeded = {}
        for fid, code in t.seeded.items():
            self.seeded[norm_hash(code)] = fid
            codes[norm_hash(code)] = code
        keys = list(codes)
        if t.kind == "suite":
            vis = self._run_suite([codes[k] for k in keys], {"visible_tests": t.visible_suite})
            hid = self._run_suite([codes[k] for k in keys], {"hidden_tests": t.hidden_suite})
            ok = lambda r: not _failed_any(r)  # noqa: E731
        else:
            vis = sandbox.eval_io([codes[k] for k in keys], t.entry_point, t.visible_inputs,
                                  t.visible_expected, t.atol, stop_on_first_fail=True)
            hid = sandbox.eval_io([codes[k] for k in keys], t.entry_point, t.hidden_inputs,
                                  t.hidden_expected, t.atol, stop_on_first_fail=True)
            ok = lambda r: r["load_error"] is None and len(r["status"]) > 0 and all(r["status"])  # noqa: E731
        self.codes = codes
        self.vis_ok = {k: ok(v) for k, v in zip(keys, vis)}
        self.hid_ok = {k: ok(h) for k, h in zip(keys, hid)}
        self.pool = [k for k in keys if not (self.vis_ok[k] and self.hid_ok[k])]

    def _run_suite(self, programs, modules, **kw):
        """Ground-truth suites of a suite task; their tests set their own Hypothesis budget."""
        return sandbox.run_tests(programs, modules, stop_on_first_fail=True,
                                 support=self.task.support, expand_parametrize=self.expand, **kw)

    def killable_mutants(self):
        t = self.task
        ms = mutation.generate(t.canonical, self.cfg.get("scoring_mutants", 30), seed=1)
        if not ms:
            self.mutants = []
            return
        if t.kind == "suite":
            res = self._run_suite([m["code"] for m in ms],
                                  {"visible_tests": t.visible_suite, "hidden_tests": t.hidden_suite})
            self.mutants = [m for m, r in zip(ms, res) if _failed_any(r)]
            return
        res = sandbox.eval_io([m["code"] for m in ms], t.entry_point,
                              t.visible_inputs + t.hidden_inputs,
                              t.visible_expected + t.hidden_expected, t.atol,
                              stop_on_first_fail=True)
        self.mutants = [m for m, r in zip(ms, res)
                        if r["load_error"] is not None or not all(r["status"])]

    # ------------------------------------------------------------ evidence
    def score_part(self, modules):
        """Validate a set of test modules and measure their detection power."""
        canon = sandbox.run_tests([self.task.canonical], modules, max_examples=self.mx,
                                  support=self.task.support, expand_parametrize=self.expand)[0]
        valid, n_tests, n_invalid, collect_fail = {}, 0, 0, 0
        for mod, mres in canon["modules"].items():
            if mres.get("collect_error"):
                collect_fail += 1
                continue
            ok = [n for n, r in mres["tests"].items() if r["status"] == "pass"]
            n_tests += len(mres["tests"])
            n_invalid += len(mres["tests"]) - len(ok)
            if ok:
                valid[mod] = ok
        out = {"n_tests": n_tests, "n_invalid": n_invalid, "collect_fail": collect_fail,
               "detected": [], "killed": [], "valid": valid}
        if not valid:
            return out
        targets = [("F", k, self.codes[k]) for k in self.pool] + \
                  [("M", m["id"], m["code"]) for m in self.mutants]
        if not targets:
            return out
        res = sandbox.run_tests([c for _, _, c in targets], {m: modules[m] for m in valid},
                                only_tests=valid, stop_on_first_fail=True, max_examples=self.mx,
                                support=self.task.support, expand_parametrize=self.expand)
        for (kind, ident, _), r in zip(targets, res):
            if _failed_any(r):
                (out["detected"] if kind == "F" else out["killed"]).append(ident)
        return out

    def verdict(self, final_code, modules, only_tests=None):
        """Release iff the final program passes T_v and every test of the
        evidence. With only_tests=None the raw evidence is used, as a release
        gate would (it cannot tell valid from invalid tests); with the valid
        tests only, the verdict isolates the effect of false oracles."""
        k = norm_hash(final_code)
        if not self.vis_ok[k]:
            return "block"
        if only_tests is not None:
            modules = {m: modules[m] for m in only_tests}
            if not modules:
                return "release"
        res = sandbox.run_tests([final_code], modules, only_tests=only_tests,
                                max_examples=self.mx, support=self.task.support,
                                expand_parametrize=self.expand)[0]
        return "block" if _failed_any(res) else "release"

    # ------------------------------------------------------------ main
    def rows(self):
        self.evaluate_programs()
        self.killable_mutants()
        rows = []
        for u in self.units:
            p0 = norm_hash(u["p0"])
            for cond, c in u["conditions"].items():
                parts = {name: self.score_part(mods) for name, mods in c["evidence"].items()}
                for p in parts.values():
                    p["seeded_detected"] = sorted(self.seeded[k] for k in p["detected"]
                                                  if k in self.seeded)
                all_modules = {m: s for mods in c["evidence"].values() for m, s in mods.items()}
                det = set().union(*(set(p["detected"]) for p in parts.values())) if parts else set()
                kil = set().union(*(set(p["killed"]) for p in parts.values())) if parts else set()
                n_tests = sum(p["n_tests"] for p in parts.values())
                n_inv = sum(p["n_invalid"] for p in parts.values())
                fk = norm_hash(c["final"])
                usage = c.get("usage", {})
                cond_tokens = sum(v.get("input_tokens", 0) + v.get("output_tokens", 0)
                                  for v in (usage.values() if "builder" in usage else [usage])
                                  if isinstance(v, dict))
                shared = u["usage_shared"]["input_tokens"] + u["usage_shared"]["output_tokens"]
                rows.append({
                    "task_id": u["task_id"], "benchmark": u["benchmark"], "run": u["run"],
                    "condition": cond,
                    "p0_visible_ok": self.vis_ok[p0], "p0_hidden_ok": self.hid_ok[p0],
                    "visible_ok": self.vis_ok[fk], "hidden_ok": self.hid_ok[fk],
                    "correct": self.vis_ok[fk] and self.hid_ok[fk],
                    "n_tests": n_tests, "n_invalid": n_inv,
                    "false_oracle_rate": (n_inv / n_tests) if n_tests else None,
                    "collect_fail": sum(p["collect_fail"] for p in parts.values()),
                    "pool_size": len(self.pool), "detected": sorted(det),
                    "detection_rate": (len(det) / len(self.pool)) if self.pool else None,
                    "seeded_faults": sorted(self.seeded.values()),
                    "seeded_detected": sorted(self.seeded[k] for k in det if k in self.seeded),
                    "seeded_detection_rate": (len([k for k in det if k in self.seeded])
                                              / len(self.seeded)) if self.seeded else None,
                    "killable": len(self.mutants), "killed": sorted(kil),
                    "mutation_score": (len(kil) / len(self.mutants)) if self.mutants else None,
                    "parts": parts,
                    "verdict": self.verdict(c["final"], all_modules),
                    "verdict_valid_only": self.verdict(
                        c["final"], all_modules,
                        {m: t for p in parts.values() for m, t in p["valid"].items()}),
                    "rounds_used": sum(1 for r in c.get("rounds", []) if r.get("failing")),
                    "open_questions": len(c.get("open_questions", [])),
                    "tokens_condition": cond_tokens, "tokens_shared": shared,
                })
        return rows


def score_campaign(cfg):
    out_dir = Path(cfg["output_dir"]) / cfg["campaign"]
    by_task = {}
    for f in sorted((out_dir / "units").rglob("run*.json")):
        if f.name.endswith(".transcript.json"):
            continue
        u = json.loads(f.read_text())
        by_task.setdefault((u["benchmark"], u["task_id"]), []).append(u)
    tasks = {}
    for bench in {b for b, _ in by_task}:
        ids = [tid for b, tid in by_task if b == bench]
        for t in data.load_tasks(bench, task_ids=ids, max_hidden=cfg.get("max_hidden")):
            tasks[(bench, t.task_id)] = t
    score_file = out_dir / "scores.jsonl"
    done = set()
    if score_file.exists():
        for line in score_file.read_text().splitlines():
            r = json.loads(line)
            done.add((r["benchmark"], r["task_id"]))
    todo = [k for k in by_task if k not in done]
    print(f"scoring {len(todo)} tasks ({len(done)} already scored)")
    with ThreadPoolExecutor(cfg.get("scoring_workers", 4)) as pool, score_file.open("a") as fh:
        futs = {pool.submit(TaskScorer(tasks[k], by_task[k], cfg).rows): k for k in todo}
        for i, f in enumerate(as_completed(futs), 1):
            k = futs[f]
            for row in f.result():
                fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(f"[{i}/{len(todo)}] scored {k[1]}", flush=True)
