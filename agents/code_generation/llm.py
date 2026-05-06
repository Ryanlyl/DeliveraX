from __future__ import annotations

import os
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI
from stage_contracts.llm_runtime import get_current_llm_config

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is optional at runtime
    load_dotenv = None  # type: ignore[assignment]


@dataclass(frozen=True)
class LLMConfig:
    api_key: str | None
    model: str
    base_url: str | None
    temperature: float = 0.1
    timeout_seconds: float = 180.0
    max_retries: int = 0


def load_llm_config() -> LLMConfig:
    runtime = get_current_llm_config()
    if runtime is not None:
        api_key = (
            os.getenv(runtime.api_key_env)
            if runtime.api_key_env and runtime.use_real_llm and not runtime.local_only
            else None
        )
        model = runtime.model or os.getenv("CODEGEN_MODEL") or os.getenv("LLM_MODEL")
        if not model:
            model = "deepseek-chat" if os.getenv("DEEPSEEK_API_KEY") else "gpt-4o-mini"
        base_url = runtime.base_url
        timeout_seconds = float(runtime.timeout_seconds) if runtime.timeout_seconds is not None else 180.0
        max_retries = int(runtime.max_retries) if runtime.max_retries is not None else 0
        temperature = float(runtime.temperature) if runtime.temperature is not None else 0.1
        return LLMConfig(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    if load_dotenv:
        load_dotenv()

    api_key = (
        os.getenv("CODEGEN_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    base_url = (
        os.getenv("CODEGEN_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
    )
    model = os.getenv("CODEGEN_MODEL") or os.getenv("LLM_MODEL")
    if not model:
        model = "deepseek-chat" if os.getenv("DEEPSEEK_API_KEY") else "gpt-4o-mini"
    if not base_url and model.lower().startswith("deepseek"):
        base_url = "https://api.deepseek.com"
    timeout_seconds = _float_env("CODEGEN_LLM_TIMEOUT_SECONDS", 180.0)
    max_retries = _int_env("CODEGEN_LLM_MAX_RETRIES", 0)
    return LLMConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


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
            raise RuntimeError("LLM is not configured. Set CODEGEN_API_KEY or run with --local-only.")
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
        content = response.choices[0].message.content
        return content or ""


def _auth_error_message(config: LLMConfig) -> str:
    endpoint = config.base_url or "https://api.openai.com/v1"
    hints = [
        "LLM authentication failed (401).",
        f"Model: {config.model}",
        f"Endpoint: {endpoint}",
        "Check that CODEGEN_API_KEY matches this endpoint.",
    ]
    if config.model.lower().startswith("deepseek") and "deepseek" not in endpoint.lower():
        hints.append("For DeepSeek, set CODEGEN_BASE_URL=https://api.deepseek.com.")
    elif "openai.com" in endpoint.lower():
        hints.append("For OpenAI, use a valid OpenAI API key or clear CODEGEN_BASE_URL if it points elsewhere.")
    else:
        hints.append("For OpenAI-compatible providers, set CODEGEN_BASE_URL to that provider's base URL.")
    return " ".join(hints)


def _timeout_error_message(config: LLMConfig) -> str:
    return (
        "LLM request timed out. "
        f"Model: {config.model}. "
        f"Endpoint: {config.base_url or 'https://api.openai.com/v1'}. "
        f"Timeout: {config.timeout_seconds}s. "
        "Code generation responses can be long; try increasing CODEGEN_LLM_TIMEOUT_SECONDS, "
        "or reduce --max-context-files / --max-file-chars."
    )


def _connection_error_message(config: LLMConfig) -> str:
    return (
        "LLM connection failed. "
        f"Endpoint: {config.base_url or 'https://api.openai.com/v1'}. "
        "Check network connectivity, proxy settings, and provider availability."
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
