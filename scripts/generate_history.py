"""Build CrashCart's noisefloor-demo commits on Jenkins, in order, to create test history.

The plan below runs each commit several times. Re-runs of the same commit are what let
flaky tests show up, and the commit order is what makes the slowdowns appear at known points.

Safe to re-run: builds Jenkins already has for a commit are counted, and only the missing
ones are started. One build runs at a time and the script waits for each to finish.

Usage (from the repo root, with Jenkins running and .env filled in):
    python scripts/generate_history.py            # run the plan
    python scripts/generate_history.py --dry-run  # only show what would run

Needs only the Python standard library.
"""

import argparse
import base64
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

JOB = "crashcart-tests"
POLL_SECONDS = 5

# (commit, builds wanted, subject). The base commit gets more builds, so every test has a
# settled normal duration before the first slowdown commit arrives.
PLAN = [
    ("f8da8bded664855367d58914c0909bb26067e7ac", 15,
     "test(demo): add switchable flaky and slow tests for Noisefloor"),
    ("c869f4b596d3b56c0f3b857f917f31da001ff977", 8,
     "refactor(demo): load order items with one query per order"),
    ("d1c62d1340529630b8fd75ac8650473b78934897", 8,
     "refactor(demo): turn off the product search cache"),
    ("16d530c7f4d347bb1bcba342ba46fb2ab027d75c", 8,
     "refactor(demo): retry tax service calls with a fixed back-off"),
    ("4331d0d5b49db140375be0ba5422fbb5615da593", 8,
     "refactor(demo): write the catalog export one row at a time"),
]  # fmt: skip


def read_env(path: Path) -> dict[str, str]:
    """Minimal .env reader: KEY=value lines, # comments ignored."""
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


class Jenkins:
    def __init__(self, url: str, user: str, token: str) -> None:
        self.url = url.rstrip("/")
        # An API token (unlike a password) needs no CSRF crumb for POST requests.
        credentials = base64.b64encode(f"{user}:{token}".encode()).decode()
        self.headers = {"Authorization": f"Basic {credentials}"}

    def _request(self, path: str, method: str = "GET") -> urllib.request.addinfourl:
        url = path if path.startswith("http") else f"{self.url}{path}"
        request = urllib.request.Request(url, method=method, headers=self.headers)
        return urllib.request.urlopen(request, timeout=30)

    def get_json(self, path: str) -> dict:
        with self._request(path) as response:
            return json.load(response)

    def builds(self) -> list[dict]:
        tree = urllib.parse.quote("builds[number,description,building,result]")
        return self.get_json(f"/job/{JOB}/api/json?tree={tree}")["builds"]

    def trigger(self, commit: str) -> str:
        """Queue one build of `commit`; returns the queue item URL."""
        query = urllib.parse.urlencode({"COMMIT_SHA": commit})
        with self._request(f"/job/{JOB}/buildWithParameters?{query}", method="POST") as response:
            return response.headers["Location"]

    def wait_for_start(self, queue_url: str) -> int:
        while True:
            item = self.get_json(f"{queue_url.rstrip('/')}/api/json")
            if item.get("cancelled"):
                raise RuntimeError(f"queued build was cancelled: {queue_url}")
            if item.get("executable"):
                return item["executable"]["number"]
            time.sleep(POLL_SECONDS)

    def wait_for_finish(self, number: int) -> dict:
        while True:
            build = self.get_json(f"/job/{JOB}/{number}/api/json?tree=result,building,duration")
            if not build["building"]:
                return build
            time.sleep(POLL_SECONDS)


def finished_builds_per_commit(jenkins: Jenkins) -> Counter:
    """Count usable builds per commit. Waits for any build still running first, so the count
    is never off by one after an interrupted run. The pipeline puts the commit SHA in each
    build's description."""
    for build in jenkins.builds():
        if build["building"]:
            print(f"Waiting for build #{build['number']}, which is still running...")
            jenkins.wait_for_finish(build["number"])
    return Counter(
        b["description"] for b in jenkins.builds() if b["result"] in ("SUCCESS", "UNSTABLE")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = read_env(Path(args.env_file))
    jenkins = Jenkins(env["JENKINS_URL"], env["JENKINS_ADMIN_USER"], env["JENKINS_API_TOKEN"])
    done = finished_builds_per_commit(jenkins)

    todo = [(commit, max(wanted - done[commit], 0), subject) for commit, wanted, subject in PLAN]
    for commit, missing, subject in todo:
        print(f"{commit[:7]}  {done[commit]:>2} done, {missing:>2} to run   {subject}")
    if args.dry_run:
        return 0

    total = sum(missing for _, missing, _ in todo)
    started = 0
    for commit, missing, _ in todo:
        for _ in range(missing):
            started += 1
            number = jenkins.wait_for_start(jenkins.trigger(commit))
            build = jenkins.wait_for_finish(number)
            print(
                f"[{started}/{total}] build #{number} on {commit[:7]}: "
                f"{build['result']} in {build['duration'] / 1000:.0f} s",
                flush=True,
            )
            # UNSTABLE just means some tests failed, which is expected. FAILURE means the
            # pipeline itself broke (checkout, install, ...), so stop and look.
            if build["result"] not in ("SUCCESS", "UNSTABLE"):
                print(f"Stopping: build #{number} ended {build['result']}. Check its console.")
                return 1
    print("History complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
