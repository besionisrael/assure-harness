"""Report of the evaluation, read from the Inspect logs (no model call, no Docker).

  python inspect_eval/report.py logs/phase_a/*.eval

Writes inspect_eval/results/REPORT.md and inspect_eval/results/per_fault.csv:
  * per model: detection over the 46 seeded faults, per service, false-oracle
    rate, error rate, tests, tokens, truncated responses;
  * per fault: runs detecting / runs, for each model, next to condition A of
    the study's main campaign (frozen scoring and exploratory rescoring), given
    as context only: the evaluation draws new suites, it does not replay the study;
  * faults missed in common: never detected by any model, and missed in at
    least one run by every model;
  * with exactly two models, an EXPLORATORY sign test over the faults (not
    pre-registered: the study's protocol registered H1 and H2 only).
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import read_eval_log
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "results"
SERVICES = ["casestudy_v2", "svc_mistral", "svc_qwen"]
STUDY_CAMPAIGNS = {"study A (frozen)": "main_casestudy", "study A (rescored)": "main_casestudy_rescored"}


def load_model_runs(path):
    """One log -> (model name, per-epoch records). A record is one (service, epoch):
    its fault detections, test counts, and the solver's stop reason."""
    log = read_eval_log(str(path))
    if log.status != "success":
        raise SystemExit(f"{path}: status {log.status}; rerun or retry it before reporting")
    records = []
    for sample in log.samples:
        score = sample.scores["suite_scorer"]
        records.append({
            "service": sample.id, "epoch": sample.epoch,
            "faults": {k[len("fault:"):]: v for k, v in score.value.items() if k.startswith("fault:")},
            "tests": score.value["tests"], "false_oracles": score.value["false_oracles"],
            "errors": score.value["errors"],
            "stop_reason": sample.store.get("stop_reason"),
        })
    usage = {m: u.output_tokens for m, u in log.stats.model_usage.items()}
    return log.eval.model, records, usage, log.eval.task_args.get("mode", "expanded")


def study_condition_a(campaign):
    """Per-fault detection of condition A in a campaign of the study: fault -> (runs detecting, runs)."""
    counts = defaultdict(lambda: [0, 0])
    path = ROOT / "study" / "results" / campaign / "scores.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["condition"] != "A":
            continue
        for fid in row["seeded_faults"]:
            c = counts[(row["benchmark"], fid)]
            c[0] += fid in row["seeded_detected"]
            c[1] += 1
    return counts


def per_fault(records):
    """(service, fault) -> [runs detecting, runs]."""
    counts = defaultdict(lambda: [0, 0])
    for r in records:
        for fid, d in r["faults"].items():
            counts[(r["service"], fid)][0] += d
            counts[(r["service"], fid)][1] += 1
    return counts


def rate(c):
    return c[0] / c[1] if c[1] else 0.0


def sign_test(faults_a, faults_b):
    """Exact two-sided sign test over seeded faults, as in the study
    (study/assure/analyze.py, seeded_sign_test): each fault's detection rate is
    averaged over runs, faults with equal rates are dropped (ties).
    Returns (faults favoring a, faults favoring b, ties, p)."""
    keys = sorted(set(faults_a) & set(faults_b))
    plus = sum(rate(faults_a[k]) > rate(faults_b[k]) for k in keys)
    minus = sum(rate(faults_a[k]) < rate(faults_b[k]) for k in keys)
    p = binomtest(plus, plus + minus, 0.5).pvalue if plus + minus else 1.0
    return plus, minus, len(keys) - plus - minus, p


def summary_row(model, records, usage):
    """Pooled numbers for one model. Detection is the mean of per-fault rates (46 faults)."""
    faults = per_fault(records)
    by_service = {s: [rate(c) for (svc, _), c in faults.items() if svc == s] for s in SERVICES}
    tests = sum(r["tests"] for r in records)
    errors = sum(r["errors"] for r in records)
    fo = sum(r["false_oracles"] for r in records)
    return {
        "model": model,
        "detection": sum(rate(c) for c in faults.values()) / len(faults),
        **{s: sum(v) / len(v) for s, v in by_service.items()},
        "false_oracle_rate": fo / (tests - errors) if tests > errors else 0.0,
        "error_rate": errors / tests if tests else 0.0,
        "tests": tests, "runs": len(records),
        "truncated": sum(r["stop_reason"] not in ("stop", None) for r in records),
        "output_tokens": sum(usage.values()),
    }


