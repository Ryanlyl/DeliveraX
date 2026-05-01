import os

import httpx

from .base import LlmProvider


async def deepseek_llm_call(prompt: str) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 Requirement Agent，只负责前端需求分析。"
                    "你必须输出合法 JSON，不要输出 Markdown，不要输出代码块。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "stream": False,
    }

    timeout = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json=payload,
        )

    if response.status_code >= 400:
        raise RuntimeError(
            "DeepSeek API request failed with status "
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
