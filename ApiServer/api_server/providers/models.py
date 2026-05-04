from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


ProviderKind = Literal["openai-compatible", "anthropic"]


class ProviderDefinition(BaseModel):
    id: str
    name: str
    kind: ProviderKind
    default_model: str | None = None
    default_base_url: str | None = None
    api_key_env: str | None = None
    available: bool = True
    notes: str | None = None
