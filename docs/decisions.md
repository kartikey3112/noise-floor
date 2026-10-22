# Decision log

Each entry records what was decided, the options considered, the choice, and why.

---

## D-001: Source of test data

- **Date:** 2026-10-22
- **Options considered:**
  1. A well-known open-source Python project.
  2. A real project taken from a published flaky-test research dataset.
  3. A new, purpose-built demo app (in this repo, or in its own repo).
  4. CrashCart (github.com/kartikey3112/crash-cart), extended with demo tests.
- **Chosen:** 4. CrashCart.
- **Why:** CrashCart is an existing personal project with 394 tests and JUnit output. It already
  has a pattern for deliberate, switchable defects. Adding clearly labelled demo tests gives
  real test data plus a known answer key for flaky and slow tests.

## D-002: Keep CrashCart's own CI unaffected

- **Date:** 2026-10-22
- **Chosen:** Demo tests that are flaky or slow on purpose stay switched off by default. They
  live in their own folder and run only when an environment variable is set, which only
  Jenkins sets.
- **Why:** CrashCart's GitHub Actions run and its public dashboard must keep reporting the
  real suite only.

## D-003: Demo changes live on a separate branch

- **Date:** 2026-10-22
- **Options considered:** commit to `main`, or use a separate branch.
- **Chosen:** a separate branch, `noisefloor-demo`, created from `main` at `ac7703e` and pushed
  to GitHub.
- **Why:** it keeps the `main` history clean. CrashCart's workflow triggers on pushes to `main`
  only, so pushes to this branch don't start a GitHub Actions run.

## D-004: Which CrashCart suites Jenkins runs

- **Date:** 2026-10-22
- **Options considered:** every suite (unit, API, UI, perf), or a lighter subset.
- **Chosen:** the backend unit tests, the API suite against a backend started inside the Jenkins
  job, and the new demo tests. The UI and perf suites are left out.
- **Why:** UI needs browsers and a Node build, and perf needs Java and JMeter. Both add a lot of
  setup for few extra tests (32 UI, 4 perf).

## D-005: Meaning of "suite" in test identity

- **Date:** 2026-10-22
- **Options considered:** the JUnit `testsuite` name, or the test layer.
- **Chosen:** the test layer: `unit`, `api` or `demo`. Example identity:
  `(api, tests.api.test_cart, test_update_quantity)`.
- **Why:** pytest writes `pytest` as the suite name for every test, so that field tells tests
  apart by nothing.

## D-006: No automatic retries in Jenkins

- **Date:** 2026-10-22
- **Options considered:** one retry per failed test (as CrashCart's UI suite does), or none.
- **Chosen:** no retries.
- **Why:** each execution stays one clean result. Flakiness then shows up across builds, which is
  exactly what the metrics measure.

## D-007: How Jenkins gets the CrashCart code

- **Date:** 2026-10-22
- **Options considered:** mount the local folder read-only, or clone from GitHub.
- **Chosen:** clone the `noisefloor-demo` branch from GitHub.
- **Why:** it's closer to a real CI setup. The branch was pushed on 2026-10-22.

## D-008: Noisefloor's role next to CrashCart

- **Date:** 2026-10-22
- **Context:** CrashCart's own results pipeline already reports same-commit conflicts and a 30-day
  flip rate.
- **Chosen:** Noisefloor is the data-engineering layer CrashCart doesn't have: Jenkins as the
  source, incremental loading, a star schema, transformations, data-quality checks and per-test
  runtime regression. The README will explain how it relates to CrashCart's flaky-test page.
- **Why:** it avoids repeating CrashCart's work and keeps the focus on data-engineering skills.

## D-009: Spreading build history over 30 days

- **Date:** 2026-10-22
- **Options considered:** running builds on a schedule for several weeks, or a labelled time
  offset.
- **Chosen:** a clearly labelled time offset, stored in its own column next to the real build
  time. The real timestamp is never overwritten.
- **Why:** every build we trigger gets today's date, so a 30-day window would otherwise hold
  only one day. The offset shows the window working in one sitting, and anyone can see what
  was simulated.

## D-010: Warehouse

- **Date:** 2026-10-22
- **Options considered:** DuckDB, PostgreSQL in Docker, SQLite, ClickHouse in Docker. Ruled out
  MotherDuck and the Snowflake trial (both can bill) and the BigQuery sandbox (cloud-only, and
  tables expire).
- **Chosen:** DuckDB.
- **Why:** it's a single file with no server, fast window functions for flip rate and rolling
  medians, and a mature dbt adapter. The data size (thousands of rows) doesn't need a server.

## D-011: Transformations

- **Date:** 2026-10-22
- **Options considered:** dbt-core, or plain SQL and Python.
- **Chosen:** dbt-core with the dbt-duckdb adapter.
- **Why:** it gives tests, docs and dependency ordering out of the box, and it's the industry
  standard. dbt Cloud (the paid product) is not used.

## D-012: Running the pipeline

- **Date:** 2026-10-22
- **Options considered:** a Python command-line tool, a Makefile, a local Dagster or Prefect.
- **Chosen:** a small Python command-line tool (for example `noisefloor run`).
- **Why:** it works the same on Windows, macOS and Linux. Make isn't built into Windows, and an
  orchestrator is heavy for this size.

## D-013: Runtime regression rule

- **Date:** 2026-10-22
- **Options considered:** rolling median and ratio, z-score, percentile.
- **Chosen:** rolling median and ratio. A run is a regression when its duration is more than
  1.5x the test's median over its previous 20 runs **and** at least 0.5 s longer.
- **Why:** the median isn't thrown off by one odd run. The 0.5 s floor stops tiny tests (say
  0.01 s to 0.02 s) from being flagged over noise.

