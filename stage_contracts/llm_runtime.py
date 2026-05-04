from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from pydantic import BaseModel, Field


class LLMRuntimeConfig(BaseModel):
    provider: str
    model: str | None = None
    base_url: str | None = None
    api_key_env: str | None = None
    temperature: float | None = None
    timeout_seconds: float | None = None
    max_retries: int | None = None
    local_only: bool = False
    use_real_llm: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        configured = False
        if self.api_key_env:
            configured = bool(os.getenv(self.api_key_env))
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "local_only": self.local_only,
            "use_real_llm": self.use_real_llm,
            "configured": configured,
            "metadata": dict(self.metadata),
        }


_CURRENT_LLM_CONFIG: ContextVar[LLMRuntimeConfig | None] = ContextVar("deliverax_llm_runtime_config", default=None)


def set_current_llm_config(config: LLMRuntimeConfig | None) -> None:
    _CURRENT_LLM_CONFIG.set(config)


def get_current_llm_config() -> LLMRuntimeConfig | None:
    return _CURRENT_LLM_CONFIG.get()


@contextmanager
def llm_config_context(config: LLMRuntimeConfig | None):
    token = _CURRENT_LLM_CONFIG.set(config)
    try:
        yield
    finally:
        _CURRENT_LLM_CONFIG.reset(token)
