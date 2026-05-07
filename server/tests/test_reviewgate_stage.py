from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from uuid import uuid4

from api_server.schemas import PipelineCreateRequest, StageRunInput
from api_server.services.pipeline_service import PipelineService
from api_server.services.stage_executor import StageExecutor
from api_server.stage_registry import StageRegistry
from api_server.storage.json_store import JsonPipelineStore
from stage_contracts import ArtifactRef, StageRunRequest


def test_reviewgate_stage_runs_local_only_from_api_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)

    paths = _write_review_inputs(tmp_root)
    registry = StageRegistry(repo_root)
    _, runner = registry.runner_for("review")
    request = StageRunRequest(
        pipeline_id="reviewgate-demo",
        stage_id="review",
        run_id=paths["task_id"],
        input_artifacts=_input_artifacts(paths),
        output_dir=str(tmp_root / "artifacts"),
        options={"local_only": True},
    )

    try:
        result = runner(request)

        artifact_names = {artifact.name for artifact in result.output_artifacts}
        assert result.status == "pending_approval"
        assert result.data["verdict"] == "approved_with_notes"
        assert result.data["test_status"] == "passed"
        assert {"review_result", "review_report", "feedback_review", "human_output"} <= artifact_names
        assert (tmp_root / "artifacts" / "reviewgate-demo" / "review" / "manifest.json").exists()
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_pipeline_service_can_run_reviewgate_stage() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)

    paths = _write_review_inputs(tmp_root)
    registry = StageRegistry(repo_root)
    store = JsonPipelineStore(tmp_root / "store")
    service = PipelineService(
        store=store,
        registry=registry,
        executor=StageExecutor(registry),
        artifacts_root=str(tmp_root / "artifacts"),
    )

    try:
        pipeline = service.create(
            PipelineCreateRequest(
                pipeline_id="reviewgate-api-demo",
                requirement="demo",
                options={"local_only": True},
            )
        )
        updated = asyncio.run(
            service.run_stage(
                pipeline.id,
                "review",
                StageRunInput(input_artifacts=_input_artifacts(paths)),
            )
        )
        review_stage = next(stage for stage in updated.stages if stage.id == "review")
        artifact_names = {artifact.name for artifact in review_stage.output_artifacts}

        assert review_stage.status == "pending_approval"
        assert updated.status == "pending_approval"
        assert "review_result" in artifact_names
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_reviewgate_stage_treats_soft_failed_codetest_as_passed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)

    paths = _write_review_inputs(
        tmp_root,
        test_payload={
            "task_id": "reviewgate-soft-pass",
            "status": "failed",
            "summary": "Selector mismatch in generated tests.",
            "soft_failed": True,
            "soft_fail_code": "TEST_GENERATION_MISMATCH",
            "validation_error_code": "TEST_GENERATION_MISMATCH",
            "environment_error_code": "",
            "errors": ["selector mismatch"],
        },
    )
    registry = StageRegistry(repo_root)
    _, runner = registry.runner_for("review")
    request = StageRunRequest(
        pipeline_id="reviewgate-soft-pass-demo",
        stage_id="review",
        run_id=paths["task_id"],
        input_artifacts=_input_artifacts(paths),
        output_dir=str(tmp_root / "artifacts"),
        options={"local_only": False},
    )

    try:
        result = runner(request)

        assert result.status == "pending_approval"
        assert result.data["test_status"] == "passed"
        assert result.data["verdict"] == "approved_with_notes"
        assert result.data["review_status"] == "approved_with_notes"
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def _write_review_inputs(tmp_root: Path, test_payload: dict[str, object] | None = None) -> dict[str, str]:
    task_id = "reviewgate-local-only"
    design_path = tmp_root / "technical_design.md"
    diff_path = tmp_root / "code_changes.diff"
    codegen_result_path = tmp_root / "codegen_result.json"
    test_result_path = tmp_root / "code_test_result.json"

    design_path.write_text("# Technical Design\n\nImplement a simple change.\n", encoding="utf-8")
    diff_path.write_text(
        "diff --git a/src/app.py b/src/app.py\n"
        "--- a/src/app.py\n"
        "+++ b/src/app.py\n"
        "@@ -1 +1 @@\n"
        "-print('old')\n"
        "+print('new')\n",
        encoding="utf-8",
    )
    codegen_result_path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "technical_design_path": str(design_path),
                "diff_path": str(diff_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    payload = test_payload or {
        "task_id": task_id,
        "status": "passed",
        "summary": "Tests passed.",
        "stdout_tail": "",
        "stderr_tail": "",
    }
    test_result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "task_id": task_id,
        "design_path": str(design_path),
        "diff_path": str(diff_path),
        "codegen_result_path": str(codegen_result_path),
        "test_result_path": str(test_result_path),
    }


def _input_artifacts(paths: dict[str, str]) -> list[ArtifactRef]:
    return [
        ArtifactRef(name="technical_design", type="markdown", path=paths["design_path"], role="handoff"),
        ArtifactRef(name="code_changes", type="diff", path=paths["diff_path"], role="handoff"),
        ArtifactRef(name="codegen_result", type="json", path=paths["codegen_result_path"], role="machine"),
        ArtifactRef(name="code_test_result", type="json", path=paths["test_result_path"], role="machine"),
    ]
