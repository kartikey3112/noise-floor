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
