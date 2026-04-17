from __future__ import annotations

import importlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .demo_data import STAGES
from .store import AppStore

SERVICE_DIR = Path(__file__).resolve().parent
STORE = AppStore(SERVICE_DIR / "data" / "deliverax.db")
TEXT_PREVIEW_SUFFIXES = {".txt", ".json", ".tex", ".md", ".log"}
TEXT_PREVIEW_LIMIT = 60_000


class MeetingAgentRequest(BaseModel):
    source_file_id: str
    mode: Literal["local", "api"] = "local"


class InfoCplRequest(BaseModel):
    draft_file_id: str
    mode: Literal["local", "api"] = "local"


app = FastAPI(
    title="DeliveraX API",
    version="0.2.0",
    description="FastAPI service layer for the DeliveraX frontend and backend agents.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_project_and_stage(project_id: str, stage_id: str) -> None:
    if not STORE.get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    if not STORE.is_valid_stage(stage_id):
        raise HTTPException(status_code=404, detail="Stage not found.")


def serialize_file(file_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": file_record["id"],
        "project_id": file_record["project_id"],
        "stage_id": file_record["stage_id"],
        "kind": file_record["kind"],
        "name": file_record["name"],
        "original_name": file_record["original_name"],
        "status": file_record["status"],
        "size_bytes": file_record["size_bytes"],
        "created_at": file_record["created_at"],
        "updated_at": file_record["updated_at"],
        "source_file_id": file_record.get("source_file_id"),
        "generated_by_job_id": file_record.get("generated_by_job_id"),
        "download_url": f"/api/files/{file_record['id']}/download",
        "content_url": f"/api/files/{file_record['id']}/content",
    }


def serialize_job(job_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job_record["id"],
        "project_id": job_record["project_id"],
        "stage_id": job_record["stage_id"],
        "type": job_record["type"],
        "status": job_record["status"],
        "payload": job_record["payload"],
        "message": job_record["message"],
        "error": job_record["error"],
        "output_file_ids": job_record["output_file_ids"],
        "created_at": job_record["created_at"],
        "updated_at": job_record["updated_at"],
        "started_at": job_record["started_at"],
        "finished_at": job_record["finished_at"],
    }


def serialize_project(project_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": project_record["id"],
        "name": project_record["name"],
        "industry": project_record["industry"],
        "status": project_record["status"],
        "progress": project_record["progress"],
        "summary": project_record["summary"],
        "owner": project_record["owner"],
        "tags": project_record["tags"],
        "current_stage_id": project_record["current_stage_id"],
        "current_stage": project_record.get("current_stage"),
    }


def run_meeting_agent_job(job_id: str, source_file_id: str, mode: str) -> None:
    STORE.update_job(job_id, status="running", message="Meeting Agent 正在执行。", started_at=utc_now())

    try:
        source_file = STORE.get_file(source_file_id)
        if not source_file:
            raise FileNotFoundError("Source meeting note was not found.")

        input_path = Path(source_file["path"])
        if mode == "api":
            module = importlib.import_module("meeting_agent.agent_api")
            output_path = module.process_single_file(input_path)
        else:
            module = importlib.import_module("meeting_agent.agent_local")
            output_path = module.process_single_meeting(input_path)

        if not output_path:
            raise RuntimeError("Meeting agent did not return an output path.")

        output_path = Path(output_path)
        if not output_path.exists():
            raise FileNotFoundError(f"Generated draft was not found: {output_path}")

        generated = STORE.upsert_file(
            project_id=source_file["project_id"],
            stage_id=source_file["stage_id"],
            kind="draft_json",
            path=output_path,
            name=output_path.name,
            original_name=output_path.name,
            status="ready",
            source_file_id=source_file_id,
            generated_by_job_id=job_id,
        )
        STORE.complete_job(job_id, output_file_ids=[generated["id"]], message="Meeting Agent 执行完成。")
    except Exception as exc:
        STORE.fail_job(job_id, str(exc))


def run_info_cpl_job(job_id: str, draft_file_id: str, mode: str) -> None:
    STORE.update_job(job_id, status="running", message="Info CPL Agent 正在执行。", started_at=utc_now())

    try:
        draft_file = STORE.get_file(draft_file_id)
        if not draft_file:
            raise FileNotFoundError("Draft JSON file was not found.")

        draft_path = Path(draft_file["path"])
        module = importlib.import_module("Info_cpl_agent.agent_info_cpl")
        output_path = module.process_single_json_file(draft_path, mode=mode)

        if not output_path:
            raise RuntimeError("Info CPL agent did not return an output path.")

        output_path = Path(output_path)
        if not output_path.exists():
            raise FileNotFoundError(f"Generated LaTeX file was not found: {output_path}")

        generated = STORE.upsert_file(
            project_id=draft_file["project_id"],
            stage_id=draft_file["stage_id"],
            kind="latex_doc",
            path=output_path,
            name=output_path.name,
            original_name=output_path.name,
            status="ready",
            source_file_id=draft_file_id,
            generated_by_job_id=job_id,
        )
        STORE.complete_job(job_id, output_file_ids=[generated["id"]], message="Info CPL Agent 执行完成。")
    except Exception as exc:
        STORE.fail_job(job_id, str(exc))


def read_file_content(path: Path) -> tuple[str, bool]:
    suffix = path.suffix.lower()
    if suffix not in TEXT_PREVIEW_SUFFIXES:
        raise HTTPException(status_code=400, detail="This file type does not support inline preview.")

    with path.open("r", encoding="utf-8", errors="replace") as file_obj:
        content = file_obj.read(TEXT_PREVIEW_LIMIT + 1)

    truncated = len(content) > TEXT_PREVIEW_LIMIT
    if truncated:
        content = content[:TEXT_PREVIEW_LIMIT]

    return content, truncated


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "timestamp": utc_now()}


