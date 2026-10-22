"""Incremental, idempotent ingestion: Jenkins -> landing files -> raw tables.

Incremental: only builds newer than the watermark (the highest build number already loaded)
are fetched.
Idempotent: each build is landed and then loaded with replace_build. Running ingestion again
with nothing new loads nothing, and re-loading a build gives the same rows, never duplicates.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from noisefloor.jenkins_client import BuildSource, BuildSummary
from noisefloor.landing import Landing
from noisefloor.parsing import parse_build, parse_test_report
from noisefloor.raw_store import RawStore


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class IngestResult:
    watermark_before: int
    watermark_after: int
    loaded: list[int] = field(default_factory=list)
    waiting_on: int | None = None  # first build still running, if any
    test_cases_loaded: int = 0


def builds_to_load(builds: list[BuildSummary], watermark: int) -> tuple[list[int], int | None]:
    """Finished builds newer than the watermark, in order, stopping at the first running one.

    Why stop there: with build 10 still running and 11 finished, loading 11 would move the
    watermark past 10, and 10 would never be loaded. Returns (numbers, first running build).
    """
    numbers = []
    for build in sorted((b for b in builds if b.number > watermark), key=lambda b: b.number):
        if build.building:
            return numbers, build.number
        numbers.append(build.number)
    return numbers, None


def load_build(landing: Landing, store: RawStore, job_name: str, number: int, now: datetime) -> int:
    """Load one landed build into the raw tables. Returns its number of test cases."""
    build_json, report_json = landing.load(number)
    cases = parse_test_report(job_name, number, report_json)
    store.replace_build(parse_build(job_name, build_json), cases, build_json, now)
    return len(cases)


def ingest(
    source: BuildSource,
    landing: Landing,
    store: RawStore,
    job_name: str,
    clock: Callable[[], datetime] = utc_now,
) -> IngestResult:
    started = clock()
    watermark = store.watermark(job_name)
    numbers, waiting_on = builds_to_load(source.list_builds(), watermark)
    result = IngestResult(watermark, watermark, waiting_on=waiting_on)

    for number in numbers:
        # Land first, then load from the landed files: the database is always rebuildable
        # from disk, and the load path is the same whether data is fresh or replayed.
        landing.save(number, source.get_build(number), source.get_test_report(number))
        result.test_cases_loaded += load_build(landing, store, job_name, number, clock())
        result.loaded.append(number)
        result.watermark_after = number

    store.record_run(
        job_name, started, clock(), result.watermark_before, result.watermark_after,
        len(result.loaded), result.test_cases_loaded,
    )  # fmt: skip
    return result


def reload_from_landing(
    landing: Landing, store: RawStore, job_name: str, clock: Callable[[], datetime] = utc_now
) -> tuple[int, int]:
    """Rebuild the raw tables from the landing files only. Returns (builds, test cases)."""
    numbers = landing.build_numbers()
    cases = sum(load_build(landing, store, job_name, n, clock()) for n in numbers)
    return len(numbers), cases
