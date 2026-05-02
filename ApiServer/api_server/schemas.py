from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from api_server.bootstrap import ensure_repo_paths

ensure_repo_paths()

from stage_contracts import ArtifactRef, StageError, StageRunResult, StageStatus


PipelineStatus = Literal[
    "queued",
    "running",
    "pending_approval",
    "succeeded",
    "failed",
    "rejected",
    "cancelled",
]


class StageDefinitionResponse(BaseModel):
    id: str
    name: str
    agent: str
    checkpoint: bool = False
    description: str | None = None
    available: bool = True


class PipelineCreateRequest(BaseModel):
    name: str = "AI DevFlow Pipeline"
    requirement: str
    pipeline_id: str | None = None
    provider: str = "local"
    repo_path: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class StageRunInput(BaseModel):
    run_id: str | None = None
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    repo_path: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class PipelineRunInput(BaseModel):
    start_stage_id: str | None = None
    repo_path: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    reviewer: str | None = None
    comment: str | None = None
    continue_pipeline: bool = False


class StageRecord(BaseModel):
    id: str
    name: str
    agent: str
    status: StageStatus = "queued"
    checkpoint: bool = False
    checkpoint_label: str | None = None
    checkpoint_description: str | None = None
    run_id: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int = 0
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    output_artifacts: list[ArtifactRef] = Field(default_factory=list)
    human_output: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)
    error: StageError | None = None

    @classmethod
    def from_stage_result(cls, *, current: "StageRecord", result: StageRunResult) -> "StageRecord":
        return cls(
            id=current.id,
            name=current.name,
            agent=current.agent,
            checkpoint=current.checkpoint,
            checkpoint_label=current.checkpoint_label,
            checkpoint_description=current.checkpoint_description,
            status=result.status,
            run_id=result.run_id,
            started_at=result.started_at,
            ended_at=result.ended_at,
            duration_ms=result.duration_ms,
            input_artifacts=result.input_artifacts,
            output_artifacts=result.output_artifacts,
            human_output=result.human_output,
            data=result.data,
            logs=result.logs,
            error=result.error,
        )


class PipelineRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    status: PipelineStatus = "queued"
    provider: str = "local"
    requirement: str
    repo_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    options: dict[str, Any] = Field(default_factory=dict)
    stages: list[StageRecord] = Field(default_factory=list)


class ArtifactListResponse(BaseModel):
    pipeline_id: str
    stage_id: str
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    standard_artifacts: dict[str, str | None] = Field(default_factory=dict)


class ArtifactTextResponse(BaseModel):
    path: str
    content: str
