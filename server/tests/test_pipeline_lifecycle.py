from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from api_server.engine.runner import PipelineRunner
from api_server.engine.run_store import JsonPipelineRunStore
from api_server.schemas import PipelineCreateRequest, PipelineRunInput
from api_server.services.pipeline_service import PipelineService
from api_server.storage.json_store import JsonPipelineStore
from stage_contracts import ArtifactRef, StageRunRequest, StageRunResult


def _wait_until(predicate, timeout_s: float = 2.0) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("timeout")


def test_start_pause_resume_and_get_run() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)

    class FakeRegistry:
        definitions = [
            type("Def", (), {"id": "a", "name": "A", "agent": "X", "module": "fake.a", "depends_on": (), "checkpoint": False, "checkpoint_label": None, "checkpoint_description": None, "description": None})(),
            type("Def", (), {"id": "b", "name": "B", "agent": "X", "module": "fake.b", "depends_on": ("a",), "checkpoint": False, "checkpoint_label": None, "checkpoint_description": None, "description": None})(),
        ]

        def list(self):
            return self.definitions

        def get(self, stage_id: str):
            return next(s for s in self.definitions if s.id == stage_id)

        def runner_for(self, stage_id: str):
            return self.get(stage_id), lambda request: request

    class FakeExecutor:
        def __init__(self):
            self.calls: list[str] = []

        async def run(self, request: StageRunRequest) -> StageRunResult:
            self.calls.append(request.stage_id)
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
                output_artifacts=[ArtifactRef(name=f"{request.stage_id}_out", type="json", path=f"{request.stage_id}.json")],
            )

    store = JsonPipelineStore(tmp_root)
    service = PipelineService(
        store=store,
        registry=FakeRegistry(),  # type: ignore[arg-type]
        executor=FakeExecutor(),  # type: ignore[arg-type]
        artifacts_root=str(tmp_root),
    )
    runner = PipelineRunner(service=service, run_store=JsonPipelineRunStore(tmp_root))

    try:
        pipeline = service.create(PipelineCreateRequest(pipeline_id="life-demo", requirement="demo"))
        run = runner.start_run(pipeline.id, PipelineRunInput())

        _wait_until(lambda: runner.get_run(pipeline.id, run.id).status in {"running", "succeeded"})

        paused = runner.pause_run(pipeline.id, run.id)
        assert paused.pause_requested is True

        _wait_until(lambda: runner.get_run(pipeline.id, run.id).status in {"paused", "succeeded"})

        resumed = runner.resume_run(pipeline.id, run.id)
        assert resumed.pause_requested is False

        _wait_until(lambda: runner.get_run(pipeline.id, run.id).status == "succeeded")

        fetched = runner.get_run(pipeline.id, run.id)
        assert fetched.status == "succeeded"
        assert set(fetched.completed_stage_ids) == {"a", "b"}
    finally:
        import shutil

        shutil.rmtree(tmp_root, ignore_errors=True)


def test_pending_approval_blocks_and_resume_continues() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)

    class FakeRegistry:
        definitions = [
            type("Def", (), {"id": "a", "name": "A", "agent": "X", "module": "fake.a", "depends_on": (), "checkpoint": False, "checkpoint_label": None, "checkpoint_description": None, "description": None})(),
            type("Def", (), {"id": "b", "name": "B", "agent": "X", "module": "fake.b", "depends_on": ("a",), "checkpoint": False, "checkpoint_label": None, "checkpoint_description": None, "description": None})(),
        ]

        def list(self):
            return self.definitions

        def get(self, stage_id: str):
            return next(s for s in self.definitions if s.id == stage_id)

        def runner_for(self, stage_id: str):
            return self.get(stage_id), lambda request: request

    class FakeExecutor:
        async def run(self, request: StageRunRequest) -> StageRunResult:
            now = datetime.now(timezone.utc)
            status = "pending_approval" if request.stage_id == "a" else "succeeded"
            return StageRunResult(
                pipeline_id=request.pipeline_id,
                stage_id=request.stage_id,
                run_id=request.run_id,
                status=status,
                started_at=now,
                ended_at=now,
                duration_ms=0,
                input_artifacts=request.input_artifacts,
                output_artifacts=[],
            )

    store = JsonPipelineStore(tmp_root)
    service = PipelineService(
        store=store,
        registry=FakeRegistry(),  # type: ignore[arg-type]
        executor=FakeExecutor(),  # type: ignore[arg-type]
        artifacts_root=str(tmp_root),
    )
    runner = PipelineRunner(service=service, run_store=JsonPipelineRunStore(tmp_root))

    try:
        pipeline = service.create(PipelineCreateRequest(pipeline_id="approval-demo", requirement="demo"))
        run = runner.start_run(pipeline.id, PipelineRunInput())

        _wait_until(lambda: runner.get_run(pipeline.id, run.id).status == "pending_approval")

        # simulate manual approval by setting stage status in pipeline record
        p = service.get(pipeline.id)
        for stage in p.stages:
            if stage.id == "a":
                stage.status = "succeeded"
        store.save(p)

        runner.resume_run(pipeline.id, run.id)
        _wait_until(lambda: runner.get_run(pipeline.id, run.id).status in {"succeeded", "failed"}, timeout_s=3.0)
        final = runner.get_run(pipeline.id, run.id)
        assert final.status == "succeeded", f"final={final.status} stage={final.current_stage_id} logs={final.logs}"
    finally:
        import shutil

        shutil.rmtree(tmp_root, ignore_errors=True)
