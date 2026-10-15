"""Statistical analysis (Section V-E) and generation of the numbers used in
the paper. Outputs, in <campaign>/analysis/:
  summary.md          human-readable report of all research questions
  stats.csv           every statistical comparison with raw and Holm p-values
  results_macros.tex  LaTeX macros read by main.tex (\\resHidPassSVHE, ...)
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, wilcoxon
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests

CONDS = ["SV", "A", "B", "AB", "ABp"]
BENCH = {"humaneval": "HE", "mbpp": "MBPP", "casestudy": "CS", "casestudy_v2": "CSii",
         "svc_mistral": "SvcM", "svc_qwen": "SvcQ"}
MACRO_COND = {"SV": "SV", "A": "A", "B": "B", "AB": "AB", "ABp": "ABprime"}


def a12(x, y):
    """Vargha-Delaney A12: probability that a value from x exceeds one from y."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    gt = (x[:, None] > y[None, :]).sum()
    eq = (x[:, None] == y[None, :]).sum()
    return (gt + 0.5 * eq) / (len(x) * len(y))


def pct(v):
    return "--" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{100 * v:.1f}"


def load(scores_file):
    return [json.loads(l) for l in Path(scores_file).read_text().splitlines() if l.strip()]


def index(rows):
    """(benchmark, task, run) -> condition -> row"""
    idx = defaultdict(dict)
    for r in rows:
        idx[(r["benchmark"], r["task_id"], r["run"])][r["condition"]] = r
    return idx


def per_task_mean(rows, cond, key):
    acc = defaultdict(list)
    for r in rows:
        if r["condition"] == cond and r.get(key) is not None:
            acc[(r["benchmark"], r["task_id"])].append(float(r[key]))
    return {k: float(np.mean(v)) for k, v in acc.items()}


