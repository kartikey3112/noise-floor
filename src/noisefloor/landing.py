"""The landing zone: Jenkins API responses saved to disk exactly as they arrived.

Layout:  <root>/<job>/builds/<number>.json          the build
         <root>/<job>/test_reports/<number>.json    its test report, or null if it had none

The raw tables in DuckDB can always be rebuilt from these files without asking Jenkins again.
"""

import json
from pathlib import Path


class Landing:
    def __init__(self, root: Path, job: str) -> None:
        self.builds_dir = root / job / "builds"
        self.reports_dir = root / job / "test_reports"

    def save(self, number: int, build: dict, report: dict | None) -> None:
        _write_json(self.builds_dir / f"{number}.json", build)
        _write_json(self.reports_dir / f"{number}.json", report)

    def load(self, number: int) -> tuple[dict, dict | None]:
        build = json.loads((self.builds_dir / f"{number}.json").read_text(encoding="utf-8"))
        report_path = self.reports_dir / f"{number}.json"
        if not report_path.exists():
            return build, None
        return build, json.loads(report_path.read_text(encoding="utf-8"))

    def build_numbers(self) -> list[int]:
        if not self.builds_dir.exists():
            return []
        return sorted(int(path.stem) for path in self.builds_dir.glob("*.json"))


def _write_json(path: Path, data: dict | None) -> None:
    # Write to a temporary file, then rename: an interrupted run never leaves half a file.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    temporary.replace(path)
