from __future__ import annotations

import asyncio
import inspect

from api_server.stage_registry import StageRegistry
from stage_contracts import StageRunRequest, StageRunResult


class StageExecutor:
    def __init__(self, registry: StageRegistry) -> None:
        self.registry = registry

    async def run(self, request: StageRunRequest) -> StageRunResult:
        _, runner = self.registry.runner_for(request.stage_id)
        if inspect.iscoroutinefunction(runner):
            return await runner(request)
        return await asyncio.to_thread(runner, request)
