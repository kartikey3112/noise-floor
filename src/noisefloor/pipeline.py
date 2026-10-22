"""Run the whole pipeline in order, stopping at the first step that fails.

    1. ingest       new Jenkins builds -> landing files -> raw tables
    2. transform    dbt build: seeds, models, unit tests and data-quality checks
    3. freshness    dbt source freshness: has ingestion loaded anything recently?

dbt lives in its own Python 3.13 environment (decision D-030), so it's run as a separate
program: the dbt executable inside transform/.venv, created by `uv sync --project transform`.
"""

import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

TRANSFORM_DIR = Path("transform")


@dataclass(frozen=True)
class Step:
    name: str
    run: Callable[[], int]  # returns an exit code: 0 means success


def dbt_executable(transform_dir: Path = TRANSFORM_DIR) -> Path:
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    suffix = ".exe" if sys.platform == "win32" else ""
    path = transform_dir / ".venv" / scripts / f"dbt{suffix}"
    if not path.exists():
        raise SystemExit(f"dbt not found at {path}. Run `uv sync --project transform` first.")
    return path


def dbt(*args: str, warehouse: Path | None = None) -> int:
    """Run one dbt command against the warehouse; returns dbt's exit code."""
    env = dict(os.environ)
    if warehouse is not None:
        env["NOISEFLOOR_WAREHOUSE"] = str(warehouse.resolve())
    command = [str(dbt_executable()), *args, "--project-dir", str(TRANSFORM_DIR),
               "--profiles-dir", str(TRANSFORM_DIR)]  # fmt: skip
    return subprocess.run(command, env=env).returncode


def run_steps(steps: list[Step], log: Callable[[str], None] = print) -> int:
    """Run steps in order. Stops at the first non-zero exit code and returns it."""
    for number, step in enumerate(steps, start=1):
        log(f"\n=== Step {number}/{len(steps)}: {step.name}")
        code = step.run()
        if code != 0:
            log(f"=== Step '{step.name}' failed (exit code {code}). Later steps were not run.")
            return code
    log(f"\n=== All {len(steps)} steps passed.")
    return 0
