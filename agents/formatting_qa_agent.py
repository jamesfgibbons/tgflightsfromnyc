#!/usr/bin/env python
import argparse
import json
import subprocess
import sys

def run(cmd, check=False):
    try:
        cp = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        ok = (cp.returncode == 0)
        return ok, cp.stdout, cp.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["check", "fix"], default="check")
    args = ap.parse_args()

    results = {
        "steps": [],
        "ok": True,
    }

    if args.mode == "fix":
        ok, out, err = run("black src tests")
        results["steps"].append({"step": "black_fix", "ok": ok, "out": out, "err": err})
        results["ok"] &= ok
        ok, out, err = run("isort src tests")
        results["steps"].append({"step": "isort_fix", "ok": ok, "out": out, "err": err})
        results["ok"] &= ok
    else:
        ok, out, err = run("black --check src tests")
        results["steps"].append({"step": "black_check", "ok": ok, "out": out, "err": err})
        results["ok"] &= ok
        ok, out, err = run("isort --check-only src tests")
        results["steps"].append({"step": "isort_check", "ok": ok, "out": out, "err": err})
        results["ok"] &= ok

    ok, out, err = run("mypy src --ignore-missing-imports --pretty")
    results["steps"].append({"step": "mypy", "ok": ok, "out": out, "err": err})
    results["ok"] &= ok

    ok, out, err = run("pytest -q")
    results["steps"].append({"step": "pytest", "ok": ok, "out": out, "err": err})
    results["ok"] &= ok

    print(json.dumps(results, indent=2))
    sys.exit(0 if results["ok"] else 1)


if __name__ == "__main__":
    main()
