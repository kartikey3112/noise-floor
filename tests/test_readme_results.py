from noisefloor.report import RESULTS_END, RESULTS_START, update_readme

DATA = {
    "overview": {
        "builds": 3, "commits": 1, "tests": 2, "executions": 6, "simulated_from": "2026-10-01",
        "simulated_to": "2026-10-02", "flaky_tests": 1, "sustained_regressions": 0,
        "regressed_tests": 0, "runtime_spikes": 0, "answer_key_matched": 1, "answer_key_total": 1,
    },
    "suites": [{"suite_name": "demo", "tests": 1}, {"suite_name": "unit", "tests": 1}],
    "flaky": [{
        "test_name": "test_x", "suite_name": "demo", "flip_rate_30d": 0.5, "flips_30d": 1,
        "pairs_30d": 2, "fail_rate": 0.333, "fails": 1, "runs": 3, "divergent_commits": 1,
        "commits_run_on": 1,
    }],
    "regressions": [],
    "answer_key": [{
        "test_name": "test_x", "designed_as": "flaky", "designed_fail_rate": 0.3,
        "observed_fail_rate": 0.333, "is_flaky": True, "divergent_commits": 1,
        "has_regressed": False, "found_commit": None, "designed_commit": None,
        "detected_as_designed": True,
    }],
}  # fmt: skip


def test_only_the_text_between_the_markers_is_replaced(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# Title\n\nIntro.\n\n{RESULTS_START}\nold numbers\n{RESULTS_END}\n\nOutro.\n"
    )

    assert update_readme(readme, DATA)

    text = readme.read_text(encoding="utf-8")
    assert text.startswith("# Title\n\nIntro.\n\n") and text.endswith(f"{RESULTS_END}\n\nOutro.\n")
    assert "old numbers" not in text
    assert "3 builds of 1 commits" in text
    assert "(1 unit, 1 demo)" in text  # suites in a fixed order: unit, API, demo
    assert "| `test_x` | demo | 50% (1/2) | 33% (1/3) | 1 of 1 |" in text


def test_running_it_twice_gives_the_same_readme(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(f"{RESULTS_START}\n{RESULTS_END}\n")
    update_readme(readme, DATA)
    once = readme.read_text(encoding="utf-8")
    update_readme(readme, DATA)
    assert readme.read_text(encoding="utf-8") == once


def test_a_readme_without_markers_is_left_alone(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# No markers here\n")
    assert not update_readme(readme, DATA)
    assert readme.read_text(encoding="utf-8") == "# No markers here\n"