## D-014: Report hosting

- **Date:** 2026-10-22
- **Options considered:** a static site on GitHub Pages, or Streamlit Community Cloud.
- **Chosen:** a static site on GitHub Pages.
- **Why:** it's free on a public repo and opens instantly with no account and no wake-up wait.

## D-015: Python version

- **Date:** 2026-10-22
- **Chosen:** Python 3.14 everywhere (Noisefloor and the Jenkins build environment).
- **Why:** it matches CrashCart. Open check: confirm dbt-core and dbt-duckdb install and run
  on 3.14 before relying on them. If they don't, raise it rather than switching silently.
- **Update 2026-10-22:** they don't. The dbt step uses Python 3.13 instead; see D-030.

## D-016: Counting skipped and error results

- **Date:** 2026-10-22
- **Chosen:** `error` counts as a fail. `skipped` is stored but ignored by every metric.
- **Example:** P, skip, F counts as one switch (P to F).
- **Why:** an error is still a broken execution. A skip tells us nothing about pass or fail.

## D-017: Which runs form a test's duration baseline

- **Date:** 2026-10-22
- **Chosen:** only passed runs count towards a test's normal duration.
- **Why:** a test that crashes early looks artificially fast. That would pull the median down
  and cause false regression alarms.

## D-018: Demo test design

- **Date:** 2026-10-22
- **Chosen:** about 10 tests in `tests/noisefloor_demo/` on the `noisefloor-demo` branch. They're
  skipped unless `NOISEFLOOR_DEMO=1`.
  - About 6 flaky tests with realistic causes (timing race, order dependence, random data, a
    slow fake service), each failing at a known rate.
  - About 4 tests that become slower from a known commit onward. Each slowdown is a real,
    small commit on the branch, for example "commit 5 makes `test_demo_search` slower".
    (Updated 2026-10-22: first proposed as tied to the build number, then changed to commits
    because real regressions come from code changes.)
  - Randomness is seeded from the build number, so rebuilding gives the same results.
  - An answer key, `expected.json`, lists what each demo test was designed to do.
- **Why:** it gives a known right answer for checking every metric, while the real CrashCart
  suites provide real data alongside.

## D-019: Package manager and project layout

- **Date:** 2026-10-22
- **Options considered:** pip with venv, or uv.
- **Chosen:** uv, with Python code in `src/noisefloor/`, tests in `tests/` and the dbt project in
  `transform/`.
- **Why:** uv is free, fast, can install Python 3.14 itself, and locks exact versions, so setup
  can be repeated exactly. The `src/` layout stops tests from importing code by accident
  without installing it.

## D-020: Container tool

- **Date:** 2026-10-22
- **Options considered:** Docker Desktop, Rancher Desktop, Docker Engine inside WSL.
- **Chosen:** Docker Desktop (with WSL 2).
- **Why:** it's the easiest install and the tool most guides assume. It's free for personal
  use with no card. A paid licence applies only to companies over 250 staff or $10M revenue.

