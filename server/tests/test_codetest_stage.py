from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from api_server.stage_registry import StageRegistry
from stage_contracts import ArtifactRef, StageRunRequest
from agents.code_testing import stage as codetest_stage


def test_codetest_stage_runs_local_only_from_codegen_result() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    source_repo = tmp_root / "source_repo"
    source_repo.mkdir(parents=True, exist_ok=True)
    (source_repo / "index-START.html").write_text(
        '<!doctype html><html><body><label><input type="checkbox"> Task</label></body></html>',
        encoding="utf-8",
    )
    design_path = tmp_root / "technical_design.md"
    diff_path = tmp_root / "code_changes.diff"
    codegen_result_path = tmp_root / "codegen_result.json"
    design_path.write_text("# Design\n", encoding="utf-8")
    diff_path.write_text("diff --git a/index-START.html b/index-START.html\n", encoding="utf-8")
    codegen_result_path.write_text(
        json.dumps(
            {
                "task_id": "codetest-local-only",
                "technical_design_path": str(design_path),
                "diff_path": str(diff_path),
                "codegen_repo_path": str(source_repo),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    registry = StageRegistry(repo_root)
    _, runner = registry.runner_for("test")
    request = StageRunRequest(
        pipeline_id="codetest-demo",
        stage_id="test",
        run_id="codetest-local-only",
        input_artifacts=[
            ArtifactRef(name="codegen_result", type="json", path=str(codegen_result_path), role="machine")
        ],
        output_dir=str(tmp_root / "artifacts"),
        options={"local_only": True},
    )

    try:
        result = runner(request)

        artifact_names = {artifact.name for artifact in result.output_artifacts}
        assert result.status == "succeeded"
        assert result.data["test_status"] == "not_run"
        assert {"code_test_result", "code_test_report", "test_run_log", "human_output"} <= artifact_names
        assert (tmp_root / "artifacts" / "codetest-demo" / "test" / "manifest.json").exists()
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_codetest_stage_soft_passes_non_critical_failure(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)
    design_path = tmp_root / "technical_design.md"
    diff_path = tmp_root / "code_changes.diff"
    repo_path = tmp_root / "repo"
    repo_path.mkdir(parents=True, exist_ok=True)
    design_path.write_text("# Design\n", encoding="utf-8")
    diff_path.write_text("diff --git a/a b/a\n", encoding="utf-8")

    fake_result = {
        "status": "failed",
        "summary": "Tests failed (exit 1). See log.",
        "errors": ["selector mismatch"],
        "local_only": False,
        "validation_error_code": "TEST_GENERATION_MISMATCH",
        "environment_error_code": "",
        "warnings": [],
    }

    monkeypatch.setattr(
        "code_testing.graph.run_codetest",
        lambda **kwargs: fake_result,  # noqa: ARG005
    )

    request = StageRunRequest(
        pipeline_id="codetest-demo",
        stage_id="test",
        run_id="codetest-soft-pass",
        input_artifacts=[],
        output_dir=str(tmp_root / "artifacts"),
        repo_path=str(repo_path),
        options={
            "design_path": str(design_path),
            "diff_path": str(diff_path),
            "repo_path": str(repo_path),
            "local_only": False,
        },
    )

    try:
        result = codetest_stage.run_stage(request)

        assert result.status == "succeeded"
        assert result.error is None
        assert result.data["soft_failed"] is True
        assert result.data["soft_fail_code"] == "TEST_GENERATION_MISMATCH"
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
