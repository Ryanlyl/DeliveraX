from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import os

from stage_contracts import (
    ArtifactRef,
    StageError,
    StageRunRequest,
    StageRunResult,
    resolve_stage_artifact_dir,
    write_stage_artifacts,
)

def run_stage(request: StageRunRequest) -> StageRunResult:
    started_at = datetime.now(timezone.utc)
    logs = ["CodeTest stage started"]
    try:
        from code_testing.graph import run_codetest

        stage_dir = resolve_stage_artifact_dir(request)
        stage_dir.mkdir(parents=True, exist_ok=True)

        codegen_result_path = request.options.get("codegen_result_path") or _first_artifact_path(
            request,
            "codegen_result",
        )
        design_path = request.options.get("design_path") or _first_artifact_path(
            request,
            "technical_design",
            "human_output",
        )
        diff_path = request.options.get("diff_path") or _first_artifact_path(
            request,
            "code_changes",
        )
        requirement_path = request.options.get("requirement_path") or _first_artifact_path(
            request,
            "requirement_spec",
            "requirement_prd",
        )
        repair_feedback_path = request.options.get("repair_feedback_path") or _first_artifact_path(
            request,
            "feedback_to_codetest",
        )
        repo_path = request.options.get("repo_path") or request.repo_path

        if not codegen_result_path and not (design_path and diff_path and repo_path):
            raise ValueError(
                "CodeTest requires a codegen_result artifact/options.codegen_result_path, "
                "or design_path + diff_path + repo_path."
            )

        legacy_output_dir = stage_dir / "legacy_output"
        workspace_dir = Path(str(request.options.get("workspace_dir") or stage_dir / "workspace"))
        # Default to running real tests when invoked by pipeline.
        # Set options.local_only=true explicitly to skip execution.
        local_only = bool(request.options.get("local_only", False))
        force = bool(request.options.get("force", True))
        max_llm_calls = _optional_int(request.options.get("max_llm_calls"))

        # Optional: stage-level options to configure frontend autostart via env
        env_overrides: dict[str, str] = {}
        if "autostart_frontend" in request.options:
            env_overrides["CODETEST_AUTOSTART_FRONTEND"] = "1" if bool(request.options.get("autostart_frontend")) else "0"
        if request.options.get("frontend_host"):
            env_overrides["CODETEST_FRONTEND_HOST"] = str(request.options.get("frontend_host"))
        if request.options.get("frontend_port"):
            env_overrides["CODETEST_FRONTEND_PORT"] = str(request.options.get("frontend_port"))
        if request.options.get("frontend_start_timeout_seconds"):
            env_overrides["CODETEST_FRONTEND_START_TIMEOUT_SECONDS"] = str(request.options.get("frontend_start_timeout_seconds"))
        if request.options.get("frontend_warmup_seconds"):
            env_overrides["CODETEST_FRONTEND_WARMUP_SECONDS"] = str(request.options.get("frontend_warmup_seconds"))

        old_env: dict[str, str | None] = {}
        for k, v in env_overrides.items():
            old_env[k] = os.getenv(k)
            os.environ[k] = v

        result_state = run_codetest(
            codegen_result_path=str(codegen_result_path) if codegen_result_path else None,
            design_path=str(design_path) if design_path else None,
            diff_path=str(diff_path) if diff_path else None,
            repo_path=str(repo_path) if repo_path else None,
            requirement_path=str(requirement_path) if requirement_path else None,
            task_id=request.run_id,
            output_dir=str(legacy_output_dir),
            workspace_dir=str(workspace_dir),
            local_only=local_only,
            force=force,
            max_llm_calls=max_llm_calls,
            repair_feedback_path=str(repair_feedback_path) if repair_feedback_path else None,
        )
        for k, prev in old_env.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev

        report_path = Path(str(result_state.get("report_path", "")))
        human_output = report_path.read_text(encoding="utf-8") if report_path.is_file() else result_state.get("summary")
        output_artifacts = _build_output_artifacts(result_state, legacy_output_dir, request.run_id)
        legacy_status = str(result_state.get("status") or "").strip().lower()
        status = _map_status(legacy_status=legacy_status, local_only=bool(result_state.get("local_only")))
        errors = [str(item) for item in result_state.get("errors") or []]
        summary = str(result_state.get("summary") or "")

        ended_at = datetime.now(timezone.utc)
        error = None
        if status == "failed":
            error = StageError(
                code="CodeTestFailed",
                message=summary or "; ".join(errors) or "CodeTest failed.",
                details={"legacy_status": legacy_status, "errors": errors},
            )

        result = StageRunResult(
            pipeline_id=request.pipeline_id,
            stage_id=request.stage_id,
            run_id=request.run_id,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=max(0, int((ended_at - started_at).total_seconds() * 1000)),
            input_artifacts=request.input_artifacts,
            output_artifacts=output_artifacts,
            human_output=str(human_output) if human_output is not None else None,
            data=_build_data(result_state, legacy_status),
            logs=[
                *logs,
                f"CodeTest completed with legacy status: {legacy_status or 'unknown'}",
                summary,
            ],
            error=error,
        )
        return write_stage_artifacts(
            request=request,
            result=result,
            input_payload={
                "codegen_result_path": str(codegen_result_path) if codegen_result_path else None,
                "design_path": str(design_path) if design_path else None,
                "diff_path": str(diff_path) if diff_path else None,
                "repo_path": str(repo_path) if repo_path else None,
                "requirement_path": str(requirement_path) if requirement_path else None,
                "repair_feedback_path": str(repair_feedback_path) if repair_feedback_path else None,
                "options": request.options,
            },
        )
    except Exception as exc:
        result = StageRunResult.from_exception(request=request, started_at=started_at, exc=exc, logs=logs)
        return write_stage_artifacts(request=request, result=result)


