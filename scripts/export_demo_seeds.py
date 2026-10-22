"""Copy the demo answer key and commit subjects from CrashCart into dbt seed files.

Jenkins doesn't know which tests were designed to be flaky or slow, or what each commit's
message was. CrashCart's noisefloor-demo branch does. This script reads them from a local
CrashCart clone and writes two small CSV files that are committed with Noisefloor, so a
fresh clone of Noisefloor needs no CrashCart at all.

Usage (from the repo root):
    python scripts/export_demo_seeds.py --crashcart ../CrashCart

Re-run it only when the demo tests or demo commits change. Needs only the standard library.
"""

import argparse
import csv
import json
import subprocess
from pathlib import Path

BRANCH = "origin/noisefloor-demo"
BASE = "origin/main"
ANSWER_KEY = "tests/noisefloor_demo/expected.json"
SEEDS_DIR = Path("transform/seeds")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def export_answer_key(repo: Path) -> int:
    key = json.loads(git(repo, "show", f"{BRANCH}:{ANSWER_KEY}"))
    columns = [
        "suite_name", "class_name", "test_name", "designed_as", "cause",
        "designed_fail_rate", "baseline_s", "slowed_s", "slows_down_at_commit_subject",
    ]  # fmt: skip
    rows = [
        {
            "suite_name": t["suite"],
            "class_name": t["classname"],
            "test_name": t["test_name"],
            "designed_as": t["designed_as"],
            "cause": t.get("cause", ""),
            "designed_fail_rate": t.get("fail_rate", ""),
            "baseline_s": t.get("baseline_s", ""),
            "slowed_s": t.get("slowed_s") or "",
            "slows_down_at_commit_subject": t.get("slows_down_at_commit") or "",
        }
        for t in key["tests"]
    ]
    _write_csv(SEEDS_DIR / "demo_expected_tests.csv", columns, rows)
    return len(rows)


def export_commits(repo: Path) -> int:
    # Oldest first: the demo commits on the branch, i.e. everything not on main.
    log = git(repo, "log", "--reverse", "--format=%H%x09%s", f"{BASE}..{BRANCH}")
    rows = [dict(zip(("commit_sha", "subject"), line.split("\t", 1), strict=True))
            for line in log.splitlines() if line]  # fmt: skip
    _write_csv(SEEDS_DIR / "demo_commits.csv", ["commit_sha", "subject"], rows)
    return len(rows)


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--crashcart", type=Path, default=Path("../CrashCart"))
    args = parser.parse_args()
    git(args.crashcart, "fetch", "--quiet", "origin")
    print(f"Wrote {export_answer_key(args.crashcart)} tests to demo_expected_tests.csv")
    print(f"Wrote {export_commits(args.crashcart)} commits to demo_commits.csv")


if __name__ == "__main__":
    main()
