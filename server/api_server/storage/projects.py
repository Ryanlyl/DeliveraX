from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from api_server.schemas import ProjectRecord


class ProjectNotFoundError(KeyError):
    pass


class JsonProjectStore:
    def __init__(self, artifacts_root: Path) -> None:
        self.root = artifacts_root.resolve()
        self.project_dir = self.root / "_projects"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def list(self) -> list[ProjectRecord]:
        records: list[ProjectRecord] = []
        for path in sorted(
            self.project_dir.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            records.append(self._read_path(path))
        return records

    def get(self, project_id: str) -> ProjectRecord:
        path = self._path_for(project_id)
        if not path.exists():
            raise ProjectNotFoundError(project_id)
        return self._read_path(path)

    def save(self, project: ProjectRecord) -> ProjectRecord:
        project.updated_at = datetime.now(timezone.utc)
        payload = json.dumps(project.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
        with self._lock:
            path = self._path_for(project.id)
            tmp_path = path.with_suffix(f"{path.suffix}.tmp")
            tmp_path.write_text(payload, encoding="utf-8")
            tmp_path.replace(path)
        return project

    def delete(self, project_id: str) -> None:
        path = self._path_for(project_id)
        if not path.exists():
            raise ProjectNotFoundError(project_id)
        with self._lock:
            path.unlink()

    def _path_for(self, project_id: str) -> Path:
        safe_id = project_id.replace("/", "_").replace("\\", "_")
        return self.project_dir / f"{safe_id}.json"

    def _read_path(self, path: Path) -> ProjectRecord:
        with self._lock:
            return ProjectRecord.model_validate_json(path.read_text(encoding="utf-8"))
