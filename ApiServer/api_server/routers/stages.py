from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api_server.schemas import StageDefinitionResponse
from api_server.stage_registry import StageNotFoundError, StageUnavailableError

router = APIRouter(prefix="/stages", tags=["stages"])


@router.get("", response_model=list[StageDefinitionResponse])
def list_stages(request: Request) -> list[StageDefinitionResponse]:
    registry = request.app.state.stage_registry
    return [
        StageDefinitionResponse(
            id=stage.id,
            name=stage.name,
            agent=stage.agent,
            checkpoint=stage.checkpoint,
            description=stage.description,
            available=stage.available,
        )
        for stage in registry.list()
    ]


def stage_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, StageNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, StageUnavailableError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))
