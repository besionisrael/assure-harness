"""EvalPlus tasks: specification, visible suite (base inputs), hidden suite
(plus inputs), canonical solution, with expected outputs computed once by
running the canonical solution in the sandbox and cached on disk."""
import gzip
import json
import pickle
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import sandbox

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILES = {"humaneval": "HumanEvalPlus.jsonl.gz", "mbpp": "MbppPlus.jsonl.gz"}
CASESTUDY = {"casestudy": ("casestudy/docpay", DATA_DIR / "casestudy"),          # v1
             "casestudy_v2": ("casestudy/docpay-v2", DATA_DIR / "casestudy_v2"),  # v2, DESIGN.md
             # services written by third-party models (second_service_kit/answers/MODELS.md)
             "svc_mistral": ("service/mistral-rooms", DATA_DIR / "service_mistral"),
             "svc_qwen": ("service/qwen-loans", DATA_DIR / "service_qwen")}
NOT_SUPPORT = {"reference.py", "faults.py", "visible_tests.py", "hidden_tests.py",
               "validate.py", "o_coding.py"}
URLS = {
    "humaneval": "https://github.com/evalplus/humanevalplus_release/releases/download/v0.1.10/HumanEvalPlus.jsonl.gz",
    "mbpp": "https://github.com/evalplus/mbppplus_release/releases/download/v0.2.0/MbppPlus.jsonl.gz",
}


@dataclass
class Task:
    task_id: str
    benchmark: str
    entry_point: str
    spec: str                 # S, the natural-language specification shown to all roles
    canonical: str            # reference implementation (never shown to agents)
    visible_inputs: list
    visible_expected: list
    hidden_inputs: list
    hidden_expected: list
    atol: float = 0.0
    meta: dict = field(default_factory=dict)
    # kind "io": EvalPlus input/output pairs. kind "suite": the visible and
    # hidden suites are test modules, run against the program with run_tests.
    kind: str = "io"
    visible_suite: str = ""
    hidden_suite: str = ""
    support: dict = field(default_factory=dict)   # extra importable modules, name -> source
    seeded: dict = field(default_factory=dict)    # seeded fault id -> faulty program

    @property
    def safe_id(self):
        return self.task_id.replace("/", "_")

    def visible_tests_text(self):
        if self.kind == "suite":
            return self.visible_suite.rstrip()
        lines = []
        for inp, exp in zip(self.visible_inputs, self.visible_expected):
            args = ", ".join(repr(a) for a in inp)
            lines.append(f"assert {self.entry_point}({args}) == {exp!r}")
        return "\n".join(lines)


def _raw(benchmark):
    path = DATA_DIR / FILES[benchmark]
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; download it from {URLS[benchmark]}")
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def _spec_and_canonical(benchmark, row):
    if benchmark == "humaneval":
        return row["prompt"].rstrip() + "\n", row["prompt"] + row["canonical_solution"]
    spec = (row["prompt"].strip() + "\n\n"
            f"Implement this as a Python function named `{row['entry_point']}`.\n")
    return spec, row["canonical_solution"]


class ExcludedTask(Exception):
    """The canonical solution returns values that cannot be serialized, so the
    task has no usable expected outputs. Such tasks are excluded, not repaired."""


def _expected(code, entry, inputs, cache_file):
    if cache_file.exists():
        with open(cache_file, "rb") as f:
            cached = pickle.load(f)
        if isinstance(cached, dict) and "excluded" in cached:
            raise ExcludedTask(cached["excluded"])
        return cached
    rec = sandbox.eval_io([code], entry, inputs, None, per_item_timeout=8.0)[0]
    if rec["load_error"]:
        raise RuntimeError(f"canonical solution does not load: {rec['load_error']}")
    if rec.get("unpicklable"):
        reason = f"canonical solution returns unpicklable {rec['unpicklable']}"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "wb") as f:
            pickle.dump({"excluded": reason}, f)
        raise ExcludedTask(reason)
    keep_in, keep_out = [], []
    for inp, (err, out) in zip(inputs, rec["outputs"]):
        if err is None:  # inputs on which the reference itself fails are dropped
            keep_in.append(inp)
            keep_out.append(out)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "wb") as f:
        pickle.dump((keep_in, keep_out), f)
    return keep_in, keep_out


