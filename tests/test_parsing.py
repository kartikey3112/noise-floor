from datetime import datetime

from conftest import JOB, build_json, case, report_json

from noisefloor.parsing import commit_sha_of, parse_build, parse_test_report


def test_build_row_takes_fields_from_the_api():
    row = parse_build(JOB, build_json(2, sha="f8da8bd"))
    assert (row.build_number, row.result, row.duration_ms) == (2, "UNSTABLE", 38_000)
    assert row.commit_sha == "f8da8bd"
    assert row.started_at_utc == datetime(2026, 10, 22, 12, 45, 40, 44_000)  # ms -> UTC


def test_commit_comes_from_git_data_before_the_description():
    build = build_json(2, sha="real-sha")
    build["description"] = "something else"
    assert commit_sha_of(build) == "real-sha"


def test_commit_falls_back_to_the_description():
    build = build_json(2, sha="from-description")
    build["actions"] = [{}, {"_class": "hudson.model.CauseAction"}]
    assert commit_sha_of(build) == "from-description"


def test_commit_is_none_when_nothing_says_which():
    build = build_json(2)
    build["actions"], build["description"] = [], None
    assert commit_sha_of(build) is None


def test_every_case_becomes_a_row_with_its_suite():
    report = report_json(
        ("unit", [case("test_a", cls="tests.test_pricing")]),
        ("demo", [case("test_b", "FAILED", 1.5, cls="tests.noisefloor_demo.test_demo_flaky")]),
    )
    rows = parse_test_report(JOB, 7, report)
    assert [(r.case_index, r.suite_name, r.class_name, r.test_name) for r in rows] == [
        (0, "unit", "tests.test_pricing", "test_a"),
        (1, "demo", "tests.noisefloor_demo.test_demo_flaky", "test_b"),
    ]
    assert (rows[1].status, rows[1].duration_s, rows[1].error_details) == (
        "FAILED", 1.5, "AssertionError: boom",
    )  # fmt: skip


def test_jenkins_statuses_are_kept_as_reported():
    """FIXED and REGRESSED are Jenkins' own words for 'passed/failed, unlike last build'.
    The raw layer keeps them; the models map them to pass and fail."""
    statuses = ["FIXED", "REGRESSED", "SKIPPED"]
    report = report_json(("demo", [case(f"test_{s}", s) for s in statuses]))
    assert [r.status for r in parse_test_report(JOB, 1, report)] == statuses


def test_duplicate_test_names_keep_separate_rows():
    report = report_json(("api", [case("test_same"), case("test_same", "FAILED")]))
    assert [r.case_index for r in parse_test_report(JOB, 1, report)] == [0, 1]


def test_a_build_without_a_report_has_no_rows():
    assert parse_test_report(JOB, 1, None) == []
    assert parse_test_report(JOB, 1, {"suites": []}) == []
