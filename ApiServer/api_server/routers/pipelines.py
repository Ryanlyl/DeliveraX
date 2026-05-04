from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api_server.routers.stages import stage_error_to_http
from api_server.engine.models import PipelineRun
from api_server.schemas import ApprovalRequest, PipelineCreateRequest, PipelineRecord, PipelineRunInput, StageRunInput
from api_server.storage.json_store import PipelineNotFoundError

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.post("", response_model=PipelineRecord)
def create_pipeline(payload: PipelineCreateRequest, request: Request) -> PipelineRecord:
    return request.app.state.pipeline_service.create(payload)


@router.get("", response_model=list[PipelineRecord])
def list_pipelines(request: Request) -> list[PipelineRecord]:
    return request.app.state.pipeline_service.list()


@router.get("/{pipeline_id}", response_model=PipelineRecord)
def get_pipeline(pipeline_id: str, request: Request) -> PipelineRecord:
    try:
        return request.app.state.pipeline_service.get(pipeline_id)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc


@router.get("/{pipeline_id}/stages/{stage_id}", response_model=dict)
def get_stage(pipeline_id: str, stage_id: str, request: Request) -> dict:
    try:
        pipeline = request.app.state.pipeline_service.get(pipeline_id)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc
    for stage in pipeline.stages:
        if stage.id == stage_id:
            return stage.model_dump(mode="json")
    raise HTTPException(status_code=404, detail=f"Stage not found: {stage_id}")


@router.post("/{pipeline_id}/run", response_model=PipelineRecord)
async def run_pipeline(pipeline_id: str, payload: PipelineRunInput, request: Request) -> PipelineRecord:
    try:
        run: PipelineRun = request.app.state.pipeline_runner.start_run(pipeline_id, payload)
        # Keep backward-compatible response shape: return pipeline view immediately.
        return request.app.state.pipeline_service.get(pipeline_id)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post("/{pipeline_id}/start", response_model=PipelineRun)
def start_pipeline(pipeline_id: str, payload: PipelineRunInput, request: Request) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.start_run(pipeline_id, payload)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc


@router.post("/{pipeline_id}/pause", response_model=PipelineRun)
def pause_pipeline(pipeline_id: str, request: Request, run_id: str | None = None) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.pause_run(pipeline_id, run_id)
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post("/{pipeline_id}/resume", response_model=PipelineRun)
def resume_pipeline(pipeline_id: str, request: Request, run_id: str | None = None) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.resume_run(pipeline_id, run_id)
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post("/{pipeline_id}/terminate", response_model=PipelineRun)
def terminate_pipeline(pipeline_id: str, request: Request, run_id: str | None = None) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.terminate_run(pipeline_id, run_id)
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.get("/{pipeline_id}/runs/{run_id}", response_model=PipelineRun)
def get_run(pipeline_id: str, run_id: str, request: Request) -> PipelineRun:
    try:
        return request.app.state.pipeline_runner.get_run(pipeline_id, run_id)
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post("/{pipeline_id}/stages/{stage_id}/run", response_model=PipelineRecord)
async def run_stage(pipeline_id: str, stage_id: str, payload: StageRunInput, request: Request) -> PipelineRecord:
    try:
        return await request.app.state.pipeline_service.run_stage(pipeline_id, stage_id, payload)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post("/{pipeline_id}/stages/{stage_id}/approve", response_model=PipelineRecord)
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


@router.post("/{pipeline_id}/stages/{stage_id}/reject", response_model=PipelineRecord)
def reject_stage(pipeline_id: str, stage_id: str, payload: ApprovalRequest, request: Request) -> PipelineRecord:
    try:
        return request.app.state.approval_service.reject(pipeline_id, stage_id, payload)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Stage not found: {stage_id}") from exc
    except Exception as exc:
        raise stage_error_to_http(exc) from exc