@app.get("/api/projects")
def list_projects() -> dict[str, Any]:
    projects = [serialize_project(project) for project in STORE.list_projects()]
    return {"items": projects, "stages": STAGES}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return {"item": serialize_project(project), "stages": STAGES}


@app.get("/api/projects/{project_id}/stages/{stage_id}")
def get_stage_detail(project_id: str, stage_id: str) -> dict[str, Any]:
    detail = STORE.get_stage_detail(project_id, stage_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Project or stage not found.")

    return {
        "project": serialize_project(detail["project"]),
        "stage": detail["stage"],
        "stages": detail["stages"],
        "files": {
            "meeting_notes": [serialize_file(item) for item in detail["files"]["meeting_notes"]],
            "draft_jsons": [serialize_file(item) for item in detail["files"]["draft_jsons"]],
            "latex_docs": [serialize_file(item) for item in detail["files"]["latex_docs"]],
        },
        "jobs": [serialize_job(item) for item in detail["jobs"]],
        "can_run": detail["can_run"],
    }


@app.post("/api/projects/{project_id}/meeting-notes")
async def upload_meeting_note(
    project_id: str,
    stage_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    ensure_project_and_stage(project_id, stage_id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name.")

    suffix = Path(file.filename).suffix.lower()
    if suffix != ".txt":
        raise HTTPException(status_code=400, detail="Only .txt meeting notes are supported for now.")

    upload_dir = STORE.project_upload_dir(project_id, stage_id)
    stored_name = STORE.build_storage_name(file.filename)
    target_path = upload_dir / stored_name

    with target_path.open("wb") as target_file:
        shutil.copyfileobj(file.file, target_file)

    file_record = STORE.upsert_file(
        project_id=project_id,
        stage_id=stage_id,
        kind="meeting_note",
        path=target_path,
        name=stored_name,
        original_name=file.filename,
        status="ready",
    )

    return {"item": serialize_file(file_record)}


@app.post("/api/projects/{project_id}/jobs/meeting-agent")
def create_meeting_agent_job(
    project_id: str,
    request: MeetingAgentRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    source_file = STORE.get_file(request.source_file_id)
    if not source_file or source_file["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Source meeting note not found.")

    if source_file["kind"] != "meeting_note":
        raise HTTPException(status_code=400, detail="Meeting Agent requires a meeting note file.")

    job = STORE.create_job(
        project_id=project_id,
        stage_id=source_file["stage_id"],
        job_type="meeting_agent",
        payload={"source_file_id": request.source_file_id, "mode": request.mode},
    )
    background_tasks.add_task(run_meeting_agent_job, job["id"], request.source_file_id, request.mode)
    return {"item": serialize_job(job)}


@app.post("/api/projects/{project_id}/jobs/info-cpl-agent")
def create_info_cpl_job(
    project_id: str,
    request: InfoCplRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    draft_file = STORE.get_file(request.draft_file_id)
    if not draft_file or draft_file["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Draft JSON file not found.")

    if draft_file["kind"] != "draft_json":
        raise HTTPException(status_code=400, detail="Info CPL Agent requires a draft JSON file.")

    job = STORE.create_job(
        project_id=project_id,
        stage_id=draft_file["stage_id"],
        job_type="info_cpl_agent",
        payload={"draft_file_id": request.draft_file_id, "mode": request.mode},
    )
    background_tasks.add_task(run_info_cpl_job, job["id"], request.draft_file_id, request.mode)
    return {"item": serialize_job(job)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = STORE.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {"item": serialize_job(job)}


@app.get("/api/files/{file_id}/content")
def get_file_content(file_id: str) -> dict[str, Any]:
    file_record = STORE.get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found.")

    path = Path(file_record["path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file no longer exists on disk.")

    content, truncated = read_file_content(path)
    return {
        "item": {
            "file_id": file_id,
            "content": content,
            "truncated": truncated,
            "encoding": "utf-8",
        }
    }


@app.get("/api/files/{file_id}/download")
def download_file(file_id: str) -> FileResponse:
    file_record = STORE.get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found.")

    path = Path(file_record["path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file no longer exists on disk.")

    return FileResponse(path=path, filename=file_record["original_name"], media_type="application/octet-stream")
