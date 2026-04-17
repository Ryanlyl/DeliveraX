from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from .demo_data import PROJECTS, STAGE_INDEX, STAGES

FileKind = Literal["meeting_note", "draft_json", "latex_doc"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AppStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.data_dir = db_path.parent
        self.storage_dir = self.data_dir / "projects"
        self._lock = threading.Lock()
        self._ensure_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_database(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    current_stage_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    name TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source_file_id TEXT,
                    generated_by_job_id TEXT
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    message TEXT NOT NULL,
                    error TEXT,
                    output_file_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_files_project_stage
                ON files(project_id, stage_id, kind, updated_at DESC);

                CREATE INDEX IF NOT EXISTS idx_jobs_project_stage
                ON jobs(project_id, stage_id, updated_at DESC);
                """
            )

            if self._count_rows(connection, "projects") == 0:
                if not self._migrate_legacy_state_json(connection):
                    self._seed_demo_projects(connection)

    def _count_rows(self, connection: sqlite3.Connection, table_name: str) -> int:
        cursor = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
        row = cursor.fetchone()
        return int(row["count"]) if row else 0

    def _migrate_legacy_state_json(self, connection: sqlite3.Connection) -> bool:
        state_file = self.data_dir / "state.json"
        if not state_file.exists():
            return False

        with state_file.open("r", encoding="utf-8") as file_obj:
            state = json.load(file_obj)

        now = utc_now()
        for project in state.get("projects", []):
            connection.execute(
                """
                INSERT INTO projects (
                    id, name, industry, status, progress, current_stage_id, summary, owner,
                    tags_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project["id"],
                    project["name"],
                    project["industry"],
                    project["status"],
                    int(project["progress"]),
                    project["current_stage_id"],
                    project["summary"],
                    project["owner"],
                    json.dumps(project.get("tags", []), ensure_ascii=False),
                    project.get("created_at", now),
                    project.get("updated_at", now),
                ),
            )

        for file_record in state.get("files", []):
            connection.execute(
                """
                INSERT INTO files (
                    id, project_id, stage_id, kind, name, original_name, path, status,
                    size_bytes, created_at, updated_at, source_file_id, generated_by_job_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_record["id"],
                    file_record["project_id"],
                    file_record["stage_id"],
                    file_record["kind"],
                    file_record["name"],
                    file_record["original_name"],
                    file_record["path"],
                    file_record["status"],
                    int(file_record.get("size_bytes", 0)),
                    file_record.get("created_at", now),
                    file_record.get("updated_at", now),
                    file_record.get("source_file_id"),
                    file_record.get("generated_by_job_id"),
                ),
            )

        for job_record in state.get("jobs", []):
            connection.execute(
                """
                INSERT INTO jobs (
                    id, project_id, stage_id, type, status, payload_json, message, error,
                    output_file_ids_json, created_at, updated_at, started_at, finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_record["id"],
                    job_record["project_id"],
                    job_record["stage_id"],
                    job_record["type"],
                    job_record["status"],
                    json.dumps(job_record.get("payload", {}), ensure_ascii=False),
                    job_record.get("message", ""),
                    job_record.get("error"),
                    json.dumps(job_record.get("output_file_ids", []), ensure_ascii=False),
                    job_record.get("created_at", now),
                    job_record.get("updated_at", now),
                    job_record.get("started_at"),
                    job_record.get("finished_at"),
                ),
            )

        return True

    def _seed_demo_projects(self, connection: sqlite3.Connection) -> None:
        now = utc_now()
        for project in PROJECTS:
            connection.execute(
                """
                INSERT INTO projects (
                    id, name, industry, status, progress, current_stage_id, summary, owner,
                    tags_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project["id"],
                    project["name"],
                    project["industry"],
                    project["status"],
                    int(project["progress"]),
                    project["current_stage_id"],
                    project["summary"],
                    project["owner"],
                    json.dumps(project.get("tags", []), ensure_ascii=False),
                    now,
                    now,
                ),
            )

    def _row_to_project(self, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["tags"] = json.loads(item.pop("tags_json"))
        item["current_stage"] = STAGE_INDEX.get(item["current_stage_id"])
        return item

    def _row_to_file(self, row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def _row_to_job(self, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        item["output_file_ids"] = json.loads(item.pop("output_file_ids_json"))
        return item

    def project_upload_dir(self, project_id: str, stage_id: str) -> Path:
        directory = self.storage_dir / project_id / stage_id / "meeting_notes"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def build_storage_name(self, original_name: str) -> str:
        suffix = Path(original_name).suffix.lower() or ".txt"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{timestamp}-{uuid4().hex[:8]}{suffix}"

    def list_projects(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT *
                FROM projects
                ORDER BY updated_at DESC, created_at DESC
                """
            )
            return [self._row_to_project(row) for row in cursor.fetchall()]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT *
                FROM projects
                WHERE id = ?
                """,
                (project_id,),
            )
            row = cursor.fetchone()
            return self._row_to_project(row) if row else None

    def is_valid_stage(self, stage_id: str) -> bool:
        return stage_id in STAGE_INDEX

    def upsert_file(
        self,
        *,
        project_id: str,
        stage_id: str,
        kind: FileKind,
        path: Path,
        name: str,
        original_name: str,
        status: str,
        source_file_id: str | None = None,
        generated_by_job_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_path = str(path.resolve())
        size_bytes = path.stat().st_size if path.exists() else 0
        now = utc_now()

        with self._lock, self._connect() as connection:
            existing_cursor = connection.execute(
                """
                SELECT id
                FROM files
                WHERE path = ?
                """,
                (resolved_path,),
            )
            existing = existing_cursor.fetchone()

            if existing:
                connection.execute(
                    """
                    UPDATE files
                    SET project_id = ?, stage_id = ?, kind = ?, name = ?, original_name = ?,
                        status = ?, size_bytes = ?, updated_at = ?, source_file_id = ?,
                        generated_by_job_id = ?
                    WHERE id = ?
                    """,
                    (
                        project_id,
                        stage_id,
                        kind,
                        name,
                        original_name,
                        status,
                        size_bytes,
                        now,
                        source_file_id,
                        generated_by_job_id,
                        existing["id"],
                    ),
                )
                file_id = existing["id"]
            else:
                file_id = uuid4().hex
                connection.execute(
                    """
                    INSERT INTO files (
                        id, project_id, stage_id, kind, name, original_name, path, status,
                        size_bytes, created_at, updated_at, source_file_id, generated_by_job_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        project_id,
                        stage_id,
                        kind,
                        name,
                        original_name,
                        resolved_path,
                        status,
                        size_bytes,
                        now,
                        now,
                        source_file_id,
                        generated_by_job_id,
                    ),
                )

            cursor = connection.execute(
                """
                SELECT *
                FROM files
                WHERE id = ?
                """,
                (file_id,),
            )
            row = cursor.fetchone()
            return self._row_to_file(row)

    def list_project_files(
        self,
        project_id: str,
        *,
        stage_id: str | None = None,
        kind: FileKind | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["project_id = ?"]
        params: list[Any] = [project_id]

        if stage_id:
            clauses.append("stage_id = ?")
            params.append(stage_id)

        if kind:
            clauses.append("kind = ?")
            params.append(kind)

        where_clause = " AND ".join(clauses)

        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f"""
                SELECT *
                FROM files
                WHERE {where_clause}
                ORDER BY updated_at DESC, created_at DESC
                """,
                params,
            )
            return [self._row_to_file(row) for row in cursor.fetchall()]

    def get_file(self, file_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT *
                FROM files
                WHERE id = ?
                """,
                (file_id,),
            )
            row = cursor.fetchone()
            return self._row_to_file(row) if row else None

    def create_job(
        self,
        *,
        project_id: str,
        stage_id: str,
        job_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        now = utc_now()
        job_id = uuid4().hex

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, project_id, stage_id, type, status, payload_json, message, error,
                    output_file_ids_json, created_at, updated_at, started_at, finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    project_id,
                    stage_id,
                    job_type,
                    "queued",
                    json.dumps(payload, ensure_ascii=False),
                    "任务已创建，等待执行。",
                    None,
                    json.dumps([], ensure_ascii=False),
                    now,
                    now,
                    None,
                    None,
                ),
            )
            cursor = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            )
            return self._row_to_job(cursor.fetchone())

    def update_job(self, job_id: str, **updates: Any) -> dict[str, Any]:
        if not updates:
            job = self.get_job(job_id)
            if not job:
                raise KeyError(f"Job not found: {job_id}")
            return job

        assignments: list[str] = []
        params: list[Any] = []

        for key, value in updates.items():
            column = key
            if key == "payload":
                column = "payload_json"
                value = json.dumps(value, ensure_ascii=False)
            elif key == "output_file_ids":
                column = "output_file_ids_json"
                value = json.dumps(value, ensure_ascii=False)

            assignments.append(f"{column} = ?")
            params.append(value)

        assignments.append("updated_at = ?")
        params.append(utc_now())
        params.append(job_id)

        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT 1
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            )
            if not cursor.fetchone():
                raise KeyError(f"Job not found: {job_id}")

            connection.execute(
                f"""
                UPDATE jobs
                SET {", ".join(assignments)}
                WHERE id = ?
                """,
                params,
            )
            cursor = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            )
            return self._row_to_job(cursor.fetchone())

    def complete_job(self, job_id: str, *, output_file_ids: list[str], message: str) -> dict[str, Any]:
        return self.update_job(
            job_id,
            status="completed",
            output_file_ids=output_file_ids,
            message=message,
            error=None,
            finished_at=utc_now(),
        )

    def fail_job(self, job_id: str, error: str) -> dict[str, Any]:
        return self.update_job(
            job_id,
            status="failed",
            message="任务执行失败。",
            error=error,
            finished_at=utc_now(),
        )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            )
            row = cursor.fetchone()
            return self._row_to_job(row) if row else None

    def list_project_jobs(self, project_id: str, *, stage_id: str | None = None) -> list[dict[str, Any]]:
        clauses = ["project_id = ?"]
        params: list[Any] = [project_id]

        if stage_id:
            clauses.append("stage_id = ?")
            params.append(stage_id)

        where_clause = " AND ".join(clauses)

        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f"""
                SELECT *
                FROM jobs
                WHERE {where_clause}
                ORDER BY updated_at DESC, created_at DESC
                """,
                params,
            )
            return [self._row_to_job(row) for row in cursor.fetchall()]

    def get_stage_detail(self, project_id: str, stage_id: str) -> dict[str, Any] | None:
        project = self.get_project(project_id)
        stage = STAGE_INDEX.get(stage_id)
        if not project or not stage:
            return None

        files = self.list_project_files(project_id, stage_id=stage_id)
        jobs = self.list_project_jobs(project_id, stage_id=stage_id)

        meeting_notes = [item for item in files if item["kind"] == "meeting_note"]
        draft_jsons = [item for item in files if item["kind"] == "draft_json"]
        latex_docs = [item for item in files if item["kind"] == "latex_doc"]

        return {
            "project": project,
            "stage": stage,
            "files": {
                "meeting_notes": meeting_notes,
                "draft_jsons": draft_jsons,
                "latex_docs": latex_docs,
            },
            "jobs": jobs[:10],
            "can_run": {
                "meeting_agent": bool(meeting_notes),
                "info_cpl_agent": bool(draft_jsons),
            },
            "stages": STAGES,
        }