class Analysis:
    def __init__(self, rows):
        for r in rows:  # a faulty program that the raw-evidence gate lets through
            r["faulty_release"] = r["verdict"] == "release" and not r["correct"]
        self.rows, self.idx = rows, index(rows)
        self.conds = [c for c in CONDS if any(r["condition"] == c for r in rows)]
        self.tests, self.macros, self.md = [], {}, []
        self.confirm = []   # confirmatory tests of PROTOCOL.md, corrected as their own family

    # ---------------------------------------------------------- tests
    def seeded_sign_test(self, label, ca, cb):
        """PROTOCOL.md, H1/H2: exact two-sided sign test over seeded faults. The
        unit is the fault (benchmark, fault id); its detection rate is averaged
        over runs, and faults with equal rates in both conditions are dropped."""
        rate = {}
        for c in (ca, cb):
            acc = defaultdict(list)
            for r in self.rows:
                if r["condition"] == c and r.get("seeded_faults"):
                    for f in r["seeded_faults"]:
                        acc[(r["benchmark"], f)].append(f in r["seeded_detected"])
            rate[c] = {k: float(np.mean(v)) for k, v in acc.items()}
        faults = sorted(set(rate[ca]) & set(rate[cb]))
        if not faults:
            return
        plus = sum(rate[ca][k] > rate[cb][k] for k in faults)
        minus = sum(rate[ca][k] < rate[cb][k] for k in faults)
        p = binomtest(plus, plus + minus, 0.5).pvalue if plus + minus else 1.0
        self.confirm.append({"rq": "H", "comparison": label, "test": "sign test over faults",
                             "n": len(faults), "a": f"{ca}.seeded", "b": f"{cb}.seeded",
                             "mean_a": float(np.mean([rate[ca][k] for k in faults])),
                             "mean_b": float(np.mean([rate[cb][k] for k in faults])),
                             "effect": f"{plus}+/{minus}-/{len(faults) - plus - minus}=",
                             "p": float(p)})

    def confirmatory(self):
        self.seeded_sign_test("H1 seeded-fault detection, AB vs SV", "AB", "SV")
        self.seeded_sign_test("H2 seeded-fault detection, AB vs ABp", "AB", "ABp")
    def mcnemar_pair(self, label, rq, ca, ka, cb, kb):
        """Paired binary outcomes over (task, run): row ca.ka vs row cb.kb."""
        pairs = [(bool(v[ca][ka]), bool(v[cb][kb])) for v in self.idx.values()
                 if ca in v and cb in v]
        if not pairs:
            return
        b = sum(1 for x, y in pairs if x and not y)
        c = sum(1 for x, y in pairs if y and not x)
        p = mcnemar([[0, b], [c, 0]], exact=True).pvalue if b + c else 1.0
        self.tests.append({"rq": rq, "comparison": label, "test": "McNemar", "n": len(pairs),
                           "a": f"{ca}.{ka}", "b": f"{cb}.{kb}",
                           "mean_a": np.mean([x for x, _ in pairs]),
                           "mean_b": np.mean([y for _, y in pairs]),
                           "effect": f"discordant {b}/{c}", "p": p})

    def wilcoxon_pair(self, label, rq, ca, cb, key):
        ma, mb = per_task_mean(self.rows, ca, key), per_task_mean(self.rows, cb, key)
        common = sorted(set(ma) & set(mb))
        if len(common) < 2:
            return
        x, y = [ma[k] for k in common], [mb[k] for k in common]
        diffs = np.array(x) - np.array(y)
        p = 1.0 if np.allclose(diffs, 0) else wilcoxon(x, y, zero_method="zsplit").pvalue
        self.tests.append({"rq": rq, "comparison": label, "test": "Wilcoxon", "n": len(common),
                           "a": f"{ca}.{key}", "b": f"{cb}.{key}",
                           "mean_a": float(np.mean(x)), "mean_b": float(np.mean(y)),
                           "effect": f"A12={a12(x, y):.2f}", "p": float(p)})

    # ---------------------------------------------------------- RQs
    def rq1(self):
        self.md.append("## RQ1: evaluation gap\n")
        self.md.append("| Benchmark | Cond. | Visible pass | Hidden pass | Gap |\n|---|---|---|---|---|")
        for bench, short in BENCH.items():
            for c in self.conds:
                rs = [r for r in self.rows if r["benchmark"] == bench and r["condition"] == c]
                if not rs:
                    continue
                v = np.mean([r["visible_ok"] for r in rs])
                h = np.mean([r["visible_ok"] and r["hidden_ok"] for r in rs])
                mc = MACRO_COND[c]
                self.macros[f"resVisPass{mc}{short}"] = pct(v)
                self.macros[f"resHidPass{mc}{short}"] = pct(h)
                self.macros[f"resGap{mc}{short}"] = pct(v - h)
                self.md.append(f"| {bench} | {c} | {pct(v)} | {pct(h)} | {pct(v - h)} |")
        self.mcnemar_pair("SV visible vs hidden (evaluation gap)", "RQ1", "SV", "visible_ok", "SV", "correct")
        for c in ("AB", "ABp", "A", "B"):
            self.mcnemar_pair(f"Final correctness SV vs {c}", "RQ1", "SV", "correct", c, "correct")

    def rq2(self):
        self.md.append("\n## RQ2: evidence quality per condition (median of per-task means)\n")
        self.md.append("| Cond. | Fault detection | Mutation score | False-oracle rate | Tokens (cond.) |\n|---|---|---|---|---|")
        for c in self.conds:
            vals = {}
            for key in ("detection_rate", "mutation_score", "false_oracle_rate", "tokens_condition"):
                m = per_task_mean(self.rows, c, key)
                vals[key] = float(np.median(list(m.values()))) if m else None
            mc = MACRO_COND[c]
            self.macros[f"resDet{mc}"] = pct(vals["detection_rate"])
            self.macros[f"resMut{mc}"] = pct(vals["mutation_score"])
            self.macros[f"resFalseOr{mc}"] = pct(vals["false_oracle_rate"])
            tok = vals["tokens_condition"]
            self.macros[f"resTok{mc}"] = "--" if tok is None else f"{tok / 1000:.1f}k"
            self.md.append(f"| {c} | {pct(vals['detection_rate'])} | {pct(vals['mutation_score'])} "
                           f"| {pct(vals['false_oracle_rate'])} | {self.macros[f'resTok{mc}']} |")
        for key in ("detection_rate", "mutation_score", "false_oracle_rate"):
            self.wilcoxon_pair(f"Context independence SV vs AB ({key})", "RQ2", "SV", "AB", key)
            self.wilcoxon_pair(f"Model independence AB vs ABp ({key})", "RQ2", "AB", "ABp", key)

    def rq3(self):
        self.md.append("\n## RQ3: complementarity of Phase A and Phase B\n")
        for key in ("detection_rate", "mutation_score"):
            self.wilcoxon_pair(f"A vs B ({key})", "RQ3", "A", "B", key)
            self.wilcoxon_pair(f"AB vs A ({key})", "RQ3", "AB", "A", key)
            self.wilcoxon_pair(f"AB vs B ({key})", "RQ3", "AB", "B", key)
        # (i) within AB: parts produced in the same verifier context
        for cond in ("AB", "ABp"):
            tot = {"faults": [0, 0, 0], "mutants": [0, 0, 0]}
            for r in self.rows:
                if r["condition"] != cond or "A" not in r["parts"] or "B" not in r["parts"]:
                    continue
                for name, field in (("faults", "detected"), ("mutants", "killed")):
                    a, b = set(r["parts"]["A"][field]), set(r["parts"]["B"][field])
                    tot[name][0] += len(a - b)
                    tot[name][1] += len(b - a)
                    tot[name][2] += len(a & b)
            self.md.append(f"Within {cond} (summed over task-runs): faults A-only/B-only/both = "
                           f"{tot['faults']}; mutants A-only/B-only/both = {tot['mutants']}")
            mc = MACRO_COND[cond]
            for name in tot:
                for lbl, v in zip(("Aonly", "Bonly", "Both"), tot[name]):
                    self.macros[f"resComp{mc}{name.capitalize()}{lbl}"] = str(v)
        # (ii) independent conditions A and B on the same pool
        tot = {"faults": [0, 0, 0], "mutants": [0, 0, 0]}
        for v in self.idx.values():
            if "A" in v and "B" in v:
                for name, field in (("faults", "detected"), ("mutants", "killed")):
                    a, b = set(v["A"][field]), set(v["B"][field])
                    tot[name][0] += len(a - b)
                    tot[name][1] += len(b - a)
                    tot[name][2] += len(a & b)
        self.md.append(f"Conditions A vs B (separate verifiers): faults A-only/B-only/both = "
                       f"{tot['faults']}; mutants = {tot['mutants']}")
        self.seeded_table()
        oq = [r["open_questions"] for r in self.rows if r["condition"] in ("A", "AB", "ABp")]
        if oq:
            share = np.mean([q > 0 for q in oq])
            self.macros["resOpenQuestionShare"] = pct(share)
            self.md.append(f"Phase A reported at least one open question in {pct(share)}% of task-runs.")

    def seeded_table(self):
        """Case study: detection of each seeded fault, per condition (runs detecting / runs),
        and within AB / ABp, by Phase A only, Phase B only, or both."""
        rows = [r for r in self.rows if r.get("seeded_detection_rate") is not None]
        if not rows:
            return
        # one table per service: fault ids are local to a service (F01 of one is not F01 of another)
        for bench in sorted({r["benchmark"] for r in rows}):
            brows = [r for r in rows if r["benchmark"] == bench]
            faults = brows[0]["seeded_faults"]
            self.md.append(f"\n### Seeded-fault detection, {bench} ({len(faults)} seeded faults, "
                           "runs detecting / runs)\n")
            self.md.append("| Fault | " + " | ".join(self.conds) + " |\n|---|" + "---|" * len(self.conds))
            for f in faults:
                cells = []
                for c in self.conds:
                    rs = [r for r in brows if r["condition"] == c]
                    cells.append(f"{sum(f in r['seeded_detected'] for r in rs)}/{len(rs)}")
                self.md.append(f"| {f} | " + " | ".join(cells) + " |")
            short = BENCH.get(bench, bench)
            for c in self.conds:
                rs = [r for r in brows if r["condition"] == c]
                if rs:
                    self.macros[f"resSeedDet{MACRO_COND[c]}{short}"] = pct(
                        np.mean([r["seeded_detection_rate"] for r in rs]))
        for c in self.conds:  # pooled over services (mean of per-row rates)
            rs = [r for r in rows if r["condition"] == c]
            if rs:
                self.macros[f"resSeedDet{MACRO_COND[c]}"] = pct(np.mean([r["seeded_detection_rate"] for r in rs]))
        for cond in ("AB", "ABp"):
            tot = [0, 0, 0]
            for r in rows:
                if r["condition"] == cond and "A" in r["parts"] and "B" in r["parts"]:
                    a = set(r["parts"]["A"]["seeded_detected"])
                    b = set(r["parts"]["B"]["seeded_detected"])
                    tot = [tot[0] + len(a - b), tot[1] + len(b - a), tot[2] + len(a & b)]
            self.md.append(f"\nCase study, within {cond}: seeded faults A-only/B-only/both = {tot}")
            for lbl, v in zip(("Aonly", "Bonly", "Both"), tot):
                self.macros[f"resSeed{MACRO_COND[cond]}{lbl}"] = str(v)

    def rq4(self):
        for field, title, suffix in (("verdict", "raw evidence, as a release gate sees it", ""),
                                     ("verdict_valid_only", "valid tests only (false oracles removed)", "Valid")):
            self._rq4_table(field, title, suffix)
        self.mcnemar_pair("Faulty releases SV vs AB", "RQ4", "SV", "faulty_release", "AB", "faulty_release")

    def _rq4_table(self, field, title, suffix):
        self.md.append(f"\n## RQ4: release decisions, {title}\n")
        self.md.append("| Cond. | TP (block faulty) | FN (release faulty) | FP (block correct) | TN | Precision(block) | Recall(block) |\n|---|---|---|---|---|---|---|")
        for c in self.conds:
            rs = [r for r in self.rows if r["condition"] == c]
            tp = sum(1 for r in rs if r[field] == "block" and not r["correct"])
            fn = sum(1 for r in rs if r[field] == "release" and not r["correct"])
            fp = sum(1 for r in rs if r[field] == "block" and r["correct"])
            tn = sum(1 for r in rs if r[field] == "release" and r["correct"])
            prec = tp / (tp + fp) if tp + fp else None
            rec = tp / (tp + fn) if tp + fn else None
            mc = MACRO_COND[c]
            self.macros[f"resBlockPrec{suffix}{mc}"] = pct(prec)
            self.macros[f"resBlockRec{suffix}{mc}"] = pct(rec)
            self.md.append(f"| {c} | {tp} | {fn} | {fp} | {tn} | {pct(prec)} | {pct(rec)} |")

    # ---------------------------------------------------------- output
    def finish(self, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        # two Holm families: the confirmatory tests of PROTOCOL.md, and everything else
        for family, tests in (("confirmatory", self.confirm), ("exploratory", self.tests)):
            if tests:
                adj = multipletests([t["p"] for t in tests], alpha=0.05, method="holm")
                for t, padj, rej in zip(tests, adj[1], adj[0]):
                    t["p_holm"], t["significant"], t["family"] = float(padj), bool(rej), family
        with open(out_dir / "stats.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["family", "rq", "comparison", "test", "n", "a", "b",
                                              "mean_a", "mean_b", "effect", "p", "p_holm",
                                              "significant"])
            w.writeheader()
            w.writerows(self.confirm + self.tests)
        for title, tests in (("Protocol tests H1/H2 (PROTOCOL.md; own Holm family; confirmatory only "
                              "for campaigns run after the freeze)", self.confirm),
                             ("Exploratory tests (Holm-corrected, alpha = 0.05)", self.tests)):
            if not tests:
                continue
            self.md.append(f"\n## {title}\n")
            self.md.append("| RQ | Comparison | Test | n | Mean a | Mean b | Effect | p | p (Holm) |\n|---|---|---|---|---|---|---|---|---|")
            for t in tests:
                self.md.append(f"| {t['rq']} | {t['comparison']} | {t['test']} | {t['n']} | "
                               f"{t['mean_a']:.3f} | {t['mean_b']:.3f} | {t['effect']} | "
                               f"{t['p']:.4f} | {t.get('p_holm', float('nan')):.4f} |")
        n_tasks = len({(r["benchmark"], r["task_id"]) for r in self.rows})
        n_runs = len({r["run"] for r in self.rows})
        self.macros["resNTasks"] = str(n_tasks)
        self.macros["resNRuns"] = str(n_runs)
        header = (f"# Analysis\n\n{n_tasks} tasks, {n_runs} runs, conditions {self.conds}. "
                  f"Pool and mutant definitions: see assure/scoring.py.\n")
        (out_dir / "summary.md").write_text(header + "\n".join(self.md) + "\n")
        lines = ["% Generated by assure.analyze. Do not edit by hand."]
        lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(self.macros.items())]
        (out_dir / "results_macros.tex").write_text("\n".join(lines) + "\n")


def analyze_campaign(cfg):
    out_dir = Path(cfg["output_dir"]) / cfg["campaign"]
    a = Analysis(load(out_dir / "scores.jsonl"))
    a.confirmatory()
    a.rq1()
    a.rq2()
    a.rq3()
    a.rq4()
    a.finish(out_dir / "analysis")
    print((out_dir / "analysis" / "summary.md").read_text())
