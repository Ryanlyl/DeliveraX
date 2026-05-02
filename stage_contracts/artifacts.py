from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ArtifactRef, StageRunRequest, StageRunResult


def default_artifacts_root(repo_root: str | Path | None = None) -> Path:
    base = Path(repo_root) if repo_root else Path.cwd()
    return base.resolve() / "artifacts"


def resolve_stage_artifact_dir(request: StageRunRequest) -> Path:
    return Path(request.output_dir).resolve() / request.pipeline_id / request.stage_id


def write_stage_artifacts(
    *,
    request: StageRunRequest,
    result: StageRunResult,
    input_payload: dict[str, Any] | None = None,
) -> StageRunResult:
    stage_dir = resolve_stage_artifact_dir(request)
    stage_dir.mkdir(parents=True, exist_ok=True)

    input_path = stage_dir / "input.json"
    result_path = stage_dir / "result.json"
    manifest_path = stage_dir / "manifest.json"
    logs_path = stage_dir / "logs.txt"
    human_output_path = stage_dir / "human_output.md"

    input_payload = input_payload or request.model_dump(mode="json")
    input_path.write_text(
        json.dumps(input_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logs_path.write_text("\n".join(result.logs).rstrip() + "\n", encoding="utf-8")

    output_artifacts = list(result.output_artifacts)
    if result.human_output is not None:
        human_output_path.write_text(result.human_output.rstrip() + "\n", encoding="utf-8")
        if not any(item.name == "human_output" for item in output_artifacts):
            output_artifacts.append(
                ArtifactRef(
                    name="human_output",
                    type="markdown",
                    path=str(human_output_path),
                    role="display",
                )
            )

    manifest = {
        "pipeline_id": result.pipeline_id,
        "stage_id": result.stage_id,
        "run_id": result.run_id,
        "status": result.status,
        "started_at": result.started_at.isoformat(),
        "ended_at": result.ended_at.isoformat(),
        "duration_ms": result.duration_ms,
        "input_artifacts": [item.model_dump(mode="json") for item in result.input_artifacts],
        "output_artifacts": [item.model_dump(mode="json") for item in output_artifacts],
        "error": result.error.model_dump(mode="json") if result.error else None,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result.output_artifacts = output_artifacts
    result.data = {
        **result.data,
        "standard_artifacts": {
            "input": str(input_path),
            "result": str(result_path),
            "manifest": str(manifest_path),
            "logs": str(logs_path),
            "human_output": str(human_output_path) if result.human_output is not None else None,
        },
    }
    result_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result
