"""Build the human review sheet of a validated service: does every hidden test
assert only what the specification fixes?

  python make_review.py services/<name>    ->  review/<name>.md"""
import ast
import re
import sys
from pathlib import Path

INTRO = """# Relecture : {name}

**Question à trancher, pour chaque test caché :** chaque assertion découle-t-elle
d'une phrase de la spécification ? Un test est **à problème** s'il exige un
comportement que la spécification ne permet pas de déduire : un code d'erreur non
listé, un ordre non spécifié, la priorité entre deux erreurs, un format de
réponse non décrit, une valeur limite ambiguë, etc.

Pour chaque test, inscris les lignes de la spécification qui le justifient, coche
une case, et ajoute une note si besoin. La relecture porte sur les tests, pas sur
la qualité du service.

Réponse attendue en fin de relecture : la liste des tests à problème. Ils seront
signalés au modèle auteur, qui les corrigera (on ne les modifie pas nous-mêmes).

## Spécification (numéros de ligne)

{spec}

## Notes de l'auteur (comportements laissés ouverts, etc.)

{notes}

## Tests cachés ({n})
"""

ITEM = """
### {i}. `{test}`{req}

```python
{src}
```

- Lignes de la spécification : ……
- Verdict : ☐ OK  ☐ Problème
- Note : ……
"""


def main(folder):
    folder = Path(folder)
    name = folder.name
    spec_lines = (folder / "spec.md").read_text(encoding="utf-8").splitlines()
    spec = "\n".join(f"    {i:3d}  {line}" for i, line in enumerate(spec_lines, 1))
    notes_file = folder / "AUTHOR_NOTES.md"
    notes = notes_file.read_text(encoding="utf-8").strip() if notes_file.exists() else "(none)"
    notes = "\n".join("> " + line for line in notes.splitlines())
    src = (folder / "hidden_tests.py").read_text(encoding="utf-8")
    lines = src.splitlines()
    tests = [n for n in ast.parse(src).body
             if isinstance(n, ast.FunctionDef) and n.name.startswith("test")]
    classes = [n for n in ast.parse(src).body if isinstance(n, ast.ClassDef)]
    out = [INTRO.format(name=name, spec=spec, notes=notes, n=len(tests))]
    for i, t in enumerate(tests, 1):
        body = "\n".join(lines[t.lineno - 1:t.end_lineno])
        if "run_state_machine_as_test" in body:  # include the state machine it runs
            for c in classes:
                if c.name in body:
                    body = "\n".join(lines[c.lineno - 1:c.end_lineno]) + "\n\n\n" + body
        reqs = sorted(set(re.findall(r"req[_-]?(\d+)", t.name, re.I)), key=int)
        req = f" (REQ-{', REQ-'.join(reqs)} d'après son nom)" if reqs else ""
        out.append(ITEM.format(i=i, test=t.name, req=req, src=body))
    dest = Path("review") / f"{name}.md"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text("".join(out), encoding="utf-8")
    print(f"{dest}: {len(tests)} tests")


if __name__ == "__main__":
    main(sys.argv[1])
