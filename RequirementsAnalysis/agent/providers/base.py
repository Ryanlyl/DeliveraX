from __future__ import annotations

from abc import ABC, abstractmethod


class LlmProvider(ABC):
    name: str = "unknown"

    @abstractmethod
    async def call(self, prompt: str) -> str:
        raise NotImplementedError
