from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI
from stage_contracts.llm_runtime import get_current_llm_config


@dataclass(frozen=True)
class LLMConfig:
    api_key: str | None
    model: str
    base_url: str | None
    temperature: float = 0.2


def load_llm_config() -> LLMConfig:
    runtime = get_current_llm_config()
    if runtime is not None:
        api_key = (
            os.getenv(runtime.api_key_env)
            if runtime.api_key_env and runtime.use_real_llm and not runtime.local_only
            else None
        )
        base_url = runtime.base_url
        model = runtime.model or os.getenv("SOLUTION_DESIGN_MODEL") or os.getenv("LLM_MODEL")
        if not model:
            model = "deepseek-chat" if os.getenv("DEEPSEEK_API_KEY") else "gpt-4o-mini"
        temperature = float(runtime.temperature) if runtime.temperature is not None else 0.2
        return LLMConfig(api_key=api_key, model=model, base_url=base_url, temperature=temperature)

    api_key = (
        os.getenv("SOLUTION_DESIGN_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    base_url = (
        os.getenv("SOLUTION_DESIGN_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
    )
    model = os.getenv("SOLUTION_DESIGN_MODEL") or os.getenv("LLM_MODEL")
    if not model:
        model = "deepseek-chat" if os.getenv("DEEPSEEK_API_KEY") else "gpt-4o-mini"

    return LLMConfig(api_key=api_key, model=model, base_url=base_url)


class ChatLLM:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or load_llm_config()
        if not self.config.api_key:
            self.client: OpenAI | None = None
            return
        kwargs: dict[str, str] = {"api_key": self.config.api_key}
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url
        self.client = OpenAI(**kwargs)

    @property
    def available(self) -> bool:
        return self.client is not None

    def complete(self, *, system: str, user: str) -> str:
        if not self.client:
            raise RuntimeError("LLM is not configured. Set SOLUTION_DESIGN_API_KEY or run with --local-only.")
        response = self.client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return content or ""

