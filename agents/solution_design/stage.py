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

from .graph import run_solution_design


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
    logs = ["SolDesign stage started"]
    try:
        repo_root = Path(__file__).resolve().parents[2]
        stage_dir = resolve_stage_artifact_dir(request)
        stage_dir.mkdir(parents=True, exist_ok=True)

        requirement_path = (
            request.options.get("requirement_path")
            or _first_artifact_path(request, "requirement_prd", "human_output")
        )
        if not requirement_path:
            raise ValueError("SolDesign requires a requirement markdown artifact or options.requirement_path.")

        repo_path = request.repo_path or request.options.get("repo_path")
        repo_url = request.options.get("repo_url")
        if not repo_path and not repo_url:
            default_frontend = repo_root / "frontend"
            repo_path = str(default_frontend) if default_frontend.exists() else None

        legacy_output_dir = stage_dir / "legacy_output"
        result_state = run_solution_design(
            requirement_path=str(requirement_path),
            repo_url=str(repo_url) if repo_url else None,
            repo_path=str(repo_path) if repo_path else None,
            repo_ref=request.options.get("repo_ref"),
            output_dir=str(legacy_output_dir),
            template_path=str(
                request.options.get("template_path")
                or repo_root / "agents" / "solution_design" / "templates" / "technical_design_template.md"
            ),
            workspace_dir=request.options.get("workspace_dir"),
            task_id=request.run_id,
            local_only=bool(request.options.get("local_only", True)),
            max_context_files=int(request.options.get("max_context_files", 24)),
        )
        output_path = Path(result_state["output_path"])
        human_output = output_path.read_text(encoding="utf-8")
        output_artifacts = [
            ArtifactRef(name="technical_design", type="markdown", path=str(output_path), role="handoff")
        ]

        ended_at = datetime.now(timezone.utc)
        status = "failed" if result_state.get("errors") else "succeeded"
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
            logs=[*logs, f"SolDesign generated: {output_path}"],
        )
        return write_stage_artifacts(
            request=request,
            result=result,
            input_payload={
                "requirement_path": str(requirement_path),
                "repo_path": str(repo_path) if repo_path else None,
                "repo_url": str(repo_url) if repo_url else None,
                "options": request.options,
            },
        )
    except Exception as exc:
        result = StageRunResult.from_exception(request=request, started_at=started_at, exc=exc, logs=logs)
        return write_stage_artifacts(request=request, result=result)

