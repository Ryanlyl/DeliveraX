from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from api_server.schemas import PipelineRecord


class PipelineNotFoundError(KeyError):
    pass


class JsonPipelineStore:
    def __init__(self, artifacts_root: Path) -> None:
        self.root = artifacts_root.resolve()
        self.pipeline_dir = self.root / "_pipelines"
        self.pipeline_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def list(self) -> list[PipelineRecord]:
        records: list[PipelineRecord] = []
        for path in sorted(self.pipeline_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            records.append(self._read_path(path))
        return records

    def get(self, pipeline_id: str) -> PipelineRecord:
        path = self._path_for(pipeline_id)
        if not path.exists():
            raise PipelineNotFoundError(pipeline_id)
        return self._read_path(path)

    def save(self, pipeline: PipelineRecord) -> PipelineRecord:
        pipeline.updated_at = datetime.now(timezone.utc)
        payload = json.dumps(pipeline.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
        with self._lock:
            self.pipeline_dir.mkdir(parents=True, exist_ok=True)
            self._path_for(pipeline.id).write_text(payload, encoding="utf-8")
        return pipeline

    def _path_for(self, pipeline_id: str) -> Path:
        safe_id = pipeline_id.replace("/", "_").replace("\\", "_")
        return self.pipeline_dir / f"{safe_id}.json"

    def _read_path(self, path: Path) -> PipelineRecord:
        return PipelineRecord.model_validate_json(path.read_text(encoding="utf-8"))
