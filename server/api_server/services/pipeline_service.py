from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from uuid import uuid4

from api_server.engine.models import (
    AgentDefinition,
    PipelineDefinition,
    PipelineRun,
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
    sanitize_options,
)
from api_server.providers.resolver import resolve_llm_config
from api_server.services.stage_executor import StageExecutor
from api_server.stage_registry import StageDefinition as RegistryStageDefinition
from api_server.stage_registry import StageRegistry
from api_server.storage.json_store import JsonPipelineStore
from stage_contracts import ArtifactRef, StageError, StageRunRequest


class PipelineService:
    _REQANALYSIS_SANITIZE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
        # Keep behavior consistent with scripts/run_static_testdata_batch.py
        (re.compile(r"@playwright/test", re.IGNORECASE), "自动化浏览器测试依赖"),
        (re.compile(r"playwright", re.IGNORECASE), "自动化浏览器测试"),
    )

    def _sanitize_requirement_for_reqanalysis(self, text: str) -> str:
        """Normalize requirement input to satisfy ReqAnalysis input boundary checks.

        Keep the original requirement in the pipeline record; only sanitize the stage input.
        """
        out = str(text or "")
        for pattern, replacement in self._REQANALYSIS_SANITIZE_RULES:
            out = pattern.sub(replacement, out)
        return out

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
        self.checkpoint_service = None

    def create(self, request: PipelineCreateRequest) -> PipelineRecord:
        pipeline_id = request.pipeline_id or uuid4().hex
        stages = [self._stage_record(stage) for stage in self.registry.list()]
        pipeline = PipelineRecord(
            id=pipeline_id,
            name=request.name,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            stage_overrides=request.stage_overrides,
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

    def mirror_run_status_to_pipeline(self, run: PipelineRun) -> PipelineRecord:
        pipeline = self.store.get(run.pipeline_id)
        pipeline.latest_run_id = run.id
        status = run.status
        if status == "terminated":
            pipeline.status = "terminated"
        elif status == "paused":
            pipeline.status = "paused"
        elif status in {"queued", "running", "pending_approval", "succeeded", "failed", "rejected", "cancelled"}:
            pipeline.status = status  # type: ignore[assignment]
        else:
            pipeline.status = "running"
        return self.store.save(pipeline)

    async def run_stage(self, pipeline_id: str, stage_id: str, input_data: StageRunInput) -> PipelineRecord:
        pipeline = self.store.get(pipeline_id)
        stage_record = self._get_stage_record(pipeline, stage_id)
        self.registry.runner_for(stage_id)
        input_artifacts = self._merge_rerun_input_artifacts(
            stage_record,
            input_data.input_artifacts,
        )

        stage_record.status = "running"
        stage_record.started_at = datetime.now(timezone.utc)
        stage_record.logs = [*stage_record.logs, "Queued by API server", "Running stage"]
        pipeline.status = "running"
        self.store.save(pipeline)

        request = StageRunRequest(
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            run_id=input_data.run_id or f"{pipeline_id}-{stage_id}-{uuid4().hex[:8]}",
            input_artifacts=input_artifacts,
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
        if updated.status == "pending_approval":
            self._checkpoint_service().create_or_update_pending_checkpoint(pipeline, updated)
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
        merged = sanitize_options({**self._stage_definition_options(stage_id), **pipeline.options, **options})
        if stage_id == "requirements":
            sanitize_enabled = bool(merged.get("sanitize_requirement_for_reqanalysis", True))
            user_input = pipeline.requirement
            if sanitize_enabled:
                user_input = self._sanitize_requirement_for_reqanalysis(user_input)
            merged.setdefault("user_input", user_input)

        pipeline_definition = self._pipeline_definition()
        try:
            engine_stage = pipeline_definition.stage_by_id(stage_id)
            llm_config, agent_payload = resolve_llm_config(
                pipeline=pipeline,
                pipeline_definition=pipeline_definition,
                stage_definition=engine_stage,
                run_options=merged,
            )
            merged["llm"] = llm_config.to_safe_dict()
            merged.setdefault("use_real_llm", llm_config.use_real_llm)
            merged.setdefault("local_only", llm_config.local_only)
            merged["agents"] = agent_payload.get("agents", [])
            agents_val = merged["agents"]
            merged["agent"] = agents_val[0] if agents_val else None
        except Exception:
            logging.exception("Failed to resolve LLM config for stage %s — stage will run without LLM", stage_id)
            merged["llm"] = {"provider": "unknown", "local_only": True, "use_real_llm": False, "error": "LLM resolution failed"}
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

    def _checkpoint_service(self):
        if self.checkpoint_service is None:
            from api_server.services.checkpoint_service import CheckpointService

            self.checkpoint_service = CheckpointService(
                store=self.store,
                registry=self.registry,
                pipeline_service=self,
                artifacts_root=self.artifacts_root,
            )
        return self.checkpoint_service

    def _merge_rerun_input_artifacts(
        self,
        stage: StageRecord,
        input_artifacts: list[ArtifactRef],
    ) -> list[ArtifactRef]:
        merged = list(input_artifacts)
        for item in stage.data.get("rerun_input_artifacts") or []:
            try:
                artifact = item if isinstance(item, ArtifactRef) else ArtifactRef.model_validate(item)
            except Exception:
                continue
            if not any(self._artifact_key(existing) == self._artifact_key(artifact) for existing in merged):
                merged.append(artifact)
        return merged

    def _artifact_key(self, artifact: ArtifactRef) -> tuple[str, str]:
        return artifact.name, artifact.path

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
