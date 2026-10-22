"""Shared test helpers: small Jenkins-shaped JSON and a fake Jenkins to ingest from.

The JSON keeps only the fields Noisefloor reads, in the same shape the real API returns
(checked against a real build of the crashcart-tests job).
"""

import pytest

from noisefloor.jenkins_client import BuildSummary
from noisefloor.landing import Landing
from noisefloor.raw_store import RawStore

JOB = "crashcart-tests"
BASE_MS = 1_792_673_020_044  # 2026-10-22 12:43:40 UTC, a real build's start time


def build_json(number: int, sha: str = "abc123", result: str = "UNSTABLE") -> dict:
    return {
        "_class": "org.jenkinsci.plugins.workflow.job.WorkflowRun",
        "number": number,
        "result": result,
        "building": False,
        "timestamp": BASE_MS + number * 60_000,  # one build a minute
        "duration": 38_000,
        "description": sha,
        "url": f"http://localhost:8080/job/{JOB}/{number}/",
        "actions": [
            {"_class": "hudson.model.CauseAction", "causes": []},
            {},  # Jenkins really does return empty actions
            {
                "_class": "hudson.plugins.git.util.BuildData",
                "lastBuiltRevision": {"SHA1": sha, "branch": [{"name": "detached"}]},
            },
        ],
    }


def case(name: str, status: str = "PASSED", duration: float = 0.2, cls: str = "tests.t") -> dict:
    return {
        "className": cls,
        "name": name,
        "status": status,
        "duration": duration,
        "errorDetails": "AssertionError: boom" if status in ("FAILED", "REGRESSED") else None,
    }


def report_json(*suites: tuple[str, list[dict]]) -> dict:
    return {"suites": [{"name": name, "cases": cases} for name, cases in suites]}


def default_report() -> dict:
    return report_json(
        ("unit", [case("test_pricing")]),
        ("demo", [case("test_flaky", "FAILED"), case("test_slow", duration=1.2)]),
    )


class FakeJenkins:
    """Same methods as JenkinsClient, serving builds held in memory."""

    def __init__(self) -> None:
        self.builds: dict[int, dict] = {}
        self.reports: dict[int, dict | None] = {}
        self.running: set[int] = set()
        self.fetched: list[int] = []  # build numbers whose details were requested

    def add(self, number: int, report: dict | None = None, running: bool = False, **kw) -> None:
        self.builds[number] = build_json(number, **kw)
        self.reports[number] = default_report() if report is None else report
        if running:
            self.running.add(number)

    def finish(self, number: int) -> None:
        self.running.discard(number)

    def list_builds(self) -> list[BuildSummary]:
        # Newest first, like Jenkins.
        return [BuildSummary(n, n in self.running) for n in sorted(self.builds, reverse=True)]

    def get_build(self, number: int) -> dict:
        self.fetched.append(number)
        return self.builds[number]

    def get_test_report(self, number: int) -> dict | None:
        return self.reports[number] or None


@pytest.fixture
def jenkins() -> FakeJenkins:
    return FakeJenkins()


@pytest.fixture
def landing(tmp_path) -> Landing:
    return Landing(tmp_path / "landing", JOB)


@pytest.fixture
def store(tmp_path):
    raw = RawStore.open(tmp_path / "warehouse.duckdb")
    yield raw
    raw.close()
