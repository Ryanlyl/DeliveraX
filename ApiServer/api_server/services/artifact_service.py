from __future__ import annotations

import json
from pathlib import Path

from api_server.schemas import ArtifactListResponse, ArtifactTextResponse
from stage_contracts import ArtifactRef


class ArtifactNotFoundError(FileNotFoundError):
    pass


class UnsafeArtifactPathError(ValueError):
    pass


class ArtifactService:
    def __init__(self, artifacts_root: Path) -> None:
        self.artifacts_root = artifacts_root.resolve()

    def list_stage_artifacts(self, pipeline_id: str, stage_id: str) -> ArtifactListResponse:
        stage_dir = self.artifacts_root / pipeline_id / stage_id
        manifest_path = stage_dir / "manifest.json"
        standard_artifacts = {
            "input": str(stage_dir / "input.json"),
            "result": str(stage_dir / "result.json"),
            "manifest": str(manifest_path),
            "logs": str(stage_dir / "logs.txt"),
            "human_output": str(stage_dir / "human_output.md"),
        }
        if not manifest_path.exists():
            return ArtifactListResponse(
                pipeline_id=pipeline_id,
                stage_id=stage_id,
                artifacts=[],
                standard_artifacts={key: value if Path(value).exists() else None for key, value in standard_artifacts.items()},
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return ArtifactListResponse(
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            artifacts=[ArtifactRef.model_validate(item) for item in manifest.get("output_artifacts", [])],
            standard_artifacts={key: value if Path(value).exists() else None for key, value in standard_artifacts.items()},
        )

    def read_text(self, path: str) -> ArtifactTextResponse:
        artifact_path = self._safe_path(path)
        if not artifact_path.exists() or not artifact_path.is_file():
            raise ArtifactNotFoundError(path)
        return ArtifactTextResponse(path=str(artifact_path), content=artifact_path.read_text(encoding="utf-8"))

    def _safe_path(self, path: str) -> Path:
        artifact_path = Path(path).resolve()
        try:
            artifact_path.relative_to(self.artifacts_root)
        except ValueError as exc:
            raise UnsafeArtifactPathError(f"Artifact path must be under {self.artifacts_root}") from exc
        return artifact_path
