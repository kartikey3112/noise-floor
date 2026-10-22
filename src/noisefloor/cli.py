"""Command line: `noisefloor <command>`. Run `noisefloor --help` for the list."""

import argparse
import sys
from pathlib import Path

from noisefloor.config import load_settings
from noisefloor.ingest import ingest, reload_from_landing
from noisefloor.jenkins_client import JenkinsClient
from noisefloor.landing import Landing
from noisefloor.raw_store import RawStore


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
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
