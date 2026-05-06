from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api_server.routers.stages import stage_error_to_http
from api_server.engine.models import PipelineRun
from api_server.schemas import ApprovalRequest, PipelineCreateRequest, PipelineRecord, PipelineRunInput, StageRunInput
from api_server.storage.json_store import PipelineNotFoundError
from api_server.storage.projects import ProjectNotFoundError

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.post(
    "",
    response_model=PipelineRecord,
    summary="创建新的 Pipeline",
    description="根据需求文本创建一个新的 AI DevFlow Pipeline。自动配置需求分析、方案设计、代码生成、测试、评审等阶段。",
    response_description="新创建的 Pipeline 记录，包含完整 stage 列表和初始状态。",
    responses={
        400: {"description": "请求参数无效"},
        500: {"description": "STAGE_EXECUTION_FAILED — 阶段执行失败"},
    },
)
def create_pipeline(payload: PipelineCreateRequest, request: Request) -> PipelineRecord:
    project = None
    if payload.project_id:
        try:
            project = request.app.state.project_store.get(payload.project_id)
        except ProjectNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Project not found: {payload.project_id}") from exc

    pipeline = request.app.state.pipeline_service.create(payload)

    if project is not None and pipeline.id not in project.pipeline_ids:
        project.pipeline_ids.append(pipeline.id)
        request.app.state.project_store.save(project)

    return pipeline


@router.get(
    "",
    response_model=list[PipelineRecord],
    summary="列出所有 Pipeline",
    description="返回所有已创建的 Pipeline 列表，按创建时间排序。",
    response_description="Pipeline 记录数组。",
)
def list_pipelines(request: Request, project_id: str | None = None) -> list[PipelineRecord]:
    pipelines = request.app.state.pipeline_service.list()
    if not project_id:
        return pipelines

    try:
        project = request.app.state.project_store.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from exc

    linked_pipeline_ids = set(project.pipeline_ids)
    return [
        pipeline
        for pipeline in pipelines
        if pipeline.project_id == project_id or pipeline.id in linked_pipeline_ids
    ]


@router.get(
    "/{pipeline_id}",
    response_model=PipelineRecord,
    summary="获取 Pipeline 详情",
    description="根据 pipeline_id 获取单个 Pipeline 的完整信息，包括所有 stage 状态和产物引用。",
    response_description="完整的 Pipeline 记录。",
    responses={
        404: {"description": "PIPELINE_NOT_FOUND — 指定 pipeline 不存在"},
    },
)
def get_pipeline(pipeline_id: str, request: Request) -> PipelineRecord:
    try:
        return request.app.state.pipeline_service.get(pipeline_id)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc


@router.get(
    "/{pipeline_id}/stages/{stage_id}",
    response_model=dict,
    summary="获取指定 Stage 详情",
    description="返回 Pipeline 中某个 stage 的完整信息。",
    response_description="Stage 数据的字典。",
    responses={
        404: {"description": "PIPELINE_NOT_FOUND 或 STAGE_NOT_FOUND"},
    },
)
def get_stage(pipeline_id: str, stage_id: str, request: Request) -> dict:
    try:
        pipeline = request.app.state.pipeline_service.get(pipeline_id)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc
    for stage in pipeline.stages:
        if stage.id == stage_id:
            return stage.model_dump(mode="json")
    raise HTTPException(status_code=404, detail=f"Stage not found: {stage_id}")


@router.post(
    "/{pipeline_id}/run",
    response_model=PipelineRecord,
    summary="运行 Pipeline（兼容接口）",
    description="启动 pipeline 运行并立即返回 pipeline 视图。此接口保留向后兼容，新调用建议使用 /start。",
    response_description="Pipeline 运行开始后的 pipeline 记录。",
    responses={
        404: {"description": "PIPELINE_NOT_FOUND"},
        500: {"description": "STAGE_EXECUTION_FAILED"},
    },
)
async def run_pipeline(pipeline_id: str, payload: PipelineRunInput, request: Request) -> PipelineRecord:
    try:
        run: PipelineRun = request.app.state.pipeline_runner.start_run(pipeline_id, payload)
        # Keep backward-compatible response shape: return pipeline view immediately.
        return request.app.state.pipeline_service.get(pipeline_id)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post(
    "/{pipeline_id}/start",
    response_model=PipelineRun,
    summary="启动 Pipeline 运行",
    description="启动 pipeline 执行。返回 PipelineRun 对象，包含 stage_order、当前阶段等运行信息。",
    response_description="新创建的 PipelineRun。",
    responses={
        404: {"description": "PIPELINE_NOT_FOUND"},
    },
)
def start_pipeline(pipeline_id: str, payload: PipelineRunInput, request: Request) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.start_run(pipeline_id, payload)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc


