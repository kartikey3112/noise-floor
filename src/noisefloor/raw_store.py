"""The raw layer in DuckDB: one table per Jenkins entity, plus a log of ingestion runs.

Grain:
  raw.jenkins_builds       one row per (job_name, build_number)
  raw.jenkins_test_cases   one row per (job_name, build_number, case_index): one test execution
  raw.ingestion_runs       one row per ingestion run

The raw tables declare no primary keys. A raw layer should accept whatever the source sends,
and uniqueness is checked by the data-quality tests instead. Idempotency comes from replacing
a build's rows inside one transaction (see replace_build).
"""

import json
from dataclasses import astuple
from datetime import datetime
from pathlib import Path

import duckdb

from noisefloor.parsing import BuildRow, TestCaseRow

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.jenkins_builds (
    job_name        VARCHAR NOT NULL,
    build_number    INTEGER NOT NULL,
    result          VARCHAR,
    started_at_utc  TIMESTAMP NOT NULL,
    duration_ms     BIGINT NOT NULL,
    commit_sha      VARCHAR,
    build_url       VARCHAR,
    raw_json        JSON NOT NULL,
    ingested_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.jenkins_test_cases (
    job_name        VARCHAR NOT NULL,
    build_number    INTEGER NOT NULL,
    case_index      INTEGER NOT NULL,
    suite_name      VARCHAR NOT NULL,
    class_name      VARCHAR NOT NULL,
    test_name       VARCHAR NOT NULL,
    status          VARCHAR NOT NULL,
    duration_s      DOUBLE NOT NULL,
    error_details   VARCHAR,
    ingested_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.ingestion_runs (
    job_name            VARCHAR NOT NULL,
    started_at_utc      TIMESTAMP NOT NULL,
    finished_at_utc     TIMESTAMP NOT NULL,
    watermark_before    INTEGER NOT NULL,
    watermark_after     INTEGER NOT NULL,
    builds_loaded       INTEGER NOT NULL,
    test_cases_loaded   INTEGER NOT NULL
);
"""


class RawStore:
    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self.db = connection
        self.db.execute(SCHEMA_SQL)

    @classmethod
    def open(cls, path: Path) -> "RawStore":
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(duckdb.connect(str(path)))

    def close(self) -> None:
        self.db.close()

    def watermark(self, job_name: str) -> int:
        """The highest build number already loaded for the job (0 if none)."""
        row = self.db.execute(
            "SELECT coalesce(max(build_number), 0) FROM raw.jenkins_builds WHERE job_name = ?",
            [job_name],
        ).fetchone()
        return row[0]

    def replace_build(
        self, build: BuildRow, cases: list[TestCaseRow], raw_build: dict, now: datetime
    ) -> None:
        """Write one build and its test cases, replacing any earlier copy, all or nothing."""
        key = [build.job_name, build.build_number]
        self.db.begin()
        try:
            where = "WHERE job_name = ? AND build_number = ?"
            self.db.execute(f"DELETE FROM raw.jenkins_test_cases {where}", key)
            self.db.execute(f"DELETE FROM raw.jenkins_builds {where}", key)
            self.db.execute(
                "INSERT INTO raw.jenkins_builds VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [*astuple(build), json.dumps(raw_build), now],
            )
            if cases:
                self.db.executemany(
                    "INSERT INTO raw.jenkins_test_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [[*astuple(case), now] for case in cases],
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def record_run(
        self,
        job_name: str,
        started: datetime,
        finished: datetime,
        watermark_before: int,
        watermark_after: int,
        builds_loaded: int,
        test_cases_loaded: int,
    ) -> None:
        self.db.execute(
            "INSERT INTO raw.ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?)",
            [job_name, started, finished, watermark_before, watermark_after,
             builds_loaded, test_cases_loaded],
        )  # fmt: skip

    def row_counts(self) -> dict[str, int]:
        tables = ("jenkins_builds", "jenkins_test_cases", "ingestion_runs")
        return {t: self.db.execute(f"SELECT count(*) FROM raw.{t}").fetchone()[0] for t in tables}
