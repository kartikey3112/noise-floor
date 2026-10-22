from noisefloor.pipeline import Step, run_steps


def recording_step(name: str, code: int, ran: list[str]) -> Step:
    def run() -> int:
        ran.append(name)
        return code

    return Step(name, run)


def test_all_steps_run_in_order_when_they_pass():
    ran: list[str] = []
    steps = [recording_step(n, 0, ran) for n in ("ingest", "transform", "freshness")]
    assert run_steps(steps, log=lambda _: None) == 0
    assert ran == ["ingest", "transform", "freshness"]


def test_a_failing_step_stops_the_later_ones_and_returns_its_code():
    """If a data-quality check fails in dbt build, nothing after it should run."""
    ran: list[str] = []
    steps = [
        recording_step("ingest", 0, ran),
        recording_step("transform", 1, ran),
        recording_step("freshness", 0, ran),
    ]
    assert run_steps(steps, log=lambda _: None) == 1
    assert ran == ["ingest", "transform"]