## D-021: Jenkins setup

- **Date:** 2026-10-22
- **Chosen:**
  - Jenkins `2.580.1-lts-jdk21` and uv `0.12.23`, both pinned. Python 3.14 is installed in the
    image by uv.
  - Everything is configured from files (Configuration as Code plus a Job DSL job), with no
    setup wizard.
  - One executor. The port is bound to `127.0.0.1` only. The admin password comes from `.env`.
  - Each suite's JUnit file gets its own suite name (`unit`, `api`, `demo`) through pytest's
    `junit_suite_name` option. This puts the D-005 suite straight into the Jenkins test report.
- **Why:** a fresh start is fully repeatable from the README. One executor avoids port clashes
  and keeps timings comparable.
- **Plugin versions:** pinned after the first successful start. `plugins.lock.txt` lists all 69
  plugins with exact versions, and the image installs from it.

## D-022: Noisefloor repository

- **Date:** 2026-10-22
- **Chosen:** a public GitHub repository, `kartikey3112/noise-floor`, with `main` as the default
  branch.
- **Why:** on a free account, GitHub Pages only hosts sites from public repositories, and
  reviewers need to be able to read the code.

## D-023: Downloads during Docker builds

- **Date:** 2026-10-22
- **Context:** the command sandbox on the development machine blocked the image build from
  reaching `ghcr.io`.
- **Chosen:** run Docker build and start commands outside the sandbox, one approved command at
  a time.
- **Why:** the build has to download from several registries (Docker Hub, ghcr.io, Python
  builds, Jenkins plugins).

## D-024: Build history plan

