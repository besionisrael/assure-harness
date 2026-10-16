"""Split the invalid tests of a scored campaign into two causes (exploratory):

  * runner-incompatible: the test function takes arguments that the frozen runner never
    passes (pytest.mark.parametrize or a pytest fixture), and it has no hypothesis @given,
    so it fails with TypeError before reaching the program;
  * genuine false oracle: any other test that fails on the reference.

  python scripts/runner_artifact.py results/main_casestudy

Writes <campaign>/analysis/runner_artifact.md and prints it."""
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

CONDS = ["SV", "A", "B", "AB", "ABp"]


def incompatible(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {n.name for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test")
            and (n.args.args or n.args.kwonlyargs)
            and not any("given" in ast.unparse(d) for d in n.decorator_list)}


def main(campaign):
    campaign = Path(campaign)
    units = {}
    for p in (campaign / "units").rglob("run*.json"):
        if not p.name.endswith(".transcript.json"):
            u = json.loads(p.read_text(encoding="utf-8"))
            units[(u["benchmark"], u["run"])] = u
    acc = defaultdict(lambda: [0, 0, 0])        # tests, runner-incompatible invalid, genuine invalid
    for line in (campaign / "scores.jsonl").read_text().splitlines():
        r = json.loads(line)
        evidence = units[(r["benchmark"], r["run"])]["conditions"][r["condition"]]["evidence"]
        for part, mods in evidence.items():
            valid = r["parts"][part]["valid"]
            for mod, src in mods.items():
                names = [n.name for n in ast.parse(src).body
                         if isinstance(n, ast.FunctionDef) and n.name.startswith("test")] \
                    if _parses(src) else []
                bad = incompatible(src)
                for name in names:
                    a = acc[(r["benchmark"], r["condition"])]
                    a[0] += 1
                    if name not in valid.get(mod, []):
                        a[1 if name in bad else 2] += 1
    lines = ["# Invalid tests by cause (exploratory)\n",
             "Runner-incompatible: arguments never passed by the frozen runner (no @given). "
             "Genuine: any other test that fails on the reference.\n",
             "| Service | Cond. | Tests | Runner-incompatible | Genuine false oracles | Genuine rate |",
             "|---|---|---|---|---|---|"]
    totals = defaultdict(lambda: [0, 0, 0])
    for (bench, cond), (t, inc, gen) in sorted(acc.items(), key=lambda kv: (kv[0][0], CONDS.index(kv[0][1]))):
        lines.append(f"| {bench} | {cond} | {t} | {inc} | {gen} | {gen / t:.1%} |" if t else "")
        tt = totals[cond]
        tt[0], tt[1], tt[2] = tt[0] + t, tt[1] + inc, tt[2] + gen
    for cond in CONDS:
        t, inc, gen = totals[cond]
        if t:
            lines.append(f"| all | {cond} | {t} | {inc} | {gen} | {gen / t:.1%} |")
    text = "\n".join(lines) + "\n"
    (campaign / "analysis" / "runner_artifact.md").write_text(text, encoding="utf-8")
    print(text)


def _parses(src):
    try:
        ast.parse(src)
        return True
    except SyntaxError:
        return False


if __name__ == "__main__":
    main(sys.argv[1])
