from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from uuid import uuid4

from api_server.schemas import PipelineCreateRequest, StageRunInput
from api_server.services.pipeline_service import PipelineService
from api_server.services.stage_executor import StageExecutor
from api_server.stage_registry import StageRegistry
from api_server.storage.json_store import JsonPipelineStore


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
