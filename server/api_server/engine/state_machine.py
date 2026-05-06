from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


class TransitionError(ValueError):
    pass


PipelineRunStatus = str


TERMINAL_STATUSES: set[PipelineRunStatus] = {"succeeded", "terminated"}


_ALLOWED_TRANSITIONS: dict[PipelineRunStatus, set[PipelineRunStatus]] = {
    "queued": {"running", "terminated"},
    "running": {
        "paused",
        "pending_approval",
        "succeeded",
        "failed",
        "terminated",
    },
    "paused": {"running", "terminated"},
    "pending_approval": {"running", "rejected", "terminated"},
    "rejected": {"running", "terminated"},
    "failed": {"running", "terminated"},
    "succeeded": set(),
    "terminated": set(),
}


def can_transition(from_status: PipelineRunStatus, to_status: PipelineRunStatus) -> bool:
    allowed = _ALLOWED_TRANSITIONS.get(from_status)
    if allowed is None:
        return False
    return to_status in allowed


def assert_transition(from_status: PipelineRunStatus, to_status: PipelineRunStatus) -> None:
    if not can_transition(from_status, to_status):
        raise TransitionError(f"Illegal transition: {from_status} -> {to_status}")


@dataclass(frozen=True)
class TransitionReason:
    message: str | None = None


def transition_run(run, to_status: PipelineRunStatus, reason: str | None = None):
    assert_transition(run.status, to_status)

    now = datetime.now(timezone.utc)
    run.status = to_status
    run.updated_at = now
    if to_status == "running" and run.started_at is None:
        run.started_at = now
    if to_status in TERMINAL_STATUSES or to_status in {"failed", "rejected"}:
        if run.ended_at is None:
            run.ended_at = now
    if reason:
        logs = list(getattr(run, "logs", []) or [])
        logs.append(reason)
        setattr(run, "logs", logs)
    return run


def non_terminal_statuses() -> Iterable[PipelineRunStatus]:
    for status in _ALLOWED_TRANSITIONS:
        if status not in TERMINAL_STATUSES:
            yield status
