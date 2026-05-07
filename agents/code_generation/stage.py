from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from stage_contracts import (
    ArtifactRef,
    StageError,
    StageRunRequest,
    StageRunResult,
    resolve_stage_artifact_dir,
    write_stage_artifacts,
)

from .graph import run_codegen


HARD_ERROR_PATTERNS = (
    "path does not exist",
    "path escapes",
    "required",
    "missing",
    "not found",
    "unable to resolve",
    "refusing to",
)


def _is_hard_error(error_msg: str) -> bool:
    lowered = error_msg.lower()
    return any(pattern.lower() in lowered for pattern in HARD_ERROR_PATTERNS)


def _determine_status(errors: list[str], local_only: bool) -> str:
    if not errors:
        return "succeeded"
    if local_only:
        hard_errors = [e for e in errors if _is_hard_error(e)]
        return "failed" if hard_errors else "succeeded"
    return "failed"


def _build_stage_error(errors: list[str], warnings: list[str]) -> StageError | None:
    if not errors and not warnings:
        return None
    detail: dict = {}
    if errors:
        detail["errors"] = errors
    if warnings:
        detail["warnings"] = warnings
    code = "CODEGEN_ERRORS" if errors else "CODEGEN_WARNINGS"
    message = "; ".join(errors) if errors else "; ".join(warnings)
    return StageError(code=code, message=message, details=detail)


def _first_artifact_path(request: StageRunRequest, *names: str) -> str | None:
    wanted = set(names)
    for artifact in request.input_artifacts:
        if artifact.name in wanted:
            return artifact.path
    for artifact in request.input_artifacts:
        if artifact.type == "markdown":
            return artifact.path
    return None


def run_stage(request: StageRunRequest) -> StageRunResult:
    started_at = datetime.now(timezone.utc)
    repo_path_input = request.repo_path or request.options.get("repo_path")
    local_only = bool(request.options.get("local_only", True))
    logs = [
        "CodeGen stage started",
        f"repo_path from request: {repo_path_input or '(none)'}",
        f"local_only: {local_only}",
    ]
    try:
        repo_root = Path(__file__).resolve().parents[2]
        stage_dir = resolve_stage_artifact_dir(request)
        stage_dir.mkdir(parents=True, exist_ok=True)

        design_path = request.options.get("design_path") or _first_artifact_path(
            request, "technical_design", "human_output"
        )
        if not design_path:
            raise ValueError("CodeGen requires a technical design artifact or options.design_path.")
        logs.append(f"design_path: {design_path}")

        legacy_output_dir = stage_dir / "legacy_output"
        result_state = run_codegen(
            design_path=str(design_path),
            repo_path=repo_path_input,
            workspace_dir=str(
                request.options.get("workspace_dir")
                or repo_root / "agents" / "solution_design" / ".workspace"
            ),
            task_id=request.run_id,
            output_dir=str(legacy_output_dir),
            local_only=bool(request.options.get("local_only", True)),
            max_context_files=int(request.options.get("max_context_files", 32)),
            max_file_chars=int(request.options.get("max_file_chars", 24000)),
        )

        report_path = Path(result_state["report_path"])
        diff_path = Path(result_state["diff_path"])
        result_json_path = Path(result_state["result_json_path"])
        human_output = report_path.read_text(encoding="utf-8")
        output_artifacts = [
            ArtifactRef(name="code_changes", type="diff", path=str(diff_path), role="handoff"),
            ArtifactRef(name="codegen_report", type="markdown", path=str(report_path), role="display"),
            ArtifactRef(name="codegen_result", type="json", path=str(result_json_path), role="machine"),
        ]

        ended_at = datetime.now(timezone.utc)
        errors = result_state.get("errors", [])
        status = _determine_status(errors, local_only)
        logs.append(f"CodeGen status: {status} (errors={len(errors)}, warnings={len(result_state.get('warnings', []))})")
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
            human_output=human_output,
            data=dict(result_state),
            logs=[*logs, f"CodeGen report generated: {report_path}"],
            error=_build_stage_error(errors, result_state.get("warnings", [])),
        )
        return write_stage_artifacts(
            request=request,
            result=result,
            input_payload={"design_path": str(design_path), "options": request.options},
        )
    except Exception as exc:
        result = StageRunResult.from_exception(request=request, started_at=started_at, exc=exc, logs=logs)
        return write_stage_artifacts(request=request, result=result)
