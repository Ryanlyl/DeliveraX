from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

from stage_contracts import (
    ArtifactRef,
    StageRunRequest,
    StageRunResult,
    resolve_stage_artifact_dir,
    write_stage_artifacts,
)

from .graph import run_codegen


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
    logs = ["CodeGen stage started"]
    try:
        options = request.options
        if not isinstance(options, dict):
            # Defensive: tolerate unexpected option payload shapes from upstream integrations.
            # Keep behavior permissive and let the stage run with empty/default options.
            if isinstance(options, str):
                try:
                    parsed = json.loads(options)
                    options = parsed if isinstance(parsed, dict) else {}
                except Exception:
                    options = {}
            else:
                options = {}

        repo_root = Path(__file__).resolve().parents[2]
        stage_dir = resolve_stage_artifact_dir(request)
        stage_dir.mkdir(parents=True, exist_ok=True)

        design_path = options.get("design_path") or _first_artifact_path(
            request, "technical_design", "human_output"
        )
        if not design_path:
            raise ValueError("CodeGen requires a technical design artifact or options.design_path.")

        legacy_output_dir = stage_dir / "legacy_output"
        result_state = run_codegen(
            design_path=str(design_path),
            repo_path=request.repo_path or options.get("repo_path"),
            workspace_dir=str(
                options.get("workspace_dir")
                or repo_root / "agents" / "solution_design" / ".workspace"
            ),
            task_id=request.run_id,
            output_dir=str(legacy_output_dir),
            local_only=bool(options.get("local_only", True)),
            max_context_files=int(options.get("max_context_files", 32)),
            max_file_chars=int(options.get("max_file_chars", 24000)),
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
            logs=[*logs, f"CodeGen report generated: {report_path}"],
        )
        return write_stage_artifacts(
            request=request,
            result=result,
            input_payload={"design_path": str(design_path), "options": options},
        )
    except Exception as exc:
        tb = traceback.format_exc()
        result = StageRunResult.from_exception(
            request=request,
            started_at=started_at,
            exc=exc,
            logs=[*logs, tb],
        )
        return write_stage_artifacts(request=request, result=result)
