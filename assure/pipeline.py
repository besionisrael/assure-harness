"""Experimental pipeline.

For each (task, run): the builder produces an initial program P0 through its
self-validation loop. Every condition branches from the same P0 and the same
builder context, so that differences between conditions are attributable to
the evidence alone.

  SV    evidence = the builder's own tests; P0 is final.
  A     verifier Phase A only (no access to the program).
  B     verifier Phase B only (read-only access to P0, mutation-guided).
  AB    Phase A, frozen, then Phase B on P0. Same model as the builder.
  ABp   as AB, verifier on a different model/provider (model independence).

In A, B, AB, ABp the evidence is frozen and evaluated on the current program;
failures are returned to the builder as counterexamples for a bounded number
of rounds.
"""
import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import agents, data, llm, prompts, sandbox

VERIFIER_CONDITIONS = {"A": ("A",), "B": ("B",), "AB": ("A", "B"), "ABp": ("A", "B")}


def _unit_path(out_dir, task, run):
    return Path(out_dir) / "units" / task.benchmark / task.safe_id / f"run{run}.json"


def run_condition(cond, task, run, builder0, backends, cfg, log):
    b = cfg["budgets"]
    builder = builder0.fork(cond)
    if cond == "SV":
        return {"programs": [builder0.solution], "final": builder0.solution,
                "evidence": {"builder": {"test_solution": builder0.tests}},
                "rounds": [], "usage": builder.usage, "open_questions": []}
    vbackend = backends["verifier_alt"] if cond == "ABp" else backends["verifier"]
    verifier = agents.Verifier(vbackend, task, {"run": run, "condition": cond}, log, cfg)
    evidence, mutation_info = {}, None
    p0 = builder0.solution
    if "A" in VERIFIER_CONDITIONS[cond]:
        evidence["A"] = verifier.phase_a()
    if "B" in VERIFIER_CONDITIONS[cond]:
        evidence["B"], mutation_info = verifier.phase_b(p0, evidence.get("A"))
    modules = {m: src for part in evidence.values() for m, src in part.items()}
    programs, rounds = [p0], []
    for r in range(1, b["cex_rounds"] + 1):
        res = sandbox.run_tests([builder.solution], modules,
                                max_examples=cfg["hypothesis_max_examples"],
                                support=task.support)[0]
        text, n_fail = agents.counterexamples(res, b["max_counterexamples"])
        rounds.append({"round": r, "failing": n_fail})
        if n_fail == 0:
            break
        builder.repair(text, b["inner_repair_rounds"])
        rounds[-1]["counterexamples"] = text
        programs.append(builder.solution)
    return {"programs": programs, "final": builder.solution,
            "evidence": evidence, "rounds": rounds, "mutation": mutation_info,
            "open_questions": verifier.open_questions,
            "usage": {"builder": builder.usage, "verifier": verifier.usage},
            "verifier_backend": vbackend.name}


class _LiveLog(list):
    """Transcript written to disk after every call, so that an interrupted unit
    (exception or killed process) can be rerun without paying again for the
    calls already made. Nothing is written while the first `keep` entries are
    being replayed, so a rerun that fails early never shortens the record."""

    def __init__(self, path, keep=0):
        super().__init__()
        self.path, self.keep = path, keep

    def append(self, item):
        super().append(item)
        if len(self) > self.keep:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self, indent=1))
            os.replace(tmp, self.path)


def run_unit(task, run, backends, cfg, out_dir):
    path = _unit_path(out_dir, task, run)
    if path.exists():
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".partial.transcript.json")
    replay = None
    if partial.exists():
        replay = llm.Replay(json.loads(partial.read_text()))
        backends = {k: replay.wrap(v) for k, v in backends.items()}
    log = _LiveLog(partial, keep=len(replay.entries) if replay else 0)
    t0 = time.time()
    builder0 = agents.Builder(backends["builder"], task, {"run": run, "condition": "P0"}, log, cfg)
    sv_info = builder0.self_validate(cfg["budgets"]["self_rounds"])
    unit = {"task_id": task.task_id, "benchmark": task.benchmark, "run": run,
            "prompt_version": prompts.PROMPT_VERSION,
            "backends": {k: v.name for k, v in backends.items()},
            "p0": builder0.solution, "p0_info": sv_info,
            "usage_shared": dict(builder0.usage), "conditions": {}}
    for cond in cfg["conditions"]:
        unit["conditions"][cond] = run_condition(cond, task, run, builder0, backends, cfg, log)
    unit["seconds"] = round(time.time() - t0, 1)
    unit["replayed_calls"] = replay.pos if replay else 0
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(unit, indent=1))
    tmp.rename(path)
    path.with_suffix(".transcript.json").write_text(json.dumps(log, indent=1))
    if partial.exists():  # replayed calls stay marked "replayed" in the final transcript
        partial.unlink()
    return "done"


def load_all_tasks(cfg, excluded=None):
    tasks = []
    for bench, opts in cfg["benchmarks"].items():
        tasks += data.load_tasks(bench, n=opts.get("n"), seed=cfg["seed"],
                                 task_ids=opts.get("task_ids"), max_hidden=cfg.get("max_hidden"),
                                 excluded=excluded)
    return tasks


def run_campaign(cfg):
    out_dir = Path(cfg["output_dir"]) / cfg["campaign"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=1))
    backends = {k: llm.make_backend(v) for k, v in cfg["models"].items()}
    excluded = []
    tasks = load_all_tasks(cfg, excluded)
    (out_dir / "excluded_tasks.json").write_text(json.dumps(excluded, indent=1))
    units = [(t, r) for t in tasks for r in range(cfg["runs"])]
    print(f"{len(tasks)} tasks x {cfg['runs']} runs = {len(units)} units; "
          f"conditions {cfg['conditions']}")
    errors = 0
    with ThreadPoolExecutor(cfg.get("workers", 4)) as pool:
        futs = {pool.submit(run_unit, t, r, backends, cfg, out_dir): (t, r) for t, r in units}
        for i, f in enumerate(as_completed(futs), 1):
            t, r = futs[f]
            try:
                status = f.result()
            except Exception:  # noqa: BLE001
                errors += 1
                status = "error"
                (out_dir / "errors.log").open("a").write(
                    f"{t.task_id} run{r}\n{traceback.format_exc()}\n")
            print(f"[{i}/{len(units)}] {t.task_id} run{r}: {status}", flush=True)
    print(f"finished with {errors} errors")
