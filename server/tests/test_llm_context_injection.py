from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from uuid import uuid4

from api_server.engine.config_loader import load_default_pipeline_definition
from api_server.schemas import PipelineCreateRequest, StageRunInput
from api_server.services.pipeline_service import PipelineService
from api_server.services.stage_executor import StageExecutor
from api_server.stage_registry import StageRegistry
from api_server.storage.json_store import JsonPipelineStore
from stage_contracts.llm_runtime import get_current_llm_config


def test_stage_executor_sets_llm_context() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)

    captured: dict[str, str | None] = {"provider": None, "model": None}

    definition = load_default_pipeline_definition()

    async def fake_runner(request):
        cfg = get_current_llm_config()
        captured["provider"] = cfg.provider if cfg else None
        captured["model"] = cfg.model if cfg else None
        from stage_contracts import StageRunResult
        from datetime import datetime, timezone

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
            output_artifacts=[],
        )

    class FakeStageRegistry(StageRegistry):
        def __init__(self, repo_root: Path):
            super().__init__(repo_root, pipeline_definition=definition)

        def runner_for(self, stage_id: str):
            return self.get(stage_id), fake_runner

    registry = FakeStageRegistry(repo_root)

    try:
        service = PipelineService(
            store=JsonPipelineStore(tmp_root),
            registry=registry,
            executor=StageExecutor(registry),
            artifacts_root=str(tmp_root),
        )

        pipeline = service.create(
            PipelineCreateRequest(
                pipeline_id="ctx-demo",
                requirement="demo",
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.2,
            )
        )

        asyncio.run(service.run_stage(pipeline.id, "solution", StageRunInput(options={"requires_approval": False})))

        assert captured["provider"] == "openai"
        assert captured["model"] == "gpt-4o-mini"
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
