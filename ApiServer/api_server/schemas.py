from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from api_server.bootstrap import ensure_repo_paths

ensure_repo_paths()

from api_server.engine.models import CheckpointRecord, PipelineRun
from stage_contracts import ArtifactRef, StageError, StageRunResult, StageStatus


PipelineStatus = Literal[
    "queued",
    "running",
    "paused",
    "pending_approval",
    "succeeded",
    "failed",
    "rejected",
    "cancelled",
    "terminated",
]


_SENSITIVE_OPTION_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
}


def _is_sensitive_option_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized == "api_key_env":
        return False
    return (
        normalized in _SENSITIVE_OPTION_KEYS
        or normalized.endswith("_api_key")
        or normalized.endswith("_secret")
        or normalized.endswith("_token")
    )


def sanitize_options(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and _is_sensitive_option_key(key):
                continue
            clean[key] = sanitize_options(item)
        return clean
    if isinstance(value, list):
        return [sanitize_options(item) for item in value]
    return value


class StageDefinitionResponse(BaseModel):
    id: str
    name: str
    agent: str
    checkpoint: bool = False
    description: str | None = None
    available: bool = True


class LLMSelection(BaseModel):
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    local_only: bool | None = None
    use_real_llm: bool | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("options", mode="before")
    @classmethod
    def _sanitize_llm_options(cls, value: Any) -> Any:
        return sanitize_options(value or {})


class PipelineCreateRequest(BaseModel):
    name: str = "AI DevFlow Pipeline"
    requirement: str
    pipeline_id: str | None = None
    provider: str = "deepseek"
    model: str | None = None
    temperature: float | None = None
    stage_overrides: dict[str, LLMSelection] = Field(default_factory=dict)
    repo_path: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("options", mode="before")
    @classmethod
    def _sanitize_create_options(cls, value: Any) -> Any:
        return sanitize_options(value or {})


class StageRunInput(BaseModel):
    run_id: str | None = None
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    repo_path: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("options", mode="before")
    @classmethod
    def _sanitize_stage_run_options(cls, value: Any) -> Any:
        return sanitize_options(value or {})


class PipelineRunInput(BaseModel):
    start_stage_id: str | None = None
    repo_path: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("options", mode="before")
    @classmethod
    def _sanitize_pipeline_run_options(cls, value: Any) -> Any:
        return sanitize_options(value or {})


class ApprovalRequest(BaseModel):
    reviewer: str | None = None
    comment: str | None = None
    reason: str | None = None
    continue_pipeline: bool = False


class CheckpointDecisionRequest(BaseModel):
    reviewer: str | None = None
    comment: str | None = None
    reason: str | None = None
    continue_pipeline: bool = True


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
    provider: str = "deepseek"
    model: str | None = None
    temperature: float | None = None
    stage_overrides: dict[str, LLMSelection] = Field(default_factory=dict)
    requirement: str
    repo_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    options: dict[str, Any] = Field(default_factory=dict)
    latest_run_id: str | None = None
    stages: list[StageRecord] = Field(default_factory=list)

    @field_validator("options", mode="before")
    @classmethod
    def _sanitize_record_options(cls, value: Any) -> Any:
        return sanitize_options(value or {})


class ArtifactListResponse(BaseModel):
    pipeline_id: str
    stage_id: str
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    standard_artifacts: dict[str, str | None] = Field(default_factory=dict)


class ArtifactTextResponse(BaseModel):
    path: str
    content: str


class CurrentCheckpointResponse(BaseModel):
    pipeline_id: str
    run_id: str | None = None
    checkpoint: CheckpointRecord | None = None
    stage: StageRecord | None = None
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    human_output: str | None = None


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    detail: str | dict | None = None
    request_id: str | None = None


class ProviderPublicResponse(BaseModel):
    id: str
    name: str
    kind: str
    default_model: str | None = None
    default_base_url: str | None = None
    api_key_env: str | None = None
    available: bool
    configured: bool
    notes: str | None = None
    models: list[str] = Field(default_factory=list)


class ReviewAssetItem(BaseModel):
    path: str | None = None
    content: str | None = None


class ReviewAssetsResponse(BaseModel):
    pipeline_id: str
    stage_id: str
    human_output: ReviewAssetItem | None = None
    diff: ReviewAssetItem | None = None
    review_report: ReviewAssetItem | None = None
    artifacts: list[ArtifactRef] = Field(default_factory=list)
