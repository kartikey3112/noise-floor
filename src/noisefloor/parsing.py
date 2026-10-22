"""Turn Jenkins API JSON into raw rows. Pure functions, so they're easy to test.

The raw layer keeps values as Jenkins reports them. For example, a test case status stays
PASSED, FAILED, SKIPPED, FIXED or REGRESSED here. Cleaning happens in the models later.
"""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class BuildRow:
    job_name: str
    build_number: int
    result: str | None
    started_at_utc: datetime
    duration_ms: int
    commit_sha: str | None
    build_url: str


@dataclass(frozen=True)
class TestCaseRow:
    __test__ = False  # not a pytest test class, despite the name

    job_name: str
    build_number: int
    case_index: int  # position in the report, so even duplicate names keep their own row
    suite_name: str
    class_name: str
    test_name: str
    status: str
    duration_s: float
    error_details: str | None


def commit_sha_of(build: dict) -> str | None:
    """The commit Jenkins actually checked out (git plugin's BuildData action). Falls back to
    the build description, where our pipeline also writes it."""
    for action in build.get("actions") or []:
        revision = (action or {}).get("lastBuiltRevision")
        if revision and revision.get("SHA1"):
            return revision["SHA1"]
    return build.get("description") or None


def parse_build(job_name: str, build: dict) -> BuildRow:
    return BuildRow(
        job_name=job_name,
        build_number=build["number"],
        result=build.get("result"),
        # Jenkins gives milliseconds since 1970 in UTC; stored as a plain UTC timestamp.
        started_at_utc=datetime.fromtimestamp(build["timestamp"] / 1000, UTC).replace(tzinfo=None),
        duration_ms=build.get("duration") or 0,
        commit_sha=commit_sha_of(build),
        build_url=build.get("url", ""),
    )


def parse_test_report(job_name: str, build_number: int, report: dict | None) -> list[TestCaseRow]:
    if not report:
        return []
    rows = []
    for suite in report.get("suites") or []:
        for case in suite.get("cases") or []:
            rows.append(
                TestCaseRow(
                    job_name=job_name,
                    build_number=build_number,
                    case_index=len(rows),
                    suite_name=suite.get("name") or "",
                    class_name=case.get("className") or "",
                    test_name=case["name"],
                    status=case["status"],
                    duration_s=float(case.get("duration") or 0),
                    error_details=case.get("errorDetails"),
                )
            )
    return rows
