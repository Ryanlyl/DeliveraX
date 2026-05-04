from __future__ import annotations

from fastapi import APIRouter

from api_server.providers.registry import list_provider_public

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
def list_providers() -> list[dict]:
    return list_provider_public()
