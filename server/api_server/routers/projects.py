from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from api_server.schemas import ProjectCreateRequest, ProjectRecord
from api_server.services.project_clone_service import clone_project_repo
from api_server.storage.projects import ProjectNotFoundError

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectRecord,
    summary="创建项目",
    description="创建一个新项目并关联 GitHub 仓库地址。",
)
def create_project(
    payload: ProjectCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> ProjectRecord:
    project = ProjectRecord(
        name=payload.name,
        description=payload.description,
        github_url=payload.github_url,
    )
    saved_project = request.app.state.project_store.save(project)
    background_tasks.add_task(
        clone_project_repo,
        saved_project.id,
        request.app.state.project_store,
        request.app.state.settings.resolved_artifacts_root,
    )
    return saved_project


@router.get(
    "",
    response_model=list[ProjectRecord],
    summary="列出所有项目",
    description="返回所有已创建的项目列表，按更新时间倒序排列。",
)
def list_projects(request: Request) -> list[ProjectRecord]:
    return request.app.state.project_store.list()


@router.get(
    "/{project_id}",
    response_model=ProjectRecord,
    summary="获取项目详情",
    description="根据 project_id 获取单个项目的完整信息。",
    responses={404: {"description": "PROJECT_NOT_FOUND"}},
)
def get_project(project_id: str, request: Request) -> ProjectRecord:
    try:
        return request.app.state.project_store.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from exc


@router.delete(
    "/{project_id}",
    response_model=dict,
    summary="删除项目",
    description="删除指定项目。",
    responses={404: {"description": "PROJECT_NOT_FOUND"}},
)
def delete_project(project_id: str, request: Request) -> dict:
    try:
        request.app.state.project_store.delete(project_id)
        return {"ok": True}
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from exc
