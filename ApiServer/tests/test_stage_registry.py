from __future__ import annotations

from pathlib import Path

from api_server.stage_registry import StageRegistry, StageUnavailableError


def test_registry_marks_connected_and_placeholder_stages() -> None:
    registry = StageRegistry(Path(__file__).resolve().parents[2])

    availability = {stage.id: stage.available for stage in registry.list()}

    assert availability["requirements"] is True
    assert availability["solution"] is True
    assert availability["code"] is True
    assert availability["test"] is True
    assert availability["review"] is False
    assert availability["integration"] is True


def test_codetest_stage_runner_is_available() -> None:
    registry = StageRegistry(Path(__file__).resolve().parents[2])

    stage, runner = registry.runner_for("test")

    assert stage.id == "test"
    assert callable(runner)


def test_placeholder_stage_runner_is_unavailable() -> None:
    registry = StageRegistry(Path(__file__).resolve().parents[2])

    try:
        registry.runner_for("review")
    except StageUnavailableError as exc:
        assert "not connected" in str(exc)
    else:
        raise AssertionError("Expected review stage to be unavailable")


def test_registry_returns_next_stage() -> None:
    registry = StageRegistry(Path(__file__).resolve().parents[2])

    next_stage = registry.next_stage_after("requirements")

    assert next_stage is not None
    assert next_stage.id == "solution"
