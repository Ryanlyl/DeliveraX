from __future__ import annotations

from fastapi import APIRouter

from api_server.providers.registry import list_provider_public
from api_server.schemas import ProviderPublicResponse

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get(
    "",
    response_model=list[ProviderPublicResponse],
    summary="列出所有可用的 AI Provider",
    description="返回所有注册的 Provider 信息，包括名称、类型、默认模型、可用状态和配置状态。前端可用于填充模型选择下拉。",
    response_description="Provider 列表",
)
def list_providers() -> list[ProviderPublicResponse]:
    raw = list_provider_public()
    result: list[ProviderPublicResponse] = []
    for item in raw:
        default_model = item.get("default_model")
        models: list[str] = []
        if default_model:
            models.append(default_model)
        result.append(
            ProviderPublicResponse(
                id=item["id"],
                name=item["name"],
                kind=item["kind"],
                default_model=default_model,
                default_base_url=item.get("default_base_url"),
                api_key_env=item.get("api_key_env"),
                available=item["available"],
                configured=item["configured"],
                notes=item.get("notes"),
                models=models,
            )
        )
    return result
