"""Validate a case-study service folder (see BRIEF.md, section 6).

Run from the service folder:  python validate.py   (or: python path/to/validate.py)
Option --min-faults N lowers the required number of faults (only for the toy example).

Checks:
  * spec.md exists and contains no fenced code block;
  * the reference passes T_v and T_h, twice (determinism);
  * every seeded fault applies (its original text occurs exactly once), passes
    T_v, fails T_h, and is caught by at least one deterministic test (a test
    whose name does not contain "stateful");
  * fault ids are unique (guaranteed by the dict) and there are at least 12.
Prints ALL OK when everything holds; exits with status 1 otherwise."""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path.cwd()
OWN = {"reference.py", "faults.py", "validate.py", "visible_tests.py", "hidden_tests.py"}
MIN_FAULTS = 12


def support_modules():
    return {p.name: p.read_text(encoding="utf-8") for p in HERE.glob("*.py")
            if p.name not in OWN and not p.name.startswith("test")}


def run(solution, suite):
    """Run one suite against one program; return (failed test names, summary line)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "solution.py").write_text(solution, encoding="utf-8")
        for name, src in support_modules().items():
            (tmp / name).write_text(src, encoding="utf-8")
        (tmp / "test_suite.py").write_text((HERE / suite).read_text(encoding="utf-8"), encoding="utf-8")
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "-rf", "--tb=no", "test_suite.py"], cwd=tmp, timeout=900,
                              capture_output=True, text=True)
    out = proc.stdout.strip().splitlines()
    failed = sorted({line.split("::")[1].split(" ")[0] for line in out if line.startswith("FAILED")})
    if proc.returncode not in (0, 1):  # collection error, usage error, ...
        failed.append(f"<pytest exit {proc.returncode}: {out[-1] if out else proc.stderr[-200:]}>")
    return failed, (out[-1] if out else "")


def main():
    min_faults = MIN_FAULTS
    if "--min-faults" in sys.argv:
        min_faults = int(sys.argv[sys.argv.index("--min-faults") + 1])
    problems = []
    spec = HERE / "spec.md"
    if not spec.exists():
        problems.append("spec.md is missing")
    elif "```" in spec.read_text(encoding="utf-8"):
        problems.append("spec.md contains a fenced code block (indent the interface by 4 spaces instead)")
    for f in ("reference.py", "visible_tests.py", "hidden_tests.py", "faults.py"):
        if not (HERE / f).exists():
            problems.append(f"{f} is missing")
    if problems:
        print("\n".join("BAD " + p for p in problems))
        raise SystemExit(1)

    spec_ = importlib.util.spec_from_file_location("service_faults", HERE / "faults.py")
    faults = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(faults)
    reference = (HERE / "reference.py").read_text(encoding="utf-8")
    print(f"support modules: {sorted(support_modules()) or 'none'}")

    for attempt in (1, 2):
        vis, vis_line = run(reference, "visible_tests.py")
        hid, hid_line = run(reference, "hidden_tests.py")
        ok = not vis and not hid
        print(f"{'OK ' if ok else 'BAD'} reference (pass {attempt})  T_v: {vis_line}  T_h: {hid_line}")
        if not ok:
            problems.append(f"reference fails: T_v {vis} T_h {hid}")

    if len(faults.FAULTS) < min_faults:
        problems.append(f"only {len(faults.FAULTS)} seeded faults (at least {min_faults} required)")
    for fid, (req, desc, old, new) in faults.FAULTS.items():
        n = reference.count(old)
        if n != 1:
            print(f"BAD {fid}: its original text occurs {n} times in reference.py")
            problems.append(fid)
            continue
        code = reference.replace(old, new)
        vis, _ = run(code, "visible_tests.py")
        hid, _ = run(code, "hidden_tests.py")
        deterministic = [t for t in hid if "stateful" not in t and not t.startswith("<")]
        if vis:
            why = f"fails T_v {vis}"
        elif not hid:
            why = "passes T_h (not detected)"
        elif not deterministic:
            why = f"caught only by stateful tests {hid}"
        else:
            why = ""
        print(f"{'BAD' if why else 'OK '} {fid} [{req}] {desc}" + (f": {why}" if why else f"  (T_h failed: {hid})"))
        if why:
            problems.append(fid)

    print("\nALL OK" if not problems else f"\n{len(problems)} problem(s): {problems}")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
