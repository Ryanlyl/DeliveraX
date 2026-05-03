from __future__ import annotations

import os
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]


@dataclass(frozen=True)
class LLMConfig:
    api_key: str | None
    model: str
    base_url: str | None
    temperature: float = 0.2
    timeout_seconds: float = 180.0
    max_retries: int = 0


def load_llm_config() -> LLMConfig:
    if load_dotenv:
        load_dotenv()

    api_key = (
        os.getenv("CODETEST_API_KEY")
        or os.getenv("CODEGEN_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    base_url = (
        os.getenv("CODETEST_BASE_URL")
        or os.getenv("CODEGEN_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
    )
    model = os.getenv("CODETEST_MODEL") or os.getenv("CODEGEN_MODEL") or os.getenv("LLM_MODEL")
    if not model:
        model = "deepseek-chat" if os.getenv("DEEPSEEK_API_KEY") else "gpt-4o-mini"
    if not base_url and model.lower().startswith("deepseek"):
        base_url = "https://api.deepseek.com"
    timeout_seconds = _float_env("CODETEST_LLM_TIMEOUT_SECONDS", 180.0)
    max_retries = _int_env("CODETEST_LLM_MAX_RETRIES", 0)
    return LLMConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class ChatLLM:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or load_llm_config()
        if not self.config.api_key:
            self.client: OpenAI | None = None
            return
        kwargs: dict[str, object] = {
            "api_key": self.config.api_key,
            "timeout": self.config.timeout_seconds,
            "max_retries": self.config.max_retries,
        }
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url
        self.client = OpenAI(**kwargs)

    @property
    def available(self) -> bool:
        return self.client is not None

    def complete(self, *, system: str, user: str) -> str:
        if not self.client:
            raise RuntimeError("LLM is not configured. Set CODETEST_API_KEY or run with --local-only.")
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                temperature=self.config.temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            content = response.choices[0].message.content
            if not content:
                return ""
            return content.strip()
        except AuthenticationError as exc:
            raise RuntimeError(f"LLM authentication failed: {exc}") from exc
        except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
