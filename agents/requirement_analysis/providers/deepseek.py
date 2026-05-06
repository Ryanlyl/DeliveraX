import os

import httpx

from stage_contracts.llm_runtime import get_current_llm_config

from .base import LlmProvider


async def deepseek_llm_call(prompt: str) -> str:
    runtime = get_current_llm_config()
    if runtime is not None and (runtime.local_only or not runtime.use_real_llm):
        raise RuntimeError("LLM runtime is configured for local-only execution")
    api_key_env = runtime.api_key_env if runtime is not None and runtime.api_key_env else "DEEPSEEK_API_KEY"
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"{api_key_env} is not configured")

    model = None
    if runtime is not None:
        model = runtime.model
    if not model:
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    temperature = 0.2
    if runtime is not None and runtime.temperature is not None:
        temperature = float(runtime.temperature)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 ReqAnalysis，只负责前端需求分析。"
                    "你必须输出合法 JSON，不要输出 Markdown，不要输出代码块。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "stream": False,
    }

    base_url = None
    if runtime is not None and runtime.base_url:
        base_url = runtime.base_url.rstrip("/")
    if not base_url:
        base_url = "https://api.deepseek.com"

    timeout_seconds = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60"))
    if runtime is not None and runtime.timeout_seconds is not None:
        timeout_seconds = float(runtime.timeout_seconds)

    max_retries = 0
    if runtime is not None and runtime.max_retries is not None:
        max_retries = int(runtime.max_retries)

    # Ensure we always time out deterministically (avoid hanging requests).
    request_timeout = httpx.Timeout(
        connect=min(10.0, timeout_seconds),
        read=timeout_seconds,
        write=timeout_seconds,
        pool=timeout_seconds,
    )
    url = (
        f"{base_url}/chat/completions"
        if not base_url.endswith("/v1")
        else f"{base_url}/chat/completions"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await asyncio.wait_for(
                    client.post(url, headers=headers, json=payload),
                    timeout=timeout_seconds + 5.0,
                )
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
            if attempt >= max_retries:
                raise
            # simple exponential backoff
            await asyncio.sleep(min(2.0 ** attempt, 8.0))

    if last_exc is not None:
        raise last_exc

    if response.status_code >= 400:
        raise RuntimeError(
            "LLM provider request failed with status "
            f"{response.status_code}: {response.text}"
        )

    data = response.json()
    content = (
        data.get("choices", [{}])[0].get("message", {}).get("content") or ""
    ).strip()
    if not content:
        raise RuntimeError("DeepSeek returned empty content")
    return content


class DeepSeekProvider(LlmProvider):
    name = "deepseek"

    async def call(self, prompt: str) -> str:
        return await deepseek_llm_call(prompt)