def main(paths):
    runs = {}
    for p in paths:
        model, records, usage, mode = load_model_runs(p)
        if mode != "expanded":
            raise SystemExit(f"{p}: mode {mode}; the report covers the expanded evaluation only")
        if model in runs:
            raise SystemExit(f"two logs for {model}; pass one log per model")
        runs[model] = (records, usage)
    models = list(runs)
    faults = {m: per_fault(runs[m][0]) for m in models}
    study = {name: study_condition_a(c) for name, c in STUDY_CAMPAIGNS.items()}
    keys = sorted(faults[models[0]], key=lambda k: (SERVICES.index(k[0]), k[1]))

    OUT.mkdir(exist_ok=True)
    with open(OUT / "per_fault.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["service", "fault"] + models + list(study))
        for k in keys:
            w.writerow(list(k) + [f"{faults[m][k][0]}/{faults[m][k][1]}" for m in models]
                       + [f"{study[s][k][0]}/{study[s][k][1]}" for s in study])

    lines = ["# Phase A evaluation: results", "",
             "Scoring mode: expanded. Detection is the mean over the 46 seeded faults of "
             "each fault's detection rate over the runs (epochs).", "",
             "## Per model", "",
             "| Model | Detection (46) | Documents (14) | Booking (17) | Loans (15) | "
             "False oracles | Errors | Tests | Runs | Truncated | Output tokens |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in models:
        s = summary_row(m, *runs[m])
        lines.append(f"| {m} | {s['detection']:.1%} | {s['casestudy_v2']:.1%} | {s['svc_mistral']:.1%} | "
                     f"{s['svc_qwen']:.1%} | {s['false_oracle_rate']:.1%} | {s['error_rate']:.1%} | "
                     f"{s['tests']} | {s['runs']} | {s['truncated']} | {s['output_tokens']:,} |")

    lines += ["", "## Per fault (runs detecting / runs)", "",
              "The two study columns are condition A of the study's main campaign (same "
              "prompt, Claude Sonnet 5.5), given as context: they are other draws, not a replication.", "",
              "| Service | Fault | " + " | ".join(models + list(study)) + " |",
              "|---|---|" + "---|" * (len(models) + len(study))]
    for k in keys:
        cells = [f"{faults[m][k][0]}/{faults[m][k][1]}" for m in models]
        cells += [f"{study[s][k][0]}/{study[s][k][1]}" for s in study]
        lines.append(f"| {k[0]} | {k[1]} | " + " | ".join(cells) + " |")

    never = [k for k in keys if all(faults[m][k][0] == 0 for m in models)]
    not_always = [k for k in keys if all(faults[m][k][0] < faults[m][k][1] for m in models)]
    lines += ["", "## Faults missed in common", "",
              f"Never detected by any model: {', '.join('/'.join(k) for k in never) or 'none'}.", "",
              f"Missed in at least one run by every model: "
              f"{', '.join('/'.join(k) for k in not_always) or 'none'}.", ""]
    for m in models:
        missed = [k for k in keys if faults[m][k][0] < faults[m][k][1]]
        lines.append(f"- {m}: missed in at least one run: {len(missed)} faults")
    if len(models) == 2:
        a, b = models
        plus, minus, ties, p = sign_test(faults[a], faults[b])
        lines += ["", "## Exploratory comparison (not pre-registered)", "",
                  "Exact two-sided sign test over the seeded faults, the procedure the study used "
                  "for its registered hypotheses. This comparison was not registered: it is "
                  "exploratory, one pair of models, and it confounds provider, capability, and "
                  "suite size (see the Tests column above). The prompt was developed in a study "
                  "where Claude was builder and verifier, and was not adapted to GPT-5.5.", "",
                  f"{a} vs {b}: {plus} faults favor {a}, {minus} favor {b}, {ties} ties; p = {p:.4f}."]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
