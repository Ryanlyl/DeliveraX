from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from api_server.schemas import (
    PipelineCreateRequest,
    PipelineRecord,
    PipelineRunInput,
    PipelineStatus,
    StageRecord,
    StageRunInput,
)
from api_server.services.stage_executor import StageExecutor
from api_server.stage_registry import StageDefinition, StageRegistry
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
        start_index = self._stage_index(pipeline, input_data.start_stage_id) if input_data.start_stage_id else 0
        previous_artifacts: list[ArtifactRef] = []
        if start_index > 0:
            for previous_stage in reversed(pipeline.stages[:start_index]):
                previous_artifacts.extend(previous_stage.output_artifacts)
        stage_order = [stage.id for stage in pipeline.stages[start_index:]]

        for stage_id in stage_order:
            pipeline = self.store.get(pipeline_id)
            stage_record = self._get_stage_record(pipeline, stage_id)
            definition = self.registry.get(stage_id)
            if not definition.available:
                stage_record.status = "skipped"
                stage_record.logs = [*stage_record.logs, "Skipped because this stage is not connected yet"]
                pipeline.status = self._derive_status(pipeline)
                self.store.save(pipeline)
                continue

            pipeline = await self.run_stage(
                pipeline_id,
                stage_id,
                StageRunInput(
                    input_artifacts=previous_artifacts,
                    repo_path=input_data.repo_path or pipeline.repo_path,
                    options=input_data.options,
                ),
            )
            completed_stage = self._get_stage_record(pipeline, stage_id)
            previous_artifacts = [*completed_stage.output_artifacts, *previous_artifacts]
            if completed_stage.status in {"failed", "pending_approval", "rejected", "cancelled"}:
                break

        pipeline.status = self._derive_status(pipeline)
        return self.store.save(pipeline)

    def _stage_record(self, definition: StageDefinition) -> StageRecord:
        return StageRecord(
            id=definition.id,
            name=definition.name,
            agent=definition.agent,
            checkpoint=definition.checkpoint,
            checkpoint_label=definition.checkpoint_label,
            checkpoint_description=definition.checkpoint_description,
        )

    def _stage_options(self, pipeline: PipelineRecord, stage_id: str, options: dict) -> dict:
        merged = {**pipeline.options, **options}
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

    def _stage_index(self, pipeline: PipelineRecord, stage_id: str | None) -> int:
        if stage_id is None:
            return 0
        for index, stage in enumerate(pipeline.stages):
            if stage.id == stage_id:
                return index
        raise KeyError(stage_id)

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
