"""Check the case-study ground truth (run inside the container):

  python data/casestudy/validate.py

The reference must pass T_v and T_h. Every seeded fault must pass T_v and fail
T_h, and must be caught by at least one deterministic test (not only by the
stateful test, whose detection depends on the random search)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from faults import FAULTS, HERE, reference, variant  # noqa: E402

STATEFUL = "test_stateful_two_users"


def run(solution, suite):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "solution.py").write_text(solution)
        (tmp / "gateway.py").write_text((HERE / "gateway.py").read_text())
        (tmp / "test_suite.py").write_text((HERE / suite).read_text())
        report = tmp / "report.txt"
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        "-rf", "--tb=no", "test_suite.py"], cwd=tmp, timeout=600,
                       stdout=open(report, "w"), stderr=subprocess.STDOUT)
        out = report.read_text()
    failed = sorted({line.split("::")[1].split(" ")[0] for line in out.splitlines()
                     if line.startswith("FAILED")})
    return failed, out.strip().splitlines()[-1]


def main():
    ok = True
    results = {}
    for name, code in [("reference", reference())] + [(f, variant(f)) for f in FAULTS]:
        vis, vis_line = run(code, "visible_tests.py")
        hid, hid_line = run(code, "hidden_tests.py")
        results[name] = {"visible_failed": vis, "hidden_failed": hid}
        if name == "reference":
            good = not vis and not hid
        else:
            good = not vis and any(t != STATEFUL for t in hid)
        ok &= good
        print(f"{'OK ' if good else 'BAD'} {name:9s} T_v: {vis_line:28s} T_h failed: {hid}")
    (HERE / "validation.json").write_text(json.dumps(results, indent=1))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
