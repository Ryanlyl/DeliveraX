from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from api_server.schemas import ArtifactListResponse, ArtifactTextResponse
from api_server.services.artifact_service import ArtifactNotFoundError, UnsafeArtifactPathError

router = APIRouter(tags=["artifacts"])


@router.get("/pipelines/{pipeline_id}/stages/{stage_id}/artifacts", response_model=ArtifactListResponse)
def list_stage_artifacts(pipeline_id: str, stage_id: str, request: Request) -> ArtifactListResponse:
    return request.app.state.artifact_service.list_stage_artifacts(pipeline_id, stage_id)


@router.get("/artifacts/file", response_model=ArtifactTextResponse)
def read_artifact_file(request: Request, path: str = Query(...)) -> ArtifactTextResponse:
    try:
        return request.app.state.artifact_service.read_text(path)
    except ArtifactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path}") from exc
    except UnsafeArtifactPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
