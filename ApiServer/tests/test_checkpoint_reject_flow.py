from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from api_server.schemas import CheckpointDecisionRequest, PipelineCreateRequest, StageRunInput
from api_server.services.checkpoint_service import CheckpointService
from api_server.services.pipeline_service import PipelineService
from api_server.stage_registry import StageDefinition
from api_server.storage.json_store import JsonPipelineStore
from stage_contracts import ArtifactRef, StageRunRequest, StageRunResult


def test_reject_checkpoint_marks_previous_stage_for_rerun_with_reason_artifact() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)

    class FakeRegistry:
        definitions = [
            StageDefinition(id="code", name="Code", agent="CodeGen", module="fake.code"),
            StageDefinition(id="test", name="Test", agent="CodeTest", module="fake.test", depends_on=("code",)),
            StageDefinition(
                id="review",
                name="Review",
                agent="ReviewGate",
                module="review_gate.stage",
                depends_on=("test",),
                checkpoint=True,
                checkpoint_label="代码评审确认",
                checkpoint_description="Confirm review.",
            ),
        ]

        def list(self) -> list[StageDefinition]:
            return self.definitions

        def get(self, stage_id: str) -> StageDefinition:
            return next(stage for stage in self.definitions if stage.id == stage_id)

        def runner_for(self, stage_id: str):
            return self.get(stage_id), lambda request: request

    store = JsonPipelineStore(tmp_root)
    registry = FakeRegistry()
    captured_inputs: dict[str, list[str]] = {}

    class FakeExecutor:
        async def run(self, request: StageRunRequest) -> StageRunResult:
            captured_inputs[request.stage_id] = [artifact.name for artifact in request.input_artifacts]
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
                output_artifacts=[
                    ArtifactRef(name="code_test_result", type="json", path="new-test-result.json")
                ],
            )

    service = PipelineService(
        store=store,
        registry=registry,  # type: ignore[arg-type]
        executor=FakeExecutor(),  # type: ignore[arg-type]
        artifacts_root=str(tmp_root),
    )
    checkpoint_service = CheckpointService(
        store=store,
        registry=registry,  # type: ignore[arg-type]
        pipeline_service=service,
        artifacts_root=tmp_root,
    )
    service.checkpoint_service = checkpoint_service

    try:
        pipeline = service.create(PipelineCreateRequest(pipeline_id="reject-demo", requirement="demo"))
        test_artifact_path = tmp_root / "reject-demo" / "test" / "code_test_result.json"
        test_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        test_artifact_path.write_text('{"status": "passed"}\n', encoding="utf-8")
        review_artifact_path = tmp_root / "reject-demo" / "review" / "review_result.json"
        review_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        review_artifact_path.write_text('{"verdict": "approved_with_notes"}\n', encoding="utf-8")

        pipeline = store.get(pipeline.id)
        code = next(stage for stage in pipeline.stages if stage.id == "code")
        test = next(stage for stage in pipeline.stages if stage.id == "test")
        review = next(stage for stage in pipeline.stages if stage.id == "review")
        code.status = "succeeded"
        test.status = "succeeded"
        test.output_artifacts = [
            ArtifactRef(name="code_test_result", type="json", path=str(test_artifact_path), role="machine")
        ]
        review.status = "pending_approval"
        review.output_artifacts = [
            ArtifactRef(name="review_result", type="json", path=str(review_artifact_path), role="machine")
        ]
        store.save(pipeline)

        current = checkpoint_service.get_current_checkpoint(pipeline.id)
        assert current.checkpoint is not None

        updated = checkpoint_service.reject(
            current.checkpoint.id,
            CheckpointDecisionRequest(
                reviewer="lead",
                reason="Please handle the edge case before integration.",
                continue_pipeline=False,
            ),
        )

        rejected_review = next(stage for stage in updated.stages if stage.id == "review")
        rerun_test = next(stage for stage in updated.stages if stage.id == "test")
        rerun_inputs = rerun_test.data["rerun_input_artifacts"]

        assert updated.status == "rejected"
        assert rejected_review.status == "rejected"
        assert rerun_test.status == "queued"
        assert rerun_test.data["rerun_required"] is True
        assert rerun_test.output_artifacts == []
        assert rerun_test.data["previous_output_artifacts"][0]["name"] == "code_test_result"
        assert rerun_inputs[0]["name"] == "reject_reason"
        assert Path(rerun_inputs[0]["path"]).exists()
        assert "Please handle the edge case" in Path(rerun_inputs[0]["path"]).read_text(encoding="utf-8")

        checkpoint = checkpoint_service._load(current.checkpoint.id)  # noqa: SLF001
        assert checkpoint.status == "rejected"
        assert checkpoint.reject_artifact is not None
        assert checkpoint.reject_artifact.name == "reject_reason"
        assert checkpoint.rerun_stage_id == "test"

        asyncio.run(service.run_stage(updated.id, "test", StageRunInput()))
        assert "reject_reason" in captured_inputs["test"]
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
