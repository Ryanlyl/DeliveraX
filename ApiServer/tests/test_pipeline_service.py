from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from api_server.schemas import PipelineCreateRequest, PipelineRunInput, StageRunInput
from api_server.services.pipeline_service import PipelineService
from api_server.services.stage_executor import StageExecutor
from api_server.stage_registry import StageDefinition, StageRegistry
from api_server.storage.json_store import JsonPipelineStore
from stage_contracts import ArtifactRef, StageRunRequest, StageRunResult


def test_pipeline_service_runs_requirements_stage() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)

    registry = StageRegistry(repo_root)
    store = JsonPipelineStore(tmp_root)
    service = PipelineService(
        store=store,
        registry=registry,
        executor=StageExecutor(registry),
        artifacts_root=str(tmp_root),
    )

    try:
        pipeline = service.create(
            PipelineCreateRequest(
                pipeline_id="service-demo",
                requirement="请生成一个任务列表页面需求，用户可以查看任务并标记完成。",
                options={"requires_approval": False},
            )
        )

        updated = asyncio.run(service.run_stage(pipeline.id, "requirements", StageRunInput()))
        requirements = next(stage for stage in updated.stages if stage.id == "requirements")

        assert requirements.status == "succeeded"
        assert any(artifact.name == "requirement_prd" for artifact in requirements.output_artifacts)
        assert (tmp_root / "service-demo" / "requirements" / "manifest.json").exists()
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_pipeline_run_passes_cumulative_artifacts_with_latest_first() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)
    captured_inputs: dict[str, list[str]] = {}

    class FakeRegistry:
        definitions = [
            StageDefinition(id="code", name="代码生成", agent="CodeGen", module="fake.code"),
            StageDefinition(id="test", name="代码测试", agent="CodeTest", module="fake.test"),
            StageDefinition(id="integration", name="交付集成", agent="Integration", module="fake.integration"),
        ]

        def list(self) -> list[StageDefinition]:
            return self.definitions

        def get(self, stage_id: str) -> StageDefinition:
            return next(stage for stage in self.definitions if stage.id == stage_id)

        def runner_for(self, stage_id: str):
            return self.get(stage_id), lambda request: request

    class FakeExecutor:
        async def run(self, request: StageRunRequest) -> StageRunResult:
            captured_inputs[request.stage_id] = [artifact.name for artifact in request.input_artifacts]
            outputs_by_stage = {
                "code": [ArtifactRef(name="codegen_result", type="json", path="codegen_result.json")],
                "test": [ArtifactRef(name="code_test_result", type="json", path="code_test_result.json")],
                "integration": [ArtifactRef(name="integration_result", type="json", path="integration_result.json")],
            }
            now = datetime.now(timezone.utc)
            return StageRunResult(
                pipeline_id=request.pipeline_id,
                stage_id=request.stage_id,
                run_id=request.run_id,
                status="succeeded",
                started_at=now,
                ended_at=now,
                duration_ms=0,
                input_artifacts=request.input_artifacts,
                output_artifacts=outputs_by_stage[request.stage_id],
            )

    service = PipelineService(
        store=JsonPipelineStore(tmp_root),
        registry=FakeRegistry(),  # type: ignore[arg-type]
        executor=FakeExecutor(),  # type: ignore[arg-type]
        artifacts_root=str(tmp_root),
    )

    try:
        pipeline = service.create(PipelineCreateRequest(pipeline_id="artifact-demo", requirement="demo"))

        asyncio.run(service.run_pipeline(pipeline.id, PipelineRunInput()))

        assert captured_inputs["code"] == []
        assert captured_inputs["test"] == ["codegen_result"]
        assert captured_inputs["integration"] == ["code_test_result", "codegen_result"]
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
