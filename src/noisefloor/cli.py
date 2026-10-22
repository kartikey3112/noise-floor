"""Command line: `noisefloor <command>`. Run `noisefloor --help` for the list."""

import argparse
import sys
from pathlib import Path

from noisefloor.config import load_settings
from noisefloor.ingest import ingest, reload_from_landing
from noisefloor.jenkins_client import JenkinsClient
from noisefloor.landing import Landing
from noisefloor.pipeline import Step, dbt, run_steps
from noisefloor.raw_store import RawStore
from noisefloor.report import build_site

SITE_DIR = Path("site")


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = load_settings(Path(args.env_file))
    landing = Landing(settings.landing_dir, settings.jenkins_job)
    store = RawStore.open(settings.warehouse_path)
    client = JenkinsClient(
        settings.jenkins_url, settings.jenkins_user, settings.jenkins_token, settings.jenkins_job
    )
    try:
        with client:
            result = ingest(client, landing, store, settings.jenkins_job)
        print(
            f"Loaded {len(result.loaded)} new builds ({result.test_cases_loaded} test results). "
            f"Watermark: build #{result.watermark_before} -> #{result.watermark_after}."
        )
        if result.waiting_on is not None:
            print(f"Build #{result.waiting_on} is still running; it and later ones load next time.")
        print(f"Raw row counts: {store.row_counts()}")
    finally:
        store.close()
    return 0


def cmd_reload_raw(args: argparse.Namespace) -> int:
    settings = load_settings(Path(args.env_file))
    landing = Landing(settings.landing_dir, settings.jenkins_job)
    store = RawStore.open(settings.warehouse_path)
    try:
        builds, cases = reload_from_landing(landing, store, settings.jenkins_job)
        print(f"Reloaded {builds} builds ({cases} test results) from {settings.landing_dir}.")
        print(f"Raw row counts: {store.row_counts()}")
    finally:
        store.close()
    return 0


def cmd_transform(args: argparse.Namespace) -> int:
    warehouse = load_settings(Path(args.env_file)).warehouse_path
    return dbt("build", warehouse=warehouse)


def cmd_report(args: argparse.Namespace) -> int:
    warehouse = load_settings(Path(args.env_file)).warehouse_path
    overview = build_site(warehouse, SITE_DIR, readme=Path("README.md"))
    print(
        f"Wrote {SITE_DIR / 'index.html'} and the README results: "
        f"{overview['flaky_tests']} flaky tests, "
        f"{overview['sustained_regressions']} sustained regressions, "
        f"answer key {overview['answer_key_matched']}/{overview['answer_key_total']}."
    )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    warehouse = load_settings(Path(args.env_file)).warehouse_path
    return run_steps(
        [
            Step("ingest new Jenkins builds", lambda: cmd_ingest(args)),
            Step(
                "build models and run all checks (dbt build)",
                lambda: dbt("build", warehouse=warehouse),
            ),
            Step(
                "check data freshness (dbt source freshness)",
                lambda: dbt("source", "freshness", warehouse=warehouse),
            ),
            Step("build the report site", lambda: cmd_report(args)),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="noisefloor", description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", default=".env", help="settings file (default: .env)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "ingest", help="fetch new finished Jenkins builds into the landing files and raw tables"
    ).set_defaults(handler=cmd_ingest)
    commands.add_parser(
        "reload-raw", help="rebuild the raw tables from the landing files, without Jenkins"
    ).set_defaults(handler=cmd_reload_raw)
    commands.add_parser(
        "transform", help="build the models and run every check (dbt build)"
    ).set_defaults(handler=cmd_transform)
    commands.add_parser(
        "report", help="build the static report site in site/ from the warehouse"
    ).set_defaults(handler=cmd_report)
    commands.add_parser(
        "run", help="the whole pipeline: ingest, transform and check, freshness, report"
    ).set_defaults(handler=cmd_run)
    args = parser.parse_args(argv)
    # Print each line as it's written, so our messages and dbt's output appear in order.
    sys.stdout.reconfigure(line_buffering=True)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
