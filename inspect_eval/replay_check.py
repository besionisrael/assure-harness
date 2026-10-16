"""Reproduction check: compare a replay_study log with the study's own scores.

  python inspect_eval/replay_check.py logs/replay/<log>.eval

For each (service, run), the Phase A suite stored by the study was rescored by
our scorer (task replay_study). We compare, against study/results/<campaign>/
scores.jsonl (condition A, part A):
  valid tests     same names, as a set
  tests           same count (when the module loaded)
  invalid tests   study n_invalid == our false oracles + errors
  seeded faults   same set detected
Hypothesis is derandomized in the runner, so we expect exact equality.
Exit code 0 when every (service, run) matches, 1 otherwise.
"""
import json
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parent.parent


def study_rows(campaign):
    """(benchmark, run) -> part A of condition A in the study's scores.jsonl."""
    rows = {}
    path = ROOT / "study" / "results" / campaign / "scores.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["condition"] == "A":
            rows[(r["benchmark"], r["run"])] = r["parts"]["A"]
    return rows


def compare(sample, expected):
    """List of differences between one replayed sample and the study's row."""
    score = sample.scores["suite_scorer"]
    classes = score.metadata["classes"]
    ours = {
        "valid": sorted(classes["valid"]),
        "invalid": len(classes["false_oracle"]) + len(classes["error"]),
        "tests": score.value["tests"],
        "seeded": sorted(k[len("fault:"):] for k, v in score.value.items()
                         if k.startswith("fault:") and v),
    }
    theirs = {
        "valid": sorted(expected["valid"].get("test_phase_a", [])),
        "invalid": expected["n_invalid"],
        "tests": expected["n_tests"],
        "seeded": sorted(expected["seeded_detected"]),
    }
    if expected["collect_fail"]:
        # The study counts no test when the module does not load; we count them as errors.
        ours.pop("tests"), theirs.pop("tests"), ours.pop("invalid"), theirs.pop("invalid")
    return [f"{k}: ours {ours[k]} / study {theirs[k]}" for k in ours if ours[k] != theirs[k]]


def main(path):
    log = read_eval_log(path)
    campaign = log.eval.task_args["campaign"]
    expected = study_rows(campaign)
    mismatches = 0
    print(f"campaign {campaign}, scoring mode {log.samples[0].scores['suite_scorer'].metadata['mode']}")
    for sample in sorted(log.samples, key=lambda s: s.id):
        key = (sample.metadata["benchmark"], sample.metadata["run"])
        diffs = compare(sample, expected[key])
        mismatches += bool(diffs)
        status = "OK  " if not diffs else "DIFF"
        print(f"{status} {sample.id:20s} " + ("; ".join(diffs) if diffs else
              f"{len(expected[key]['seeded_detected'])} faults, {expected[key]['n_tests']} tests, "
              f"{expected[key]['n_invalid']} invalid"))
    print(f"{len(log.samples) - mismatches}/{len(log.samples)} runs reproduced exactly")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
