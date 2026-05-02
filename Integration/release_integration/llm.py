from __future__ import annotations

import os
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional runtime helper
    load_dotenv = None  # type: ignore[assignment]


@dataclass(frozen=True)
class LLMConfig:
    api_key: str | None
    model: str | None
    base_url: str | None
    temperature: float = 0.1
    timeout_seconds: float = 180.0
    max_retries: int = 0


def load_llm_config() -> LLMConfig:
    if load_dotenv:
        load_dotenv()

    api_key = (
        os.getenv("DELIVERY_INTEGRATION_LLM_API_KEY")
        or os.getenv("DELIVERY_INTEGRATION_API_KEY")
        or os.getenv("DELIVERY_INTEGRATION_DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
    )
    base_url = (
        os.getenv("DELIVERY_INTEGRATION_LLM_BASE_URL")
        or os.getenv("DELIVERY_INTEGRATION_BASE_URL")
        or os.getenv("DELIVERY_INTEGRATION_DEEPSEEK_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
    )
    model = (
        os.getenv("DELIVERY_INTEGRATION_LLM_MODEL")
        or os.getenv("DELIVERY_INTEGRATION_MODEL")
        or os.getenv("DELIVERY_INTEGRATION_DEEPSEEK_MODEL")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("DEEPSEEK_MODEL")
        or os.getenv("LLM_MODEL")
    )

    return LLMConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=_float_env("DELIVERY_INTEGRATION_LLM_TEMPERATURE", 0.1),
        timeout_seconds=_float_env("DELIVERY_INTEGRATION_LLM_TIMEOUT_SECONDS", 180.0),
        max_retries=_int_env("DELIVERY_INTEGRATION_LLM_MAX_RETRIES", 0),
    )


class ChatLLM:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or load_llm_config()
        if not self.config.api_key or not self.config.model:
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
            raise RuntimeError(
                "LLM is not configured. Set DELIVERY_INTEGRATION_LLM_API_KEY "
                "and DELIVERY_INTEGRATION_LLM_MODEL. Set DELIVERY_INTEGRATION_LLM_BASE_URL "
                "for non-default OpenAI-compatible providers."
            )
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                temperature=self.config.temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except AuthenticationError as exc:
            raise RuntimeError(_auth_error_message(self.config)) from exc
        except APITimeoutError as exc:
            raise RuntimeError(_timeout_error_message(self.config)) from exc
        except APIConnectionError as exc:
            raise RuntimeError(_connection_error_message(self.config)) from exc
        except APIStatusError as exc:
            if exc.status_code == 401:
                raise RuntimeError(_auth_error_message(self.config)) from exc
            raise
        return response.choices[0].message.content or ""


def _auth_error_message(config: LLMConfig) -> str:
    endpoint = config.base_url or "https://api.openai.com/v1"
    return (
        "Integration LLM authentication failed. "
        f"Model: {config.model}. Endpoint: {endpoint}. "
        "Check DELIVERY_INTEGRATION_LLM_API_KEY and DELIVERY_INTEGRATION_LLM_BASE_URL."
    )


def _timeout_error_message(config: LLMConfig) -> str:
    return (
        "Integration LLM request timed out. "
        f"Model: {config.model}. Timeout: {config.timeout_seconds}s. "
        "Try increasing DELIVERY_INTEGRATION_LLM_TIMEOUT_SECONDS or lowering --summary-max-diff-chars."
    )


def _connection_error_message(config: LLMConfig) -> str:
    return (
        "Integration LLM connection failed. "
        f"Endpoint: {config.base_url or 'https://api.openai.com/v1'}. "
        "Check DELIVERY_INTEGRATION_LLM_BASE_URL, network connectivity, and provider availability."
    )


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

