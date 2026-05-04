from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api_server.routers.stages import stage_error_to_http
from api_server.schemas import (
    CheckpointDecisionRequest,
    CurrentCheckpointResponse,
    PipelineRecord,
    PipelineRunInput,
)
from api_server.services.checkpoint_service import CheckpointNotFoundError
from api_server.storage.json_store import PipelineNotFoundError

router = APIRouter(tags=["checkpoints"])


@router.get(
    "/pipelines/{pipeline_id}/checkpoints/current",
    response_model=CurrentCheckpointResponse,
)
def get_current_checkpoint(pipeline_id: str, request: Request) -> CurrentCheckpointResponse:
    try:
        return request.app.state.checkpoint_service.get_current_checkpoint(pipeline_id)
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}") from exc


@router.post("/checkpoints/{checkpoint_id}/approve", response_model=PipelineRecord)
async def approve_checkpoint(
    checkpoint_id: str,
    payload: CheckpointDecisionRequest,
    request: Request,
) -> PipelineRecord:
    try:
        pipeline = request.app.state.checkpoint_service.approve(checkpoint_id, payload)
        if not payload.continue_pipeline:
            return pipeline
        return await _continue_pipeline(pipeline, request)
    except CheckpointNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Checkpoint not found: {checkpoint_id}") from exc
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pipeline not found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Stage not found: {exc}") from exc
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


@router.post("/checkpoints/{checkpoint_id}/reject", response_model=PipelineRecord)
def reject_checkpoint(
    checkpoint_id: str,
    payload: CheckpointDecisionRequest,
    request: Request,
) -> PipelineRecord:
    try:
        if not (payload.reason or payload.comment):
            payload.reason = "Rejected by human checkpoint reviewer."
        return request.app.state.checkpoint_service.reject(checkpoint_id, payload)
    except CheckpointNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Checkpoint not found: {checkpoint_id}") from exc
    except PipelineNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pipeline not found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Stage not found: {exc}") from exc
    except Exception as exc:
        raise stage_error_to_http(exc) from exc


async def _continue_pipeline(pipeline: PipelineRecord, request: Request) -> PipelineRecord:
    latest_run_id = pipeline.latest_run_id
    if latest_run_id:
        request.app.state.pipeline_runner.resume_run(pipeline.id, latest_run_id)
        return request.app.state.pipeline_service.get(pipeline.id)

    next_stage_id = _next_queued_stage_id(pipeline)
    if next_stage_id is None:
        return pipeline
    return await request.app.state.pipeline_service.run_pipeline(
        pipeline.id,
        PipelineRunInput(start_stage_id=next_stage_id),
    )


def _next_queued_stage_id(pipeline: PipelineRecord) -> str | None:
    for stage in pipeline.stages:
        if stage.status == "queued":
            return stage.id
    return None
