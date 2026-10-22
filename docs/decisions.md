# Architecture decision records

The decisions that shaped Noisefloor, with the alternatives considered and their
consequences. The git history has the detail of how each was implemented.

| # | Decision |
|---|---|
| [ADR-001](#adr-001-test-data-crashcart-plus-switchable-demo-tests) | Test data: CrashCart plus switchable demo tests |
| [ADR-002](#adr-002-test-identity-and-what-jenkins-runs) | Test identity and what Jenkins runs |
| [ADR-003](#adr-003-reproducible-jenkins-and-build-history) | Reproducible Jenkins and build history |
| [ADR-004](#adr-004-duckdb-as-the-warehouse) | DuckDB as the warehouse |
| [ADR-005](#adr-005-dbt-for-transformations-on-its-own-python-version) | dbt for transformations, on its own Python version |
| [ADR-006](#adr-006-a-raw-landing-layer-that-keeps-the-source-as-is) | A raw landing layer that keeps the source as is |
| [ADR-007](#adr-007-incremental-idempotent-ingestion) | Incremental, idempotent ingestion |
| [ADR-008](#adr-008-star-schema-at-test-execution-grain) | Star schema at test-execution grain |
| [ADR-009](#adr-009-simulated-build-times) | Simulated build times |
| [ADR-010](#adr-010-metric-definitions) | Metric definitions |
| [ADR-011](#adr-011-runtime-spikes-versus-sustained-regressions) | Runtime spikes versus sustained regressions |
| [ADR-012](#adr-012-data-quality-checks) | Data-quality checks |
| [ADR-013](#adr-013-orchestration-and-ci) | Orchestration and CI |
| [ADR-014](#adr-014-a-static-report-and-a-generated-readme) | A static report and a generated README |
| [ADR-015](#adr-015-free-tools-only) | Free tools only |

---

## ADR-001: Test data: CrashCart plus switchable demo tests

**Status:** accepted

**Context.** Flaky tests are rare in a healthy suite, and there's no way to check a detector
without known right answers. Company data was off the table.

**Decision.** Use my own CrashCart project (real backend unit and API tests with JUnit output),
plus a set of demo tests that are flaky or slow *on purpose*:

- They live on a separate branch, `noisefloor-demo`, in `tests/noisefloor_demo/`, and are
  skipped unless `NOISEFLOOR_DEMO=1`. CrashCart's own CI runs only on `main` and never sets the
  variable, so its results are unaffected.
- The flaky tests fail for realistic reasons (a timing race, order dependence, random data, a
  slow dependency, a time-zone slip), each at a known rate.
- The slow tests get slower at specific, real commits ("load order items with one query per
  order"), because real regressions come from code changes.
- Randomness is seeded from the Jenkins build number, so a rebuilt history gives the same
  outcomes.
- `expected.json` is the answer key.

**Alternatives.**
- A well-known open-source project: real, but rarely flaky, and with no answer key.
- A project from a flaky-test research dataset: real flakiness, but often 1 failure in 50 or
  more runs, and no answer key for slowdowns.
- A separate demo app: full control, but entirely synthetic.

**Consequences.** Detection can be scored ("11 of 11 detected as designed"), next to real tests
that should come out clean. The demo tests are labelled as synthetic everywhere they appear.
CrashCart already has a small flaky-test page of its own, so Noisefloor's focus is the data
engineering around it: ingestion, modelling, quality checks and runtime regressions.

## ADR-002: Test identity and what Jenkins runs

**Status:** accepted

**Decision.**
- A test is `(suite, classname, test_name)`, and **suite** means the test layer: `unit`, `api` or
  `demo`. pytest names every JUnit suite `pytest`, so the Jenkinsfile sets
  `-o junit_suite_name=<layer>` for each layer. The identity then comes straight from Jenkins'
  test report. Example: `(api, tests.api.test_cart, test_update_quantity)`.
- Jenkins runs the unit tests, the API tests against a backend it starts itself, and the demo
  tests. CrashCart's UI tests (browsers, Node) and perf tests (Java, JMeter) are left out: a lot
  of setup for few extra tests.
- **No automatic retries.** A retry turns one flaky execution into a "pass". Without retries,
  every execution is recorded once, and flakiness shows up across builds, which is what the
  metrics measure.

## ADR-003: Reproducible Jenkins and build history

**Status:** accepted

**Decision.**
- Jenkins LTS in Docker, configured entirely from files: Configuration as Code for the admin
  user and settings, Job DSL for the job, and the Jenkinsfile in this repo. No setup wizard,
  no clicking.
- Pinned versions: Jenkins `2.580.1-lts-jdk21`, uv `0.12.23` (which installs Python 3.14 in the
  image), and all 69 plugins in `plugins.lock.txt`.
- One executor: every build starts its own backend on port 8000, and builds running side by side
  would also make timings noisier.
- Scripts and ingestion use a Jenkins API token from `.env`, never the admin password.
- `scripts/generate_history.py` builds the 5 demo commits in order: 15 builds on the base commit,
  then 8 on each slowdown commit. It can be re-run safely and only starts the builds that are
  missing.

**Why those numbers.** 15 builds give every test a settled normal duration before the first
slowdown. 8 runs per commit give a flaky test room to both pass and fail on the same commit.

## ADR-004: DuckDB as the warehouse

**Status:** accepted

**Alternatives.**
- PostgreSQL in Docker: production-like, but another server to run, and slower for analytics.
- SQLite: no window-function speed, and a weaker dbt adapter.
- ClickHouse: built for far more data than this.
- MotherDuck, the Snowflake trial and the BigQuery sandbox were ruled out: they can bill, or
  they run in the cloud rather than locally.

**Decision.** DuckDB, as one file (`data/noisefloor.duckdb`).

**Why.** The data is small (about 13,000 executions) and the work is analytical: rolling
windows, medians, lags. DuckDB does that fast, with zero setup, and has a mature dbt adapter.

## ADR-005: dbt for transformations, on its own Python version

**Status:** accepted

**Decision.** dbt-core with dbt-duckdb, in its own uv environment (`transform/`) on **Python
3.13**, while the rest of the project uses 3.14. Both environments pin DuckDB 1.5.6, so they
read the same file.

**Context.** The project targets Python 3.14, to match CrashCart. I tested dbt before relying
on it:

| Combination | Result |
|---|---|
| dbt-core 1.11 + dbt-duckdb 1.11 on Python 3.14 | fails at start-up, in its `mashumaro` dependency |
| dbt-core 1.12 on 3.14 | starts, then fails on a missing `metricflow` module |
| dbt-core 1.11 on Python 3.13 | works |

**Alternatives.** The whole project on 3.13 (one environment, but out of step with CrashCart).
Plain SQL run from Python (3.14 everywhere, but no dbt tests, docs or ordering). Pinning dbt 1.12's
dependencies until it works on 3.14 (unsupported, and fragile).

**Consequences.** Two lock files to maintain. The pipeline calls dbt as a separate program from
`transform/.venv`. When dbt supports 3.14, the split can be removed.

## ADR-006: A raw landing layer that keeps the source as is

**Status:** accepted

**Decision.**
- Every build's API response and its test report are saved **unchanged** as JSON under
  `data/raw/jenkins/<job>/`, then loaded into DuckDB's `raw` schema:
  - `jenkins_builds`: one row per build
  - `jenkins_test_cases`: one row per test execution
  - `ingestion_runs`: one row per ingestion run
- The raw layer keeps Jenkins' own values: real UTC times, and statuses such as `FIXED` and
  `REGRESSED`. Cleaning and the simulated time happen in the dbt models, as separate columns.
- The raw tables declare **no primary keys**. A raw layer should accept what the source sends.
  Uniqueness is checked by the data-quality tests instead (ADR-012).

**Consequences.** `noisefloor reload-raw` rebuilds the raw tables from disk without Jenkins.
A bad load can be replayed, and the raw layer is an exact, checkable copy of the source.

## ADR-007: Incremental, idempotent ingestion

**Status:** accepted

**Decision.**
- **Incremental:** a watermark (the highest build number loaded) means only newer builds are
  fetched. Loading **stops at the first build still running**: if build 10 is running and 11
  has finished, loading 11 would move the watermark past 10, and 10 would never be loaded.
- **Idempotent:** each build is written in one transaction, deleting its rows and inserting
  them again. Running ingestion twice changes nothing the second time.

**Evidence.** Against the real Jenkins, run 1 loaded builds #2 to #9. Run 2, straight after,
loaded nothing and reported #10 as still running. Row counts were unchanged. Unit tests cover
the same cases against a fake Jenkins.

## ADR-008: Star schema at test-execution grain

**Status:** accepted

**Decision.**
- **Fact `fct_test_executions`:** one row per test execution (one test case in one build).
  It holds the outcome, Jenkins status, duration, error message, real and simulated times, and
  `test_run_seq` (the test's 1st, 2nd… execution in time order).
- **Dimensions:** `dim_test`, `dim_build`, `dim_commit`, `dim_date`.
- `commit_key` sits on the fact directly, although the build implies it. The flaky rule is
  literally "same test, same commit", so that question takes one join instead of two.
- **Keys** are MD5 hashes of the natural key columns. The same input always gives the same key,
  so rebuilding from scratch never renumbers anything.
- **Layers:** staging (views), intermediate (views), marts and metrics (tables). Each model's
  SQL starts with its grain.

**Why this grain.** Every metric is an aggregate over "what happened to this test in this
build". A coarser grain (per test per day) would lose the same-commit comparison.

## ADR-009: Simulated build times

**Status:** accepted

**Context.** All demo builds ran in one afternoon, so a 30-day window would contain everything
and prove nothing.

**Decision.** In the models, the newest build keeps its real start time, and each earlier build
is placed 18 hours before the next (dbt var `simulated_build_spacing_hours`). The 47 builds then
span about 34 days, so the oldest fall outside the 30-day window. Real times are kept next to
them in `*_real_utc` columns, and the report says the timeline is simulated.

**Consequences.** Simulated times shift if a new build arrives, because they're anchored to the
newest one. Metrics are always recomputed in full, so results stay consistent for any given set
of builds.

## ADR-010: Metric definitions

**Status:** accepted

**Outcomes.** `PASSED`/`FIXED` → pass. `FAILED`/`REGRESSED` → fail (JUnit errors arrive as
`FAILED`). `SKIPPED` → skip, stored but ignored by every metric.

**Flaky (same-commit divergence).** The test both passed and failed on the same commit.

**30-day flip rate.** Put the test's non-skipped executions in time order, pair each with the
one before it, and count the pairs where the outcome switched. For each day, only pairs with
both runs inside the 30 days ending that day count. Example: P, P, F, P gives 2 flips in 3
pairs, 67%.

**Runtime regression.** A passed run that takes more than **1.5×** the median of the test's
previous **20** passed runs, **and** at least **0.5 s** longer, with at least 5 earlier passed
runs to compare against.
- The median, rather than the mean, isn't thrown off by one odd run.
- The 0.5 s floor stops tiny tests from raising alarms (0.01 s → 0.40 s is 40×, but noise).
- **Only passed runs form the baseline.** A test that crashes early looks fast and would drag
  the median down, so normal runs would then look like regressions.

**Alternatives for the regression rule.** A z-score (statistically standard, but easily skewed
by outliers). A percentile threshold (easy to explain, but needs more history).

**Evidence.** Each metric has dbt unit tests on small hand-made data with known answers. With a
deliberately wrong threshold (a 0.3 s floor), the matching unit test fails.

## ADR-011: Runtime spikes versus sustained regressions

**Status:** accepted

**Context.** On the full history, the rule flagged 23 episodes in real API tests. Most were a
single slow run: the API tests run 4 at a time on one laptop, so their timings are noisy.

**Alternatives.**
1. Keep the rule, and label episodes by how long they last.
2. Count only slowdowns that last several runs (a change to the rule itself).
3. Raise the thresholds (simple, but it also hides modest real slowdowns).

**Decision.** Option 1. Back-to-back flagged runs form one *episode*. An episode with 3 or more
flagged runs is **sustained**, and a shorter one is a **spike**. "Has regressed" counts sustained
episodes only, and the report lists spikes separately.

**Why.** It shows everything honestly and doesn't tune the rule to fit one dataset. The demo
slowdowns last 8 to 11 runs, so they're far from the boundary.

**Consequences.** The three real API tests with sustained episodes all started at the same build,
on the same commit as the fast builds before it. So the cause was the machine, not the code,
which the star schema makes quick to check.

## ADR-012: Data-quality checks

**Status:** accepted

**Decision.** dbt tests, run on every `dbt build`:

- **Uniqueness** of every grain, in the raw tables and the models, including at most one
  execution per test per build (true because there are no retries).
- **Nulls** where a missing value would break a metric: commit SHA, start time, test identity,
  duration, outcome.
- **Referential integrity:** every raw test case belongs to a raw build (a two-column key), and
  every fact row links to all four dimensions.
- **Allowed values** for build results, statuses, outcomes and episode kinds.
- **Rules:** no negative durations, and every completed build has test results. A suite that
  loses more than 10% of its results from one build to the next only **warns**, because tests
  can be removed on purpose.
- **Freshness:** a warning after 1 day without ingestion, an error after 7.

**Evidence.** On a deliberately broken copy of the warehouse (a duplicated build, a missing
commit SHA, one build's unit results deleted), the matching checks failed, failed and warned.

## ADR-013: Orchestration and CI

**Status:** accepted

**Decision.**
- `noisefloor run` runs ingest, then `dbt build` (models, unit tests and every quality check),
  then freshness, then the report. It stops at the first failing step and exits with its code.
  A scheduler such as cron or Windows Task Scheduler can call it.
- CI on GitHub Actions runs lint, the Python tests and a full `dbt build` on an **empty**
  warehouse. GitHub can't reach the local Jenkins, but every model, unit test and quality
  check still runs.

**Alternatives.** A Makefile (not built into Windows). Dagster or Prefect running locally
(heavy for one linear pipeline).

## ADR-014: A static report and a generated README

**Status:** accepted

**Decision.**
- `noisefloor report` writes one static page into `site/`, with every number embedded as JSON
  from the metric tables. GitHub Actions publishes `site/` to GitHub Pages.
- The README's results section sits between two marker comments and is rewritten by the same
  command, so no result in it is typed by hand.
- Every report query has a complete sort order: rebuilding everything gives byte-identical
  output.
- Charts use Chart.js, pinned with an integrity hash. Each chart has a table with the same
  numbers, and the colours were checked for colour-vision deficiency in light and dark mode.
- The flip-rate chart skips days whose window holds fewer than 10 pairs of runs. One flip in a
  single pair would read as 100%; the table still lists every day.

**Alternatives.** Streamlit Community Cloud: interactive, but the app sleeps when idle, so
visitors wait for it to wake.

## ADR-015: Free tools only

**Status:** accepted

**Decision.** Everything is free and open source, and runs locally: Docker, Jenkins, Python, uv,
DuckDB, dbt-core and Chart.js. The only hosted services are GitHub's free tier for a public
repository: the repo itself, Actions and Pages. Nothing asks for payment details. dbt Cloud,
MotherDuck and cloud warehouses were avoided for that reason.
