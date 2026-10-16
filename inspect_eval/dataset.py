"""Dataset of the evaluation: the three stateful services of the study.

One Inspect Sample = one service. The model sees only the specification S
(Phase A is specification-first), so one test suite per service and per epoch
is enough: the scorer then runs it against the reference and against every
seeded fault of that service. This mirrors the study, where one Phase A suite
per run was scored against all faults. The unit of analysis stays the seeded
fault (46 in total), aggregated by the metrics in scorer.py.

Everything here reads the frozen files of study/data/ and never modifies them.
Ground truth (reference, faults, hidden tests) is kept out of the Sample and
loaded by the scorer through load_service(), so it can never leak into the
prompt or clutter the logs.
"""
import importlib.util
import re
from functools import lru_cache
from pathlib import Path

from inspect_ai.dataset import MemoryDataset, Sample

STUDY_DATA = Path(__file__).resolve().parent.parent / "study" / "data"

# Benchmark id (as in the study's results) -> folder of the service.
# The ids are the ones used in study/results/, so that results can be compared
# line by line with the paper's per-fault tables.
SERVICES = {
    "casestudy_v2": "casestudy_v2",     # documents and payments, written by the authors
    "svc_mistral": "service_mistral",   # room booking, written by Mistral Medium 3.5
    "svc_qwen": "service_qwen",         # equipment loans, written by Qwen 3.7-Plus
}

# Files of a service folder that are ground truth or tooling, never importable
# by the program under test. Same list as study/assure/data.py (NOT_SUPPORT).
NOT_SUPPORT = {"reference.py", "faults.py", "visible_tests.py", "hidden_tests.py",
               "validate.py", "o_coding.py"}

# The class under test, as named in the study's Phase A prompt ("Interface: ...").
ENTRY_POINT = "Service"


def _read(path):
    """Read a text file as UTF-8. The study's faults.reference() relies on the
    platform default encoding, which is cp1252 on Windows; we do not call it."""
    return path.read_text(encoding="utf-8")


def _strip_comments(spec):
    """Remove the <!-- ... --> author notes of spec.md, exactly as the study does
    (study/assure/data.py, load_casestudy). The models never saw these notes."""
    return re.sub(r"<!--.*?-->\n*", "", spec, flags=re.S).strip() + "\n"


def _fault_table(folder):
    """Import faults.py only to read its FAULTS dict:
    fault id -> (requirement, description, old text, new text)."""
    spec = importlib.util.spec_from_file_location(f"faults_{folder.name}", folder / "faults.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FAULTS


def _apply(reference, fault_id, old, new):
    """Build the faulty program: one local edit of the reference. Same rule as
    the study's variant(): the edited text must occur exactly once."""
    count = reference.count(old)
    if count != 1:
        raise ValueError(f"{fault_id}: target occurs {count} times in reference.py")
    return reference.replace(old, new)


@lru_cache(maxsize=None)
def load_service(benchmark):
    """Everything known about one service, including its ground truth.

    Returns a dict with:
      spec        S as shown to the models (comments removed)
      reference   reference implementation (correct by construction)
      faults      fault id -> {"requirement", "description", "program"}
      visible     T_v, the visible acceptance tests (a negative control: every
                  fault passes it by construction)
      hidden      T_h, the hidden tests (a positive control: every fault fails it)
      support     extra modules importable by programs and tests (e.g. gateway)
    Cached because the scorer calls it once per sample and epoch.
    """
    folder = STUDY_DATA / SERVICES[benchmark]
    reference = _read(folder / "reference.py")
    faults = {}
    for fault_id, (requirement, description, old, new) in _fault_table(folder).items():
        faults[fault_id] = {"requirement": requirement, "description": description,
                            "program": _apply(reference, fault_id, old, new)}
    return {
        "spec": _strip_comments(_read(folder / "spec.md")),
        "reference": reference,
        "faults": faults,
        "visible": _read(folder / "visible_tests.py"),
        "hidden": _read(folder / "hidden_tests.py"),
        "support": {p.stem: _read(p) for p in sorted(folder.glob("*.py"))
                    if p.name not in NOT_SUPPORT},
    }


def service_sample(benchmark):
    """One Sample per service.

    input     the specification S, the only thing Phase A may see; the solver
              wraps it in the study's frozen prompt
    target    the ids of the seeded faults that a good suite should detect
    metadata  what the solver and the scorer need, without any code:
              which service, the class under test, and a readable fault list
    """
    service = load_service(benchmark)
    return Sample(
        id=benchmark,
        input=service["spec"],
        target=sorted(service["faults"]),
        metadata={
            "benchmark": benchmark,
            "entry_point": ENTRY_POINT,
            "faults": {fid: {"requirement": f["requirement"], "description": f["description"]}
                       for fid, f in sorted(service["faults"].items())},
        },
    )


def assure_dataset(benchmarks=tuple(SERVICES)):
    """The dataset of the task: 3 samples, 46 seeded faults in total."""
    return MemoryDataset([service_sample(b) for b in benchmarks], name="assure-services")


def replay_dataset(runs=5):
    """Dataset of the replay check: one Sample per (service, run) of the study's
    main campaign (15 samples). The solver stored_suite() puts the Phase A suite
    that the study stored for that run in the store; no model is called."""
    samples = []
    for benchmark in SERVICES:
        for run in range(runs):
            samples.append(Sample(
                id=f"{benchmark}/run{run}",
                input=load_service(benchmark)["spec"],
                metadata={"benchmark": benchmark, "run": run, "entry_point": ENTRY_POINT},
            ))
    return MemoryDataset(samples, name="assure-replay")


if __name__ == "__main__":
    # Quick look at the dataset: python inspect_eval/dataset.py
    total = 0
    for sample in assure_dataset():
        n = len(sample.target)
        total += n
        print(f"{sample.id:13s} {n:2d} faults  spec {len(sample.input):5d} chars  "
              f"support modules: {sorted(load_service(sample.id)['support']) or '-'}")
    print(f"total: {total} seeded faults")
