from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from api_server.bootstrap import ensure_repo_paths

ensure_repo_paths()

from stage_contracts import ArtifactRef


class PipelineDefinitionError(ValueError):
    pass


class AgentDefinition(BaseModel):
    id: str
    name: str
    role: str | None = None
    system_prompt: str | None = None
    input_contract: dict[str, Any] = Field(default_factory=dict)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    context_paths: list[str] = Field(default_factory=list)
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
    pipeline_definition_id: str
    status: str = "queued"
    stage_order: list[str] = Field(default_factory=list)
    current_stage_id: str | None = None
    completed_stage_ids: list[str] = Field(default_factory=list)
    blocked_stage_ids: list[str] = Field(default_factory=list)
    artifact_refs_by_stage: dict[str, list[ArtifactRef]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


CheckpointStatus = Literal["pending", "approved", "rejected"]


class CheckpointRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    pipeline_run_id: str
    stage_id: str
    status: CheckpointStatus = "pending"
    reviewer: str | None = None
    reason: str | None = None
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: datetime | None = None
