from __future__ import annotations

import pytest

from api_server.engine.state_machine import TransitionError, can_transition, transition_run
from api_server.engine.models import PipelineRun


def test_state_machine_allows_queued_to_running() -> None:
    run = PipelineRun(pipeline_id="p1")
    assert can_transition(run.status, "running")
    transition_run(run, "running")
    assert run.status == "running"


def test_state_machine_rejects_illegal_transition() -> None:
    run = PipelineRun(pipeline_id="p1")
    with pytest.raises(TransitionError):
        transition_run(run, "succeeded")


def test_state_machine_allows_running_to_paused_and_back() -> None:
    run = PipelineRun(pipeline_id="p1")
    transition_run(run, "running")
    transition_run(run, "paused")
    assert run.status == "paused"
    transition_run(run, "running")
    assert run.status == "running"
