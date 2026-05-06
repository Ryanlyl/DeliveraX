from __future__ import annotations

import asyncio
import inspect

from api_server.stage_registry import StageRegistry
from stage_contracts import StageRunRequest, StageRunResult
from stage_contracts.llm_runtime import LLMRuntimeConfig, llm_config_context


class StageExecutor:
    def __init__(self, registry: StageRegistry) -> None:
        self.registry = registry

    async def run(self, request: StageRunRequest) -> StageRunResult:
        _, runner = self.registry.runner_for(request.stage_id)
        llm_payload = request.options.get("llm") if isinstance(request.options, dict) else None
        config: LLMRuntimeConfig | None = None
        if isinstance(llm_payload, dict):
            if llm_payload.get("error"):
                # LLM resolution failed upstream — log warning but continue (stage may handle nil config)
                import logging
                logging.warning("LLM config error for stage %s: %s", request.stage_id, llm_payload.get("error"))
            else:
                try:
                    config = LLMRuntimeConfig.model_validate(llm_payload)
                except Exception:
                    config = None
        if inspect.iscoroutinefunction(runner):
            with llm_config_context(config):
                return await runner(request)
        with llm_config_context(config):
            return await asyncio.to_thread(runner, request)
