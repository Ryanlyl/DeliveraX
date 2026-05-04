from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from api_server.engine.models import PipelineRun


class PipelineRunNotFoundError(KeyError):
    pass


class JsonPipelineRunStore:
    def __init__(self, artifacts_root: Path) -> None:
        self.root = artifacts_root.resolve()
        self.runs_dir = self.root / "_runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def create(self, run: PipelineRun) -> PipelineRun:
        return self.save(run)

    def save(self, run: PipelineRun) -> PipelineRun:
        run.updated_at = datetime.now(timezone.utc)
        payload = json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
        with self._lock:
            path = self._path_for(run.pipeline_id, run.id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
        return run

    def get(self, pipeline_id: str, run_id: str) -> PipelineRun:
        path = self._path_for(pipeline_id, run_id)
        if not path.exists():
            raise PipelineRunNotFoundError(f"{pipeline_id}:{run_id}")
        return PipelineRun.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self, pipeline_id: str) -> list[PipelineRun]:
        base = self.runs_dir / self._safe(pipeline_id)
        if not base.exists():
            return []
        runs: list[PipelineRun] = []
        for path in sorted(base.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            runs.append(PipelineRun.model_validate_json(path.read_text(encoding="utf-8")))
        return runs

    def latest(self, pipeline_id: str) -> PipelineRun | None:
        runs = self.list(pipeline_id)
        return runs[0] if runs else None

    def _path_for(self, pipeline_id: str, run_id: str) -> Path:
        return self.runs_dir / self._safe(pipeline_id) / f"{self._safe(run_id)}.json"

    def _safe(self, value: str) -> str:
        return value.replace("/", "_").replace("\\", "_")
