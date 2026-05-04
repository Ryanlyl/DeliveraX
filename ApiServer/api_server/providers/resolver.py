from __future__ import annotations

from typing import Any

from api_server.engine.models import AgentDefinition, PipelineDefinition, StageDefinition
from api_server.providers.registry import provider_registry
from api_server.schemas import LLMSelection, PipelineRecord
from stage_contracts import LLMRuntimeConfig


def _coalesce_str(*values: str | None) -> str | None:
    for value in values:
        if value is not None and str(value).strip():
            return str(value)
    return None


def _override_str(*values: str | None) -> str | None:
    return _coalesce_str(*reversed(values))


def _coalesce_float(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return float(value)
    return None


def _override_float(*values: float | None) -> float | None:
    return _coalesce_float(*reversed(values))


def _coalesce_bool(*values: bool | None) -> bool | None:
    for value in values:
        if value is not None:
            return bool(value)
    return None


def _override_bool(*values: bool | None) -> bool | None:
    return _coalesce_bool(*reversed(values))


def _option_value(selection: LLMSelection | None, key: str) -> Any:
    if selection is None:
        return None
    return selection.options.get(key)


def _safe_agent_dict(agent: AgentDefinition) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "system_prompt": agent.system_prompt,
        "accepted_input_artifact_types": list(getattr(agent, "accepted_input_artifact_types", []) or []),
        "output_artifact_contract": dict(getattr(agent, "output_artifact_contract", {}) or {}),
        "context_paths": list(agent.context_paths or []),
        "default_provider": getattr(agent, "default_provider", None) or agent.provider,
        "default_model": getattr(agent, "default_model", None) or agent.model,
    }


def resolve_llm_config(
    *,
    pipeline: PipelineRecord,
    pipeline_definition: PipelineDefinition,
    stage_definition: StageDefinition,
    run_options: dict[str, Any] | None = None,
) -> tuple[LLMRuntimeConfig, dict[str, Any]]:
    run_options = run_options or {}

    registry = provider_registry()

    stage_override = None
    if getattr(pipeline, "stage_overrides", None):
        stage_override = pipeline.stage_overrides.get(stage_definition.id)

    run_override = None
    if isinstance(run_options.get("llm"), dict):
        run_override = LLMSelection.model_validate(run_options["llm"])  # type: ignore[arg-type]

    stage_agent_ids = list(stage_definition.agent_ids or [])
    agents: list[AgentDefinition] = [pipeline_definition.agent_by_id(agent_id) for agent_id in stage_agent_ids]

    agent_provider = _coalesce_str(
        *((getattr(agent, "default_provider", None) or agent.provider) for agent in agents)
    )
    agent_model = _coalesce_str(*((getattr(agent, "default_model", None) or agent.model) for agent in agents))

    provider_id = _override_str(
        agent_provider,
        pipeline.provider,
        stage_override.provider if stage_override else None,
        run_override.provider if run_override else None,
    )
    if not provider_id:
        provider_id = "local"

    provider_def = registry.get(provider_id)

    default_model = provider_def.default_model if provider_def else None
    base_url = _override_str(
        provider_def.default_base_url if provider_def else None,
        _option_value(stage_override, "base_url"),
        _option_value(run_override, "base_url"),
    )
    api_key_env = _override_str(
        provider_def.api_key_env if provider_def else None,
        _option_value(stage_override, "api_key_env"),
        _option_value(run_override, "api_key_env"),
    )

    model = _override_str(
        default_model,
        agent_model,
        getattr(pipeline, "model", None),
        stage_override.model if stage_override else None,
        run_override.model if run_override else None,
    )

    temperature = _override_float(
        getattr(pipeline, "temperature", None),
        stage_override.temperature if stage_override else None,
        run_override.temperature if run_override else None,
    )

    local_only = bool(provider_id == "local")
    override_local_only = _override_bool(
        stage_override.local_only if stage_override else None,
        run_override.local_only if run_override else None,
    )
    if override_local_only is not None:
        local_only = override_local_only

    use_real_llm = bool(not local_only)
    override_use_real_llm = _override_bool(
        stage_override.use_real_llm if stage_override else None,
        run_override.use_real_llm if run_override else None,
    )
    if override_use_real_llm is not None:
        use_real_llm = override_use_real_llm and not local_only
        if not override_use_real_llm:
            local_only = True

    timeout_seconds = _override_float(
        _option_value(stage_override, "timeout_seconds"),
        _option_value(run_override, "timeout_seconds"),
    )
    max_retries_value = _coalesce_float(
        _option_value(run_override, "max_retries"),
        _option_value(stage_override, "max_retries"),
    )
    max_retries = int(max_retries_value) if max_retries_value is not None else None

    config = LLMRuntimeConfig(
        provider=provider_id,
        model=model,
        base_url=base_url,
        api_key_env=api_key_env,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        local_only=local_only,
        use_real_llm=use_real_llm,
        metadata={
            "agent_provider": agent_provider,
            "stage_id": stage_definition.id,
        },
    )

    agent_payload: dict[str, Any] = {
        "stage_agent_ids": stage_agent_ids,
        "agents": [_safe_agent_dict(agent) for agent in agents],
    }

    return config, agent_payload
