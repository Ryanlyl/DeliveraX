from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    logs = ["ReviewGate stage started"]
    try:
        from ReviewGate.agent.runner import run_codereview

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
        test_result_path = request.options.get("test_result_path") or _first_artifact_path(
            request,
            "code_test_result",
        )
        requirement_path = request.options.get("requirement_path") or _first_artifact_path(
            request,
            "requirement_spec",
            "requirement_prd",
        )
        policy_pack_path = request.options.get("policy_pack_path") or _first_artifact_path(
            request,
            "policy_pack",
        )

        if not test_result_path:
            raise ValueError("ReviewGate requires a code_test_result artifact or options.test_result_path.")

        legacy_output_dir = stage_dir / "legacy_output"
        result_state = run_codereview(
            codegen_result_path=str(codegen_result_path) if codegen_result_path else None,
            design_path_cli=str(design_path) if design_path else None,
            diff_path_cli=str(diff_path) if diff_path else None,
            test_result_path=str(test_result_path),
            requirement_path_cli=str(requirement_path) if requirement_path else None,
            task_id_cli=str(request.options.get("task_id") or request.run_id),
            output_dir=str(legacy_output_dir),
            policy_pack_path=str(policy_pack_path) if policy_pack_path else None,
            local_only=_bool_option(request.options, "local_only", False),
            max_llm_calls_override=_optional_int(request.options.get("max_llm_calls")),
        )

        review_status = str(result_state.get("status") or "").strip().lower()
        merge_recommendation = str(result_state.get("merge_recommendation") or "").strip().lower()
        output_artifacts = _build_output_artifacts(result_state)
        report_path = result_state.get("code_review_report_path")
        human_output = None
        if report_path and Path(str(report_path)).is_file():
            human_output = Path(str(report_path)).read_text(encoding="utf-8")
        else:
            human_output = str(result_state.get("summary") or "")

        status = _map_status(
            review_status=review_status,
            merge_recommendation=merge_recommendation,
            options=request.options,
        )
        ended_at = datetime.now(timezone.utc)
        error = _build_error(
            api_status=status,
            review_status=review_status,
            merge_recommendation=merge_recommendation,
            result_state=result_state,
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
            human_output=human_output,
            data={
                **dict(result_state),
                "review_status": review_status,
                "merge_recommendation": merge_recommendation,
            },
            logs=[
                *logs,
                f"ReviewGate completed with review status: {review_status or 'unknown'}",
                f"ReviewGate merge recommendation: {merge_recommendation or 'unknown'}",
                str(result_state.get("summary") or ""),
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
                "test_result_path": str(test_result_path),
                "requirement_path": str(requirement_path) if requirement_path else None,
                "policy_pack_path": str(policy_pack_path) if policy_pack_path else None,
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


def _bool_option(options: dict[str, Any], key: str, default: bool) -> bool:
    value = options.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _map_status(
    *,
    review_status: str,
    merge_recommendation: str,
    options: dict[str, Any],
) -> str:
    requires_approval = _bool_option(options, "requires_approval", True)
    if review_status in {"approved", "approve", "pass", "passed", "ok"}:
        return "pending_approval" if requires_approval else "succeeded"
    if review_status in {"rejected", "reject"}:
        return "rejected"
    if review_status == "test":
        if requires_approval:
            return "pending_approval"
        if _bool_option(options, "allow_local_review_success", False):
            return "succeeded"
        return "failed"
    if not review_status and merge_recommendation in {"approve", "approve_with_nits"} and not requires_approval:
        return "succeeded"
    return "failed"


def _build_output_artifacts(result_state: dict[str, Any]) -> list[ArtifactRef]:
    candidates = [
        ("review_result", "json", result_state.get("result_json_path"), "machine"),
        ("review_report", "markdown", result_state.get("code_review_report_path"), "display"),
        ("feedback_review", "markdown", result_state.get("feedback_review_path"), "handoff"),
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


def _build_error(
    *,
    api_status: str,
    review_status: str,
    merge_recommendation: str,
    result_state: dict[str, Any],
) -> StageError | None:
    if api_status not in {"failed", "rejected"}:
        return None
    issues = result_state.get("issues") or []
    errors = result_state.get("errors") or []
    summary = str(result_state.get("summary") or "ReviewGate did not approve this change.")
    return StageError(
        code="ReviewGateRejected" if api_status == "rejected" else "ReviewGateBlocked",
        message=summary,
        details={
            "review_status": review_status,
            "merge_recommendation": merge_recommendation,
            "issue_count": len(issues) if isinstance(issues, list) else 0,
            "errors": errors if isinstance(errors, list) else [],
        },
    )
