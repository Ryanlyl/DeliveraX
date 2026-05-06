from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from api_server.engine.config_loader import load_default_pipeline_definition
from api_server.providers.resolver import resolve_llm_config
from api_server.schemas import LLMSelection, PipelineCreateRequest, PipelineRecord
from api_server.services.pipeline_service import PipelineService
from api_server.services.stage_executor import StageExecutor
from api_server.stage_registry import StageRegistry
from api_server.storage.json_store import JsonPipelineStore


def _pipeline(*, provider: str = "local") -> PipelineRecord:
    return PipelineRecord(
        id="p",
        name="p",
        provider=provider,
        requirement="req",
    )


def test_stage_override_wins_over_pipeline_global_config() -> None:
    definition = load_default_pipeline_definition()
    stage = definition.stage_by_id("solution")

    pipeline = _pipeline(provider="openai")
    pipeline.model = "gpt-4o-mini"
    pipeline.temperature = 0.3
    pipeline.stage_overrides = {
        "solution": LLMSelection(provider="deepseek", model="deepseek-chat", temperature=0.1)
    }

    config, _ = resolve_llm_config(
        pipeline=pipeline,
        pipeline_definition=definition,
        stage_definition=stage,
        run_options={},
    )

    assert config.provider == "deepseek"
    assert config.model == "deepseek-chat"
    assert config.temperature == 0.1


def test_run_option_override_wins_over_stage_override() -> None:
    definition = load_default_pipeline_definition()
    stage = definition.stage_by_id("solution")

    pipeline = _pipeline(provider="openai")
    pipeline.stage_overrides = {"solution": LLMSelection(provider="deepseek", model="deepseek-chat")}

    config, _ = resolve_llm_config(
        pipeline=pipeline,
        pipeline_definition=definition,
        stage_definition=stage,
        run_options={"llm": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.2}},
    )

    assert config.provider == "openai"
    assert config.model == "gpt-4o-mini"
    assert config.temperature == 0.2


def test_safe_llm_payload_contains_no_api_key() -> None:
    definition = load_default_pipeline_definition()
    stage = definition.stage_by_id("solution")
    pipeline = _pipeline(provider="openai")

    config, _ = resolve_llm_config(
        pipeline=pipeline,
        pipeline_definition=definition,
        stage_definition=stage,
        run_options={},
    )

    payload = config.to_safe_dict()
    assert "api_key" not in payload
    assert payload.get("api_key_env") in {"OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", None}


def test_pipeline_create_saves_llm_selection_without_api_key() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)
    registry = StageRegistry(repo_root)
    service = PipelineService(
        store=JsonPipelineStore(tmp_root),
        registry=registry,
        executor=StageExecutor(registry),
        artifacts_root=str(tmp_root),
    )

    try:
        pipeline = service.create(
            PipelineCreateRequest(
                pipeline_id="llm-selection-demo",
                requirement="demo",
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.4,
                options={"api_key": "sk-should-not-be-stored", "safe": True},
                stage_overrides={
                    "solution": LLMSelection(
                        provider="deepseek",
                        model="deepseek-chat",
                        temperature=0.1,
                        options={"api_key": "sk-stage", "api_key_env": "DEEPSEEK_API_KEY"},
                    )
                },
            )
        )

        loaded = service.get(pipeline.id)
        assert loaded.provider == "openai"
        assert loaded.model == "gpt-4o-mini"
        assert loaded.temperature == 0.4
        assert loaded.stage_overrides["solution"].provider == "deepseek"
        assert loaded.stage_overrides["solution"].options == {"api_key_env": "DEEPSEEK_API_KEY"}
        assert "api_key" not in loaded.options
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
