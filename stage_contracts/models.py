from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field
import traceback


StageStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "pending_approval",
    "rejected",
    "cancelled",
    "skipped",
]


class ArtifactRef(BaseModel):
    name: str
    type: str
    path: str
    role: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StageError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class StageRunRequest(BaseModel):
    pipeline_id: str
    stage_id: str
    run_id: str
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    output_dir: str
    repo_path: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class StageRunResult(BaseModel):
    pipeline_id: str
    stage_id: str
    run_id: str
    status: StageStatus
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    output_artifacts: list[ArtifactRef] = Field(default_factory=list)
    human_output: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)
    error: StageError | None = None

    @classmethod
    def from_exception(
        cls,
        *,
        request: StageRunRequest,
        started_at: datetime,
        exc: Exception,
        logs: list[str] | None = None,
    ) -> "StageRunResult":
        ended_at = datetime.now(timezone.utc)
        return cls(
            pipeline_id=request.pipeline_id,
            stage_id=request.stage_id,
            run_id=request.run_id,
            status="failed",
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=_duration_ms(started_at, ended_at),
            input_artifacts=request.input_artifacts,
            logs=logs or [],
            error=StageError(
                code=exc.__class__.__name__,
                message=str(exc),
                details={"traceback": "".join(traceback.format_exception(exc))},
            ),
        )


def _duration_ms(started_at: datetime, ended_at: datetime) -> int:
    return max(0, int((ended_at - started_at).total_seconds() * 1000))
