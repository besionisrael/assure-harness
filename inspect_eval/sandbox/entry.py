"""Runs inside the sandbox container. Loads the study's frozen runner
(_runner.py, copied next to this file by the scorer), runs one test job, and
writes the result as JSON.

Why JSON and not the runner's own pickle output: the result is read back on
the host, and unpickling data produced next to untrusted code would let that
code execute on the host. JSON can only carry data.

Usage (by the scorer): python -I entry.py job.json result.json
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_runner():
    """Import _runner.py by path: with python -I, the script's folder is not on sys.path."""
    spec = importlib.util.spec_from_file_location("_runner", os.path.join(HERE, "_runner.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    runner = load_runner()
    with open(sys.argv[1], encoding="utf-8") as f:
        job = json.load(f)
    sys.setrecursionlimit(5000)          # as in _runner.main()
    result = runner.run_tests(job)
    payload = json.dumps(result, default=str)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(payload)
    os._exit(0)                          # as in _runner.main(): skip teardown of possibly corrupted state


if __name__ == "__main__":
    main()