def _build(benchmark, r, seed, max_hidden):
    spec, canonical = _spec_and_canonical(benchmark, r)
    safe = r["task_id"].replace("/", "_")
    cache = DATA_DIR / "cache" / benchmark
    vin, vexp = _expected(canonical, r["entry_point"], r["base_input"],
                          cache / f"{safe}.base.pkl")
    hin, hexp = _expected(canonical, r["entry_point"], r["plus_input"],
                          cache / f"{safe}.plus.pkl")
    if max_hidden and len(hin) > max_hidden:
        idx = sorted(random.Random(seed).sample(range(len(hin)), max_hidden))
        hin, hexp = [hin[i] for i in idx], [hexp[i] for i in idx]
    return Task(r["task_id"], benchmark, r["entry_point"], spec, canonical,
                vin, vexp, hin, hexp, float(r.get("atol") or 0.0))


def load_casestudy(benchmark="casestudy"):
    """A stateful service task: the case study v1 (data/casestudy) or v2, which
    adds deliberate ambiguities (data/casestudy_v2/DESIGN.md), or a service
    written by a third-party model. The specification shown to agents is spec.md
    without its <!-- comments -->; every other .py file of the folder that is not
    part of the ground truth is a support module importable by programs and tests."""
    import importlib.util
    task_id, d = CASESTUDY[benchmark]
    spec = re.sub(r"<!--.*?-->\n*", "", (d / "spec.md").read_text(encoding="utf-8"),
                  flags=re.S).strip() + "\n"
    mod_spec = importlib.util.spec_from_file_location("casestudy_faults", d / "faults.py")
    faults = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(faults)
    return Task(task_id, benchmark, "Service", spec, faults.reference(),
                [], [], [], [], kind="suite",
                visible_suite=(d / "visible_tests.py").read_text(encoding="utf-8"),
                hidden_suite=(d / "hidden_tests.py").read_text(encoding="utf-8"),
                support={p.stem: p.read_text(encoding="utf-8") for p in sorted(d.glob("*.py"))
                         if p.name not in NOT_SUPPORT},
                seeded={f: faults.variant(f) for f in faults.FAULTS})


def load_tasks(benchmark, n=None, seed=0, task_ids=None, max_hidden=None, excluded=None):
    """Excluded tasks are reported in `excluded` (a list, appended to). When
    sampling, each one is replaced by a task drawn from the rows not yet
    sampled, with a separate RNG, so the rest of the sample is unchanged."""
    if benchmark in CASESTUDY:
        return [load_casestudy(benchmark)]
    all_rows = _raw(benchmark)
    reserve = []
    if task_ids:
        wanted = set(task_ids)
        rows = [r for r in all_rows if r["task_id"] in wanted]
    elif n not in (None, "all"):
        rows = random.Random(seed).sample(all_rows, int(n))
        chosen = {r["task_id"] for r in rows}
        reserve = sorted((r for r in all_rows if r["task_id"] not in chosen),
                         key=lambda r: r["task_id"])
        random.Random(f"{seed}-replacements").shuffle(reserve)
    else:
        rows = all_rows
    tasks = []
    queue = list(rows)
    while queue:
        r = queue.pop(0)
        try:
            tasks.append(_build(benchmark, r, seed, max_hidden))
        except ExcludedTask as e:
            if excluded is not None:
                excluded.append({"benchmark": benchmark, "task_id": r["task_id"],
                                 "reason": str(e)})
            print(f"excluded {r['task_id']}: {e}")
            if reserve:
                queue.append(reserve.pop(0))
    tasks.sort(key=lambda t: t.task_id)
    return tasks
