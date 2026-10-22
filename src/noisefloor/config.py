"""Settings, read from environment variables, with a local .env file as a fallback."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    jenkins_url: str
    jenkins_user: str
    jenkins_token: str
    jenkins_job: str
    data_dir: Path

    @property
    def warehouse_path(self) -> Path:
        return self.data_dir / "noisefloor.duckdb"

    @property
    def landing_dir(self) -> Path:
        return self.data_dir / "raw" / "jenkins"


def read_env_file(path: Path) -> dict[str, str]:
    """KEY=value lines; blank lines and # comments are ignored. A missing file is empty."""
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def load_settings(env_file: Path = Path(".env")) -> Settings:
    # Real environment variables win over .env, so CI or a shell can override any value.
    values = {**read_env_file(env_file), **os.environ}
    missing = [key for key in ("JENKINS_ADMIN_USER", "JENKINS_API_TOKEN") if not values.get(key)]
    if missing:
        raise SystemExit(f"Missing settings: {', '.join(missing)}. See .env.example.")
    return Settings(
        jenkins_url=values.get("JENKINS_URL", "http://localhost:8080").rstrip("/"),
        jenkins_user=values["JENKINS_ADMIN_USER"],
        jenkins_token=values["JENKINS_API_TOKEN"],
        jenkins_job=values.get("NOISEFLOOR_JENKINS_JOB", "crashcart-tests"),
        data_dir=Path(values.get("NOISEFLOOR_DATA_DIR", "data")),
    )
