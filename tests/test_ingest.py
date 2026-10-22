from conftest import JOB, case, report_json

from noisefloor.ingest import builds_to_load, ingest, reload_from_landing
from noisefloor.jenkins_client import BuildSummary


def raw_rows(store) -> tuple[list, list]:
    builds = store.db.execute(
        "SELECT build_number, commit_sha, result FROM raw.jenkins_builds ORDER BY 1"
    ).fetchall()
    cases = store.db.execute(
        "SELECT build_number, case_index, suite_name, test_name, status, duration_s "
        "FROM raw.jenkins_test_cases ORDER BY 1, 2"
    ).fetchall()
    return builds, cases


# --- choosing what to load ---


def test_only_builds_after_the_watermark_are_loaded():
    builds = [BuildSummary(n, False) for n in (5, 4, 3, 2)]
    assert builds_to_load(builds, watermark=3) == ([4, 5], None)


def test_loading_stops_at_the_first_running_build():
    """Loading 4 while 3 is still running would move the watermark past 3 for good."""
    builds = [BuildSummary(4, False), BuildSummary(3, True), BuildSummary(2, False)]
    assert builds_to_load(builds, watermark=0) == ([2], 3)


def test_deleted_build_numbers_are_simply_skipped():
    builds = [BuildSummary(5, False), BuildSummary(2, False)]  # 3 and 4 were deleted
    assert builds_to_load(builds, watermark=0) == ([2, 5], None)


# --- end to end against a fake Jenkins ---


def test_first_run_loads_everything(jenkins, landing, store):
    jenkins.add(2, sha="aaa")
    jenkins.add(3, sha="bbb")
    result = ingest(jenkins, landing, store, JOB)
    assert (result.loaded, result.watermark_before, result.watermark_after) == ([2, 3], 0, 3)
    builds, cases = raw_rows(store)
    assert builds == [(2, "aaa", "UNSTABLE"), (3, "bbb", "UNSTABLE")]
    assert len(cases) == 6  # 3 test cases per build
    assert landing.build_numbers() == [2, 3]


def test_running_again_with_nothing_new_changes_nothing(jenkins, landing, store):
    jenkins.add(2)
    ingest(jenkins, landing, store, JOB)
    before = raw_rows(store)
    jenkins.fetched.clear()

    result = ingest(jenkins, landing, store, JOB)

    assert result.loaded == [] and jenkins.fetched == []  # not even asked for details
    assert raw_rows(store) == before
    assert store.row_counts()["ingestion_runs"] == 2  # both runs are logged


def test_new_builds_are_picked_up_incrementally(jenkins, landing, store):
    jenkins.add(2)
    ingest(jenkins, landing, store, JOB)
    jenkins.add(3)
    jenkins.fetched.clear()

    result = ingest(jenkins, landing, store, JOB)

    assert result.loaded == [3] and jenkins.fetched == [3]
    assert [b[0] for b in raw_rows(store)[0]] == [2, 3]


def test_a_running_build_waits_for_the_next_run(jenkins, landing, store):
    jenkins.add(2)
    jenkins.add(3, running=True)
    jenkins.add(4)

    first = ingest(jenkins, landing, store, JOB)
    assert (first.loaded, first.waiting_on) == ([2], 3)

    jenkins.finish(3)
    second = ingest(jenkins, landing, store, JOB)
    assert (second.loaded, second.waiting_on) == ([3, 4], None)


def test_a_build_without_tests_is_loaded_with_no_cases(jenkins, landing, store):
    jenkins.add(2, report={}, result="FAILURE")  # broke before tests ran: no report
    ingest(jenkins, landing, store, JOB)
    builds, cases = raw_rows(store)
    assert builds == [(2, "abc123", "FAILURE")] and cases == []


def test_reloading_the_same_build_never_duplicates_rows(jenkins, landing, store):
    jenkins.add(2)
    ingest(jenkins, landing, store, JOB)
    before = raw_rows(store)

    reload_from_landing(landing, store, JOB)
    reload_from_landing(landing, store, JOB)

    assert raw_rows(store) == before


def test_raw_tables_can_be_rebuilt_from_landing_alone(jenkins, landing, store):
    jenkins.add(2, report=report_json(("demo", [case("test_x", "FAILED", 0.7)])))
    jenkins.add(3)
    ingest(jenkins, landing, store, JOB)
    before = raw_rows(store)
    store.db.execute("DELETE FROM raw.jenkins_test_cases")
    store.db.execute("DELETE FROM raw.jenkins_builds")

    assert reload_from_landing(landing, store, JOB) == (2, 4)
    assert raw_rows(store) == before


def test_ingestion_runs_record_the_watermark_move(jenkins, landing, store):
    jenkins.add(2)
    jenkins.add(3)
    ingest(jenkins, landing, store, JOB)
    run = store.db.execute(
        "SELECT watermark_before, watermark_after, builds_loaded, test_cases_loaded "
        "FROM raw.ingestion_runs"
    ).fetchone()
    assert run == (0, 3, 2, 6)
