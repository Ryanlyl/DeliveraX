from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from stage_contracts import (
    ArtifactRef,
    StageRunRequest,
    StageRunResult,
    resolve_stage_artifact_dir,
    write_stage_artifacts,
)

from .graph import run_integration


def _first_artifact_path(request: StageRunRequest, *names: str) -> str | None:
    wanted = set(names)
    for artifact in request.input_artifacts:
        if artifact.name in wanted:
            return artifact.path
    for artifact in request.input_artifacts:
        if artifact.type == "json":
            return artifact.path
    return None


def run_stage(request: StageRunRequest) -> StageRunResult:
    started_at = datetime.now(timezone.utc)
    logs = ["Integration stage started"]
    try:
        stage_dir = resolve_stage_artifact_dir(request)
        stage_dir.mkdir(parents=True, exist_ok=True)

        codegen_result_path = request.options.get("codegen_result_path") or _first_artifact_path(
            request, "codegen_result"
        )
        if not codegen_result_path:
            raise ValueError("Integration requires a codegen result artifact or options.codegen_result_path.")

        legacy_output_dir = stage_dir / "legacy_output"
        result_state = run_integration(
            codegen_result_path=str(codegen_result_path),
            changeset_path=request.options.get("changeset_path"),
            test_result_path=request.options.get("test_result_path"),
            review_result_path=request.options.get("review_result_path"),
            test_status=request.options.get("test_status", "passed"),
            review_status=request.options.get("review_status", "approved"),
            task_id=request.run_id,
            workspace_dir=str(request.options.get("workspace_dir") or stage_dir / "workspace"),
            output_dir=str(legacy_output_dir),
            integration_branch=request.options.get("integration_branch"),
            force=bool(request.options.get("force", True)),
            create_commit=bool(request.options.get("create_commit", True)),
            allow_source_head_drift=bool(request.options.get("allow_source_head_drift", False)),
            use_llm=bool(request.options.get("use_llm", False)),
            require_llm=bool(request.options.get("require_llm", False)),
            summary_max_diff_chars=int(request.options.get("summary_max_diff_chars", 24000)),
        )

        final_diff_path = Path(result_state["final_diff_path"])
        summary_path = Path(result_state["summary_path"])
        pr_body_path = Path(result_state["pr_body_path"])
        result_json_path = Path(result_state["result_json_path"])
        human_output = summary_path.read_text(encoding="utf-8")
        output_artifacts = [
            ArtifactRef(name="final_changes", type="diff", path=str(final_diff_path), role="handoff"),
            ArtifactRef(name="change_summary", type="markdown", path=str(summary_path), role="display"),
            ArtifactRef(name="github_pr_body", type="markdown", path=str(pr_body_path), role="handoff"),
            ArtifactRef(name="integration_result", type="json", path=str(result_json_path), role="machine"),
        ]

        ended_at = datetime.now(timezone.utc)
        status = "succeeded" if result_state.get("merge_ready") else "failed"
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
            logs=[*logs, f"Integration summary generated: {summary_path}"],
        )
        return write_stage_artifacts(
            request=request,
            result=result,
            input_payload={"codegen_result_path": str(codegen_result_path), "options": request.options},
        )
    except Exception as exc:
        result = StageRunResult.from_exception(request=request, started_at=started_at, exc=exc, logs=logs)
        return write_stage_artifacts(request=request, result=result)

