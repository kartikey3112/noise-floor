"""Read builds and test reports from the Jenkins JSON API."""

from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class BuildSummary:
    number: int
    building: bool


class BuildSource(Protocol):
    """What ingestion needs from Jenkins. Tests pass a fake with the same methods."""

    def list_builds(self) -> list[BuildSummary]: ...
    def get_build(self, number: int) -> dict: ...
    def get_test_report(self, number: int) -> dict | None: ...


class JenkinsClient:
    def __init__(self, url: str, user: str, token: str, job: str, timeout_s: float = 30) -> None:
        self.job = job
        # An API token works as the password in basic auth, and GET requests need no crumb.
        self._http = httpx.Client(base_url=url, auth=(user, token), timeout=timeout_s)

    def __enter__(self) -> "JenkinsClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self._http.close()

    def _get_json(self, path: str, **params: str) -> dict:
        response = self._http.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def list_builds(self) -> list[BuildSummary]:
        # allBuilds, not builds: the builds field stops at the newest 100.
        data = self._get_json(f"/job/{self.job}/api/json", tree="allBuilds[number,building]")
        return [BuildSummary(b["number"], b["building"]) for b in data["allBuilds"]]

    def get_build(self, number: int) -> dict:
        return self._get_json(f"/job/{self.job}/{number}/api/json")

    def get_test_report(self, number: int) -> dict | None:
        """The build's JUnit report, or None if it has none (e.g. it failed before tests ran)."""
        response = self._http.get(f"/job/{self.job}/{number}/testReport/api/json")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
