"""Build the static report site from the warehouse.

Reads the metric tables, puts every number the page shows into one JSON document, and writes
site/index.html with that JSON embedded, plus its CSS and JavaScript. Nothing on the page is
typed by hand: re-running the pipeline and this step gives the same page.

The page works opened straight from disk and on GitHub Pages; it needs no server.
"""

import json
import shutil
from importlib.resources import files
from pathlib import Path

import duckdb

TEMPLATE = files("noisefloor") / "report_template"
DATA_PLACEHOLDER = "__REPORT_DATA__"


def _rows(db: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    cursor = db.execute(sql)
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _one(db: duckdb.DuckDBPyConnection, sql: str) -> dict:
    return _rows(db, sql)[0]


def collect(db: duckdb.DuckDBPyConnection) -> dict:
    """Every number the report shows, read from the marts and metrics schemas."""
    overview = _one(
        db,
        """
        select
            (select count(*) from marts.dim_build)                  as builds,
            (select count(*) from marts.dim_commit)                 as commits,
            (select count(*) from marts.dim_test)                   as tests,
            (select count(*) from marts.dim_test where is_demo)     as demo_tests,
            (select count(*) from marts.fct_test_executions)        as executions,
            (select strftime(min(started_at_utc), '%Y-%m-%d') from marts.dim_build)
                                                                    as simulated_from,
            (select strftime(max(started_at_utc), '%Y-%m-%d') from marts.dim_build)
                                                                    as simulated_to,
            (select strftime(max(started_at_real_utc), '%Y-%m-%d %H:%M UTC')
               from marts.dim_build)                                as data_as_of,
            (select count(*) from metrics.mart_test_health where is_flaky) as flaky_tests,
            (select count(*) from metrics.mart_runtime_regressions
               where episode_kind = 'sustained')                    as sustained_regressions,
            (select count(*) from metrics.mart_test_health where has_regressed)
                                                                    as regressed_tests,
            (select count(*) from metrics.mart_runtime_regressions
               where episode_kind = 'spike')                        as runtime_spikes,
            (select count(*) filter (where detected_as_designed)
               from metrics.mart_answer_key_check)                  as answer_key_matched,
            (select count(*) from metrics.mart_answer_key_check)    as answer_key_total
        """,
    )

    flaky = _rows(
        db,
        """
        select h.test_key, h.suite_name, h.class_name, h.test_name,
               round(h.flip_rate_30d, 3) as flip_rate_30d, h.flips_30d, h.pairs_30d,
               round(h.fail_rate, 3) as fail_rate, h.fails, h.runs,
               h.divergent_commits, h.commits_run_on,
               t.designed_as, t.designed_cause, t.designed_fail_rate
        from metrics.mart_test_health as h
        join marts.dim_test as t using (test_key)
        where h.is_flaky
        order by h.flip_rate_30d desc, h.test_name
        """,
    )

    # Colour follows the test, not its rank: series are assigned in a fixed (name) order.
    flaky_keys = sorted(row["test_key"] for row in flaky)
    flip_trend = _rows(
        db,
        f"""
        select f.test_key, strftime(f.calendar_date, '%Y-%m-%d') as day,
               round(f.flip_rate, 3) as flip_rate, f.flips_in_window, f.pairs_in_window
        from metrics.mart_flip_rate_daily as f
        where f.test_key in ({", ".join(f"'{k}'" for k in flaky_keys) or "''"})
        order by f.calendar_date
        """,
    )

    regressions = _rows(
        db,
        """
        select r.test_key, h.suite_name, h.test_name, r.episode_kind, r.flagged_runs,
               b.build_number as onset_build, c.short_sha as onset_commit, c.subject,
               round(r.baseline_median_s, 3) as baseline_s,
               round(r.onset_duration_s, 3) as onset_s,
               round(r.onset_duration_ratio, 2) as ratio
        from metrics.mart_runtime_regressions as r
        join metrics.mart_test_health as h using (test_key)
        join marts.dim_build as b on b.build_key = r.onset_build_key
        join marts.dim_commit as c on c.commit_key = r.onset_commit_key
        order by r.episode_kind desc, r.onset_at_utc, h.test_name
        """,
    )

    # Duration over builds for the tests with a sustained regression in the demo suite.
    slow_keys = sorted(
        {r["test_key"] for r in regressions if r["episode_kind"] == "sustained"}
        & {k for (k,) in db.execute("select test_key from marts.dim_test where is_demo").fetchall()}
    )
    durations = _rows(
        db,
        f"""
        select f.test_key, b.build_number, round(f.duration_s, 3) as duration_s
        from marts.fct_test_executions as f
        join marts.dim_build as b using (build_key)
        where f.outcome = 'pass'
          and f.test_key in ({", ".join(f"'{k}'" for k in slow_keys) or "''"})
        order by b.build_number
        """,
    )
    commits = _rows(
        db,
        """
        select c.commit_seq, c.short_sha, c.subject, min(b.build_number) as first_build
        from marts.dim_commit as c
        join marts.dim_build as b using (commit_key)
        group by all
        order by c.commit_seq
        """,
    )

    answer_key = _rows(
        db,
        """
        select test_name, designed_as, designed_cause, designed_fail_rate,
               round(observed_fail_rate, 3) as observed_fail_rate, is_flaky, divergent_commits,
               has_regressed, left(designed_slowdown_commit_sha, 7) as designed_commit,
               left(first_regression_commit_sha, 7) as found_commit, detected_as_designed
        from metrics.mart_answer_key_check
        order by designed_as, test_name
        """,
    )

    suites = _rows(
        db, "select suite_name, count(*) as tests from marts.dim_test group by 1 order by 1"
    )

    names = {row["test_key"]: row["test_name"] for row in flaky + regressions}
    return {
        "overview": overview,
        "suites": suites,
        "flaky": flaky,
        "flaky_series": [{"test_key": k, "test_name": names[k]} for k in flaky_keys],
        "flip_trend": flip_trend,
        "regressions": regressions,
        "slow_series": [{"test_key": k, "test_name": names[k]} for k in slow_keys],
        "durations": durations,
        "commits": commits,
        "answer_key": answer_key,
    }


def embed(html: str, data: dict) -> str:
    # "</" inside the JSON would end the <script> tag early, so it's escaped.
    payload = json.dumps(data, separators=(",", ":"), default=str).replace("</", "<\\/")
    return html.replace(DATA_PLACEHOLDER, payload)


def build_site(warehouse: Path, out_dir: Path) -> dict:
    """Write out_dir/index.html (data embedded) and its assets. Returns the overview numbers."""
    with duckdb.connect(str(warehouse), read_only=True) as db:
        data = collect(db)
    out_dir.mkdir(parents=True, exist_ok=True)
    html = (TEMPLATE / "index.html").read_text(encoding="utf-8")
    (out_dir / "index.html").write_text(embed(html, data), encoding="utf-8", newline="\n")
    for asset in ("report.css", "report.js"):
        with (TEMPLATE / asset).open("rb") as source, (out_dir / asset).open("wb") as target:
            shutil.copyfileobj(source, target)
    return data["overview"]
