from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from api_server.bootstrap import ensure_repo_paths

ensure_repo_paths()

from stage_contracts import ArtifactRef, StageError


class PipelineDefinitionError(ValueError):
    pass


class AgentDefinition(BaseModel):
    id: str
    name: str
    role: str | None = None
    system_prompt: str | None = None
    accepted_input_artifact_types: list[str] = Field(default_factory=list)
    output_artifact_contract: dict[str, Any] = Field(default_factory=dict)
    input_contract: dict[str, Any] = Field(default_factory=dict)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    context_paths: list[str] = Field(default_factory=list)
    default_provider: str | None = None
    default_model: str | None = None
    provider: str | None = None
    model: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class StageDefinition(BaseModel):
    id: str
    name: str
    agent_ids: list[str] = Field(default_factory=list)
    module: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    checkpoint: bool = False
    checkpoint_label: str | None = None
    checkpoint_description: str | None = None
    description: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @property
    def available(self) -> bool:
        return bool(self.module)


class PipelineDefinition(BaseModel):
    id: str
    name: str
    version: str
    stages: list[StageDefinition] = Field(default_factory=list)
    agents: list[AgentDefinition] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)

    def stage_by_id(self, stage_id: str) -> StageDefinition:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        raise KeyError(stage_id)

    def agent_by_id(self, agent_id: str) -> AgentDefinition:
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        raise KeyError(agent_id)


class PipelineRun(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    pipeline_id: str
    pipeline_definition_id: str | None = None
    status: str = "queued"
    stage_order: list[str] = Field(default_factory=list)
    current_stage_id: str | None = None
    next_stage_id: str | None = None
    completed_stage_ids: list[str] = Field(default_factory=list)
    failed_stage_id: str | None = None
    rejected_stage_id: str | None = None
    pause_requested: bool = False
    terminate_requested: bool = False
    artifact_refs_by_stage: dict[str, list[ArtifactRef]] = Field(default_factory=dict)
    pending_input_artifacts_by_stage: dict[str, list[ArtifactRef]] = Field(default_factory=dict)
    checkpoint_ids: list[str] = Field(default_factory=list)
    error: StageError | None = None
    logs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    ended_at: datetime | None = None


CheckpointStatus = Literal["pending", "approved", "rejected"]


class CheckpointRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    pipeline_id: str = ""
    run_id: str | None = None
    pipeline_run_id: str | None = None
    stage_id: str
    status: CheckpointStatus = "pending"
    title: str
    description: str | None = None
    reviewer: str | None = None
    comment: str | None = None
    reason: str | None = None
    reject_reason: str | None = None
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: datetime | None = None
    rerun_stage_id: str | None = None
    reject_artifact: ArtifactRef | None = None

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if data.get("run_id") is None and data.get("pipeline_run_id"):
            data["run_id"] = data["pipeline_run_id"]
        if data.get("pipeline_run_id") is None and data.get("run_id"):
            data["pipeline_run_id"] = data["run_id"]
        if data.get("reject_reason") is None and data.get("reason"):
            data["reject_reason"] = data["reason"]
        if data.get("reason") is None and data.get("reject_reason"):
            data["reason"] = data["reject_reason"]
        data.setdefault("title", data.get("stage_id", "Checkpoint"))
        return data