- **Date:** 2026-10-22
- **Chosen:**
  - 15 builds on the base demo commit (`f8da8bd`), then 8 builds on each of the 4 slowdown
    commits, in commit order. 47 builds in total.
  - Run by `scripts/generate_history.py`, which uses only the standard library and can be
    re-run safely (it only starts the builds that are missing).
  - The first test build (#1, run on the last commit) was deleted, so history starts at build
    #2 and follows commit order.
- **Why:** 15 builds give every test a settled normal duration before the first slowdown. 8
  re-runs per commit give the flaky tests room to disagree on the same commit.

## D-025: Jenkins API token

- **Date:** 2026-10-22
- **Chosen:** scripts and ingestion authenticate with a Jenkins API token (`JENKINS_API_TOKEN`
  in `.env`), not the admin password.
- **Why:** a token can be revoked on its own, and it needs no CSRF crumb for POST requests.

## D-026: Raw landing layer

- **Date:** 2026-10-22
- **Options considered:** raw JSON files plus DuckDB, or DuckDB only.
- **Chosen:** both.
  - Each build and its test report are saved unchanged under `data/raw/jenkins/<job>/`
    (git-ignored), then loaded into DuckDB (`data/noisefloor.duckdb`), schema `raw`.
  - Tables: `raw.jenkins_builds` (one row per build), `raw.jenkins_test_cases` (one row per
    test execution), `raw.ingestion_runs` (one row per run).
  - `noisefloor reload-raw` rebuilds the raw tables from the files without asking Jenkins.
  - The raw tables declare no primary keys. Uniqueness is checked by the data-quality tests
    in Phase 5.
- **Why:** it's the standard landing-zone pattern. A bad load can be replayed from disk, and the
  raw layer accepts whatever the source sends.

## D-027: Incremental and idempotent ingestion

- **Date:** 2026-10-22
- **Chosen:**
  - Watermark = the highest build number already loaded. Only newer, finished builds are
    fetched, and loading stops at the first build still running.
  - Each build is written in one transaction: delete its rows, insert them again.
- **Example:** run 1 loaded builds #2 to #9. Run 2, straight after, loaded 0 builds and waited on
  #10, which was still running. Row counts didn't change.
- **Why:** without the stop rule, a running build could be skipped forever once a later build
  moved the watermark past it.

## D-028: What the raw layer keeps

- **Date:** 2026-10-22
- **Chosen:** values exactly as Jenkins reports them: real UTC start times and Jenkins' own test
  statuses (PASSED, FAILED, SKIPPED, and also FIXED and REGRESSED if they appear). The
  status mapping (D-016) and the 30-day time offset (D-009) are applied in the Phase 3 models,
  as separate, labelled columns.
- **Why:** the raw layer stays an exact, checkable copy of the source.

## D-029: Python tooling on the development machine

- **Date:** 2026-10-22
- **Chosen:** uv 0.12.23 installed for the current user with the system Python. Package
  downloads run outside the command sandbox, one approved command at a time, the same as
  D-023. Versions are locked in `uv.lock`.
- **Why:** uv inside the project's own environment would be removed by `uv sync`.

## D-030: Python version for dbt

- **Date:** 2026-10-22
- **Tested:**
  - dbt-core 1.11 + dbt-duckdb 1.11 on Python 3.14 fails at start-up (in its `mashumaro`
    dependency).
  - dbt-core 1.12 on 3.14 fails with a missing `metricflow` module.
  - dbt-core 1.11 on Python 3.13 works.
- **Options considered:** (a) Python 3.13 only for the dbt step, (b) the whole project on 3.13,
  (c) drop dbt for plain SQL, (d) keep trying dbt 1.12 on 3.14.
- **Chosen:** (a). `transform/` has its own locked uv environment on Python 3.13. Ingestion stays
  on 3.14. Both pin DuckDB 1.5.6, so they read the same database file.
- **Why:** dbt runs on an officially supported combination, and the rest of the project keeps
  3.14.

## D-031: Star schema

- **Date:** 2026-10-22
- **Chosen:**
  - Fact `fct_test_executions`: one row per test execution (one test case in one build), with
    keys to `dim_test`, `dim_build`, `dim_commit` and `dim_date`.
  - The fact holds `outcome`, `jenkins_status`, `duration_s`, `error_message`, simulated and
    real times, and `test_run_seq`.
  - `commit_key` sits on the fact directly, even though the build implies it, because the
    flaky rule is "same test, same commit".
  - Layers: staging (views), intermediate (views), marts (tables).
- **Why:** the grain matches the question being asked ("what happened to this test in this
  build"), and every metric is an aggregate over it.

## D-032: Simulated time formula

- **Date:** 2026-10-22
- **Chosen:** the newest build keeps its real start time, and each earlier build is placed 18
  hours before the next one (dbt var `simulated_build_spacing_hours`). The real time stays in
  `*_real_utc` columns.
- **Note:** simulated times are anchored to the newest build, so they shift whenever a new build
  arrives. Metrics are always recomputed in full, so results stay consistent for a given set of
  builds.
- **Why:** the ~46 builds span about 34 days, so the 30-day window visibly leaves the oldest
  builds out.

## D-033: Demo answer key as dbt seeds

- **Date:** 2026-10-22
- **Chosen:** `scripts/export_demo_seeds.py` copies `expected.json` and the demo commit subjects
  from CrashCart's `noisefloor-demo` branch into `transform/seeds/` (`demo_expected_tests.csv`,
  `demo_commits.csv`). The CSVs are committed.
- **Why:** Jenkins knows neither which tests were designed to be flaky or slow, nor the commit
  messages. Committing the seeds means a fresh clone needs no CrashCart.

## D-034: Surrogate keys

- **Date:** 2026-10-22
- **Chosen:** keys are the MD5 hash of the natural key columns joined with `|` (macro
  `surrogate_key`).
- **Why:** the same input always gives the same key, so full rebuilds never renumber rows, and
  no sequence state is needed.

## D-035: Metric details

- **Date:** 2026-10-22
- **Simulated time:** left as designed in D-032 (anchored to the newest build). The history is
  complete, so it won't shift unless new builds are added.
- **Edge cases, filled in while building (open to change):**
  - **Flip rate:** pairs of consecutive non-skipped executions. A pair counts in a day's
    window only if both of its executions fall in the 30 days ending at the end of that day.
    The test-level "current" value is the window ending on the last day with builds.
  - **Regression:** needs at least 5 earlier passed runs. Only passed runs are checked, and
    only passed runs form the baseline (D-017).
  - **Regression episodes:** consecutive flagged runs of one test form one episode. Its onset
    gives the commit where the slowdown started.
- **Tests:** 7 dbt unit tests on hand-made data with known answers, one or more per metric. With
  a deliberately wrong setting (floor 0.3 s instead of 0.5 s), the expected unit test fails.
- **Result on the full history:** all 11 demo tests detected as designed. 0 of the 268 real
  tests are flaky. Each slowdown is found on exactly its designed commit.

## D-036: Runtime spikes versus sustained regressions

- **Date:** 2026-10-22
- **Context:** 23 regression episodes in real API tests were mostly single slow runs. The API
  tests run 4 at a time, so their timings are noisy.
- **Options considered:** (1) keep the rule and label episodes by length, (2) count only
  sustained slowdowns (change D-013), (3) raise the thresholds.
- **Chosen:** (1).
  - Each episode gets `episode_kind`: `sustained` if it has 3 or more flagged runs in a row
    (dbt var `regression_sustained_min_runs`), otherwise `spike`.
  - `has_regressed` and the answer-key check count sustained episodes only.
- **Result:** API has 20 spikes and 3 sustained episodes (3 to 4 runs each). Demo has 4
  sustained episodes (8 to 11 runs) and no spikes.
- **Why:** it shows everything honestly, and doesn't tune the rule to fit this dataset.

## D-037: Data-quality checks

- **Date:** 2026-10-22
- **Chosen:** dbt tests, run by every `dbt build`:
  - **Uniqueness:** raw builds `(job, build)`, raw test cases `(job, build, case_index)`, the
    fact grain `(test_key, build_key)`, and every model's key.
  - **Nulls:** build number, start time and commit SHA. Suite, class and test name. Duration
    and outcome.
  - **Referential integrity:** every raw test case belongs to a raw build (a two-column key).
    Every fact row links to all four dimensions.
  - **Allowed values:** build results, Jenkins statuses, outcomes, episode kinds.
  - **Rules:** durations aren't negative, and every SUCCESS or UNSTABLE build has test
    results. A suite losing more than 10% of its results from one build to the next only
    warns, because tests can be removed on purpose.
  - **Freshness:** `dbt source freshness` on `raw.jenkins_builds` and `raw.ingestion_runs`.
    It warns after 1 day without ingestion and errors after 7.
- **Proof:** on a copy of the warehouse with a duplicated build, a missing commit SHA and one
  build's unit results deleted, the matching checks failed, failed and warned.
- **Why:** it covers the four kinds asked for (nulls, uniqueness, referential integrity,
  freshness), plus the failure modes most likely in this pipeline.

## D-038: Running the pipeline end to end

- **Date:** 2026-10-22
- **Chosen:** `noisefloor run` runs ingest, then `dbt build` (models, unit tests and every
  data-quality check), then `dbt source freshness`. It stops at the first failing step and
  exits with its code. dbt is called from its own environment (`transform/.venv`).
  `noisefloor transform` runs only the dbt step.
- **Scheduling (optional, free):** Windows Task Scheduler or cron can call `noisefloor run`.
  GitHub Actions can't reach the local Jenkins (D-014 context), so it isn't used for the
  pipeline.
- **Why:** one command, the same on every OS. A non-zero exit code makes it easy to schedule
  or wrap.

## D-039: The report

- **Date:** 2026-10-22
- **Chosen:**
  - One static page, written by `noisefloor report` (also step 4 of `noisefloor run`) into
    `site/`, with every number embedded as JSON from the metric tables. No number is typed by
    hand.
  - **Sections:** summary tiles, flaky tests with their 30-day flip rate and a trend chart,
    runtime regressions (sustained first, spikes listed separately) with a duration chart,
    and the answer-key scorecard.
  - **Charts:** Chart.js 4.5.1 from jsDelivr, pinned with an integrity hash, as in CrashCart.
    Every chart has a table with the same numbers.
  - **Colours:** colours follow the test in a fixed order, checked with a colour-vision
    validator in light and dark mode. Three light-mode colours are below 3:1 contrast, which
    the tables cover. Light and dark themes follow the system setting.
  - **Flip-rate chart:** skips days whose window holds fewer than 10 pairs of runs, because
    one flip in a single pair would read as 100%. The table still lists every day.
  - **Publishing:** `site/` is committed. `.github/workflows/pages.yml` publishes it to
    GitHub Pages on pushes that change it. One manual step: Settings > Pages > Source:
    GitHub Actions.
- **Why:** it's free, opens with one click, needs no server, and every number on it can be
  traced to a query.
