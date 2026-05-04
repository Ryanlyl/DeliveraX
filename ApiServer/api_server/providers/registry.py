from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from api_server.providers.models import ProviderDefinition


@lru_cache
def provider_registry() -> dict[str, ProviderDefinition]:
    providers = [
        ProviderDefinition(
            id="openai",
            name="OpenAI",
            kind="openai-compatible",
            default_base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            default_model="gpt-4o-mini",
            available=True,
        ),
        ProviderDefinition(
            id="deepseek",
            name="DeepSeek",
            kind="openai-compatible",
            default_base_url="https://api.deepseek.com",
            api_key_env="DEEPSEEK_API_KEY",
            default_model="deepseek-chat",
            available=True,
        ),
        ProviderDefinition(
            id="anthropic",
            name="Anthropic",
            kind="anthropic",
            api_key_env="ANTHROPIC_API_KEY",
            default_model="claude-3-5-sonnet-latest",
            available=False,
            notes="experimental/unavailable in DeliveraX Phase 3",
        ),
    ]
    return {provider.id: provider for provider in providers}


def list_provider_public() -> list[dict[str, Any]]:
    registry = provider_registry()
    result: list[dict[str, Any]] = []
    for provider in registry.values():
        configured = False
        if provider.api_key_env:
            configured = bool(os.getenv(provider.api_key_env))
        result.append(
            {
                "id": provider.id,
                "name": provider.name,
                "kind": provider.kind,
                "default_model": provider.default_model,
                "default_base_url": provider.default_base_url,
                "api_key_env": provider.api_key_env,
                "available": provider.available,
                "configured": configured,
                "notes": provider.notes,
            }
        )
    return result