@router.post(
    "/{pipeline_id}/pause",
    response_model=PipelineRun,
    summary="暂停 Pipeline",
    description="暂停正在运行的 pipeline。pipeline 将在当前 stage 完成后暂停。",
    response_description="更新后的 PipelineRun，pause_requested=True。",
    responses={
        409: {"description": "INVALID_TRANSITION — Pipeline 当前状态不允许暂停"},
        404: {"description": "RUN_NOT_FOUND"},
    },
)
def pause_pipeline(pipeline_id: str, request: Request, run_id: str | None = None) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.pause_run(pipeline_id, run_id)
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post(
    "/{pipeline_id}/resume",
    response_model=PipelineRun,
    summary="恢复 Pipeline",
    description="恢复被暂停的 pipeline 执行。",
    response_description="更新后的 PipelineRun。",
    responses={
        409: {"description": "INVALID_TRANSITION — Pipeline 当前状态不允许恢复"},
        404: {"description": "RUN_NOT_FOUND"},
    },
)
def resume_pipeline(pipeline_id: str, request: Request, run_id: str | None = None) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.resume_run(pipeline_id, run_id)
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post(
    "/{pipeline_id}/terminate",
    response_model=PipelineRun,
    summary="终止 Pipeline",
    description="终止 pipeline 执行。已完成的 stage 结果会被保留。",
    response_description="更新后的 PipelineRun，terminate_requested=True 或 status=terminated。",
    responses={
        409: {"description": "INVALID_TRANSITION — Pipeline 当前状态不允许终止"},
        404: {"description": "RUN_NOT_FOUND"},
    },
)
def terminate_pipeline(pipeline_id: str, request: Request, run_id: str | None = None) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.terminate_run(pipeline_id, run_id)
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.get(
    "/{pipeline_id}/runs/{run_id}",
    response_model=PipelineRun,
    summary="获取 PipelineRun 详情",
    description="返回指定 run 的详细信息，包括各阶段状态、已完成/失败的 stage 等。",
    response_description="完整的 PipelineRun 对象。",
    responses={
        404: {"description": "RUN_NOT_FOUND"},
    },
)
def get_run(pipeline_id: str, run_id: str, request: Request) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.get_run(pipeline_id, run_id)
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post(
    "/{pipeline_id}/stages/{stage_id}/run",
    response_model=PipelineRecord,
    summary="运行单个 Stage",
    description="手动触发 pipeline 中某个 stage 的执行。",
    response_description="更新后的 Pipeline 记录。",
    responses={
        404: {"description": "PIPELINE_NOT_FOUND 或 STAGE_NOT_FOUND"},
        500: {"description": "STAGE_EXECUTION_FAILED"},
    },
)
async def run_stage(pipeline_id: str, stage_id: str, payload: StageRunInput, request: Request) -> PipelineRecord:
    try:
        return await request.app.state.pipeline_service.run_stage(pipeline_id, stage_id, payload)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post(
    "/{pipeline_id}/stages/{stage_id}/approve",
    response_model=PipelineRecord,
    summary="批准 Stage",
    description="人工批准当前 stage 的产物，可选择是否自动继续 pipeline 执行。",
    response_description="更新后的 Pipeline 记录。",
    responses={
        404: {"description": "PIPELINE_NOT_FOUND 或 STAGE_NOT_FOUND"},
        409: {"description": "INVALID_TRANSITION"},
    },
)
async def approve_stage(pipeline_id: str, stage_id: str, payload: ApprovalRequest, request: Request) -> PipelineRecord:
    try:
        pipeline = request.app.state.approval_service.approve(pipeline_id, stage_id, payload)
        if not payload.continue_pipeline:
            return pipeline
        latest_run_id = getattr(pipeline, "latest_run_id", None)
        request.app.state.pipeline_runner.resume_run(pipeline_id, latest_run_id)
        return request.app.state.pipeline_service.get(pipeline_id)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Stage not found: {stage_id}") from exc
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post(
    "/{pipeline_id}/stages/{stage_id}/reject",
    response_model=PipelineRecord,
    summary="驳回 Stage",
    description="人工驳回当前 stage 的产物，需要提供驳回理由。",
    response_description="更新后的 Pipeline 记录。",
    responses={
        404: {"description": "PIPELINE_NOT_FOUND 或 STAGE_NOT_FOUND"},
        409: {"description": "INVALID_TRANSITION"},
    },
)
def reject_stage(pipeline_id: str, stage_id: str, payload: ApprovalRequest, request: Request) -> PipelineRecord:
    try:
        return request.app.state.approval_service.reject(pipeline_id, stage_id, payload)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Stage not found: {stage_id}") from exc
    except Exception as exc:
        raise stage_error_to_http(exc) from exc