def _first_artifact_path(request: StageRunRequest, *names: str) -> str | None:
    wanted = set(names)
    for artifact in request.input_artifacts:
        if artifact.name in wanted:
            return artifact.path
    return None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _map_status(*, legacy_status: str, local_only: bool) -> str:
    if local_only and legacy_status in {"test", "not_run", "skipped"}:
        return "succeeded"
    if legacy_status in {"passed", "pass", "ok", "success", "succeeded"}:
        return "succeeded"
    if legacy_status in {"cancelled", "skipped"}:
        return legacy_status
    return "failed"


def _build_output_artifacts(
    result_state: dict[str, Any],
    legacy_output_dir: Path,
    run_id: str,
) -> list[ArtifactRef]:
    legacy_task_dir = legacy_output_dir / run_id
    candidates = [
        ("code_test_result", "json", result_state.get("result_json_path"), "machine"),
        ("code_test_report", "markdown", result_state.get("report_path"), "display"),
        ("test_plan", "json", result_state.get("test_plan_path") or legacy_task_dir / "test_plan.json", "machine"),
        ("test_generation", "json", legacy_task_dir / "test_generation.json", "machine"),
        ("test_run_log", "text", result_state.get("log_path") or legacy_task_dir / "test_run.log", "log"),
    ]
    artifacts: list[ArtifactRef] = []
    for name, artifact_type, raw_path, role in candidates:
        if not raw_path:
            continue
        path = Path(str(raw_path))
        if not path.is_file():
            continue
        artifacts.append(ArtifactRef(name=name, type=artifact_type, path=str(path), role=role))
    return artifacts


def _build_data(result_state: dict[str, Any], legacy_status: str) -> dict[str, Any]:
    result_json_path = result_state.get("result_json_path")
    payload: dict[str, Any] = {}
    if result_json_path and Path(str(result_json_path)).is_file():
        try:
            payload = json.loads(Path(str(result_json_path)).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}

    test_status = "not_run" if result_state.get("local_only") else legacy_status
    return {
        **payload,
        "legacy_status": legacy_status,
        "test_status": test_status,
        "summary": result_state.get("summary", payload.get("summary", "")),
        "local_only": bool(result_state.get("local_only")),
        "exit_code": result_state.get("exit_code"),
        "duration_ms": result_state.get("duration_ms", payload.get("duration_ms", 0)),
        "generated_files": result_state.get("generated_files") or payload.get("generated_files", []),
        "warnings": result_state.get("warnings") or payload.get("warnings", []),
        "errors": result_state.get("errors") or payload.get("errors", []),
    }
