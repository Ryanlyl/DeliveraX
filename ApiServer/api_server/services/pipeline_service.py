from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from api_server.engine.models import (
    AgentDefinition,
    PipelineDefinition,
    StageDefinition as EngineStageDefinition,
)
from api_server.engine.planner import collect_upstream_artifacts, topological_stage_order
from api_server.schemas import (
    PipelineCreateRequest,
    PipelineRecord,
    PipelineRunInput,
    PipelineStatus,
    StageRecord,
    StageRunInput,
)
from api_server.services.stage_executor import StageExecutor
from api_server.stage_registry import StageDefinition as RegistryStageDefinition
from api_server.stage_registry import StageRegistry
from api_server.storage.json_store import JsonPipelineStore
from stage_contracts import ArtifactRef, StageError, StageRunRequest


class PipelineService:
    def __init__(
        self,
        *,
        store: JsonPipelineStore,
        registry: StageRegistry,
        executor: StageExecutor,
        artifacts_root: str,
    ) -> None:
        self.store = store
        self.registry = registry
        self.executor = executor
        self.artifacts_root = artifacts_root

    def create(self, request: PipelineCreateRequest) -> PipelineRecord:
        pipeline_id = request.pipeline_id or uuid4().hex
        stages = [self._stage_record(stage) for stage in self.registry.list()]
        pipeline = PipelineRecord(
            id=pipeline_id,
            name=request.name,
            provider=request.provider,
            requirement=request.requirement,
            repo_path=request.repo_path,
            options=request.options,
            stages=stages,
        )
        return self.store.save(pipeline)

    def list(self) -> list[PipelineRecord]:
        return self.store.list()

    def get(self, pipeline_id: str) -> PipelineRecord:
        return self.store.get(pipeline_id)

    async def run_stage(self, pipeline_id: str, stage_id: str, input_data: StageRunInput) -> PipelineRecord:
        pipeline = self.store.get(pipeline_id)
        stage_record = self._get_stage_record(pipeline, stage_id)
        self.registry.runner_for(stage_id)

        stage_record.status = "running"
        stage_record.started_at = datetime.now(timezone.utc)
        stage_record.logs = [*stage_record.logs, "Queued by API server", "Running stage"]
        pipeline.status = "running"
        self.store.save(pipeline)

        request = StageRunRequest(
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            run_id=input_data.run_id or f"{pipeline_id}-{stage_id}-{uuid4().hex[:8]}",
            input_artifacts=input_data.input_artifacts,
            output_dir=self.artifacts_root,
            repo_path=input_data.repo_path or pipeline.repo_path,
            options=self._stage_options(pipeline, stage_id, input_data.options),
        )
        try:
            result = await self.executor.run(request)
        except Exception as exc:
            pipeline = self.store.get(pipeline_id)
            stage_record = self._get_stage_record(pipeline, stage_id)
            ended_at = datetime.now(timezone.utc)
            stage_record.status = "failed"
            stage_record.ended_at = ended_at
            if stage_record.started_at is not None:
                stage_record.duration_ms = max(
                    0,
                    int((ended_at - stage_record.started_at).total_seconds() * 1000),
                )
            stage_record.logs = [*stage_record.logs, f"Stage runner crashed: {exc}"]
            stage_record.error = StageError(code=exc.__class__.__name__, message=str(exc))
            pipeline.status = "failed"
            self.store.save(pipeline)
            raise

        pipeline = self.store.get(pipeline_id)
        stage_record = self._get_stage_record(pipeline, stage_id)
        updated = StageRecord.from_stage_result(current=stage_record, result=result)
        self._replace_stage_record(pipeline, updated)
        pipeline.status = self._derive_status(pipeline)
        self.store.save(pipeline)
        return pipeline

    async def run_pipeline(self, pipeline_id: str, input_data: PipelineRunInput) -> PipelineRecord:
        pipeline = self.store.get(pipeline_id)
        definition = self._pipeline_definition()
        full_stage_order = self._stage_order(pipeline, definition)
        start_index = (
            self._stage_index(full_stage_order, input_data.start_stage_id)
            if input_data.start_stage_id
            else 0
        )
        completed_artifacts = self._completed_artifacts_by_stage(
            pipeline,
            full_stage_order[:start_index],
        )
        stage_order = full_stage_order[start_index:]

        for stage_id in stage_order:
            pipeline = self.store.get(pipeline_id)
            stage_record = self._get_stage_record(pipeline, stage_id)
            definition = self.registry.get(stage_id)
            if not definition.available:
                stage_record.status = "skipped"
                stage_record.logs = [*stage_record.logs, "Skipped because this stage is not connected yet"]
                pipeline.status = self._derive_status(pipeline)
                self.store.save(pipeline)
                completed_artifacts[stage_id] = list(stage_record.output_artifacts)
                continue

            input_artifacts = collect_upstream_artifacts(
                stage_id,
                completed_artifacts,
                self._registry_pipeline_definition(),
            )
            pipeline = await self.run_stage(
                pipeline_id,
                stage_id,
                StageRunInput(
                    input_artifacts=input_artifacts,
                    repo_path=input_data.repo_path or pipeline.repo_path,
                    options=input_data.options,
                ),
            )
            completed_stage = self._get_stage_record(pipeline, stage_id)
            completed_artifacts[stage_id] = list(completed_stage.output_artifacts)
            if completed_stage.status in {"failed", "pending_approval", "rejected", "cancelled"}:
                break

        pipeline.status = self._derive_status(pipeline)
        return self.store.save(pipeline)

    def _stage_record(self, definition: RegistryStageDefinition) -> StageRecord:
        return StageRecord(
            id=definition.id,
            name=definition.name,
            agent=definition.agent,
            checkpoint=definition.checkpoint,
            checkpoint_label=definition.checkpoint_label,
            checkpoint_description=definition.checkpoint_description,
        )

    def _stage_options(self, pipeline: PipelineRecord, stage_id: str, options: dict) -> dict:
        merged = {**self._stage_definition_options(stage_id), **pipeline.options, **options}
        if stage_id == "requirements":
            merged.setdefault("user_input", pipeline.requirement)
        return merged

    def _get_stage_record(self, pipeline: PipelineRecord, stage_id: str) -> StageRecord:
        for stage in pipeline.stages:
            if stage.id == stage_id:
                return stage
        raise KeyError(stage_id)

    def _replace_stage_record(self, pipeline: PipelineRecord, updated: StageRecord) -> None:
        for index, stage in enumerate(pipeline.stages):
            if stage.id == updated.id:
                pipeline.stages[index] = updated
                return
        raise KeyError(updated.id)

    def _stage_index(self, stage_order: list[str], stage_id: str | None) -> int:
        if stage_id is None:
            return 0
        try:
            return stage_order.index(stage_id)
        except ValueError as exc:
            raise KeyError(stage_id) from exc

    def _stage_order(self, pipeline: PipelineRecord, definition: PipelineDefinition) -> list[str]:
        pipeline_stage_ids = {stage.id for stage in pipeline.stages}
        return [stage_id for stage_id in topological_stage_order(definition) if stage_id in pipeline_stage_ids]

    def _completed_artifacts_by_stage(
        self,
        pipeline: PipelineRecord,
        stage_order: list[str],
    ) -> dict[str, list[ArtifactRef]]:
        artifacts_by_stage: dict[str, list[ArtifactRef]] = {}
        for stage_id in stage_order:
            stage = self._get_stage_record(pipeline, stage_id)
            artifacts_by_stage[stage_id] = list(stage.output_artifacts)
        return artifacts_by_stage

    def _registry_pipeline_definition(self) -> PipelineDefinition | None:
        definition = getattr(self.registry, "pipeline_definition", None)
        if isinstance(definition, PipelineDefinition):
            return definition
        return None

    def _pipeline_definition(self) -> PipelineDefinition:
        definition = self._registry_pipeline_definition()
        if definition is not None:
            return definition
        return self._pipeline_definition_from_registry()

    def _pipeline_definition_from_registry(self) -> PipelineDefinition:
        agents: dict[str, AgentDefinition] = {}
        stages: list[EngineStageDefinition] = []
        for stage in self.registry.list():
            agent_id = stage.agent or f"{stage.id}_agent"
            if agent_id not in agents:
                agents[agent_id] = AgentDefinition(id=agent_id, name=stage.agent or agent_id)
            stages.append(
                EngineStageDefinition(
                    id=stage.id,
                    name=stage.name,
                    agent_ids=[agent_id] if agent_id else [],
                    module=stage.module,
                    depends_on=list(getattr(stage, "depends_on", ())),
                    checkpoint=stage.checkpoint,
                    checkpoint_label=stage.checkpoint_label,
                    checkpoint_description=stage.checkpoint_description,
                    description=stage.description,
                )
            )
        return PipelineDefinition(
            id="registry-derived",
            name="Registry Derived Pipeline",
            version="1.0.0",
            stages=stages,
            agents=list(agents.values()),
        )

    def _stage_definition_options(self, stage_id: str) -> dict:
        definition = self._registry_pipeline_definition()
        if definition is None:
            return {}
        try:
            return dict(definition.stage_by_id(stage_id).options)
        except KeyError:
            return {}

    def _derive_status(self, pipeline: PipelineRecord) -> PipelineStatus:
        statuses = [stage.status for stage in pipeline.stages]
        if any(status == "failed" for status in statuses):
            return "failed"
        if any(status == "rejected" for status in statuses):
            return "rejected"
        if any(status == "cancelled" for status in statuses):
            return "cancelled"
        if any(status == "pending_approval" for status in statuses):
            return "pending_approval"
        if any(status == "running" for status in statuses):
            return "running"
        if all(status in {"succeeded", "skipped"} for status in statuses):
            return "succeeded"
        return "queued"
