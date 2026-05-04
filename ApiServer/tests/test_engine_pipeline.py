from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from api_server.engine.config_loader import (
    load_default_pipeline_definition,
    load_pipeline_definition,
)
from api_server.engine.models import PipelineDefinitionError
from api_server.engine.planner import topological_stage_order
from api_server.stage_registry import StageRegistry


def test_default_pipeline_loads_six_stages() -> None:
    definition = load_default_pipeline_definition()

    assert [stage.id for stage in definition.stages] == [
        "requirements",
        "solution",
        "code",
        "test",
        "review",
        "integration",
    ]
    assert len(definition.agents) == 6
    assert definition.stage_by_id("requirements").checkpoint is True
    assert definition.stage_by_id("solution").checkpoint is True
    assert definition.stage_by_id("solution").checkpoint_label == "方案设计审批"
    assert definition.stage_by_id("review").module == "review_gate.stage"


def test_default_pipeline_topological_order_is_current_chain() -> None:
    definition = load_default_pipeline_definition()

    assert topological_stage_order(definition) == [
        "requirements",
        "solution",
        "code",
        "test",
        "review",
        "integration",
    ]


def test_load_pipeline_definition_rejects_unknown_dependency() -> None:
    tmp_root = _tmp_root()
    tmp_root.mkdir(parents=True, exist_ok=True)
    path = tmp_root / "pipeline.json"
    try:
        payload = _pipeline_payload(
            [
                {"id": "requirements", "name": "Requirements", "depends_on": ["missing"]},
            ]
        )
        path.write_text(json.dumps(payload), encoding="utf-8")

        with pytest.raises(PipelineDefinitionError, match="unknown stage 'missing'"):
            load_pipeline_definition(path)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_load_pipeline_definition_rejects_cycle() -> None:
    tmp_root = _tmp_root()
    tmp_root.mkdir(parents=True, exist_ok=True)
    path = tmp_root / "pipeline.json"
    try:
        payload = _pipeline_payload(
            [
                {"id": "requirements", "name": "Requirements", "depends_on": ["solution"]},
                {"id": "solution", "name": "Solution", "depends_on": ["requirements"]},
            ]
        )
        path.write_text(json.dumps(payload), encoding="utf-8")

        with pytest.raises(PipelineDefinitionError, match="cycle"):
            load_pipeline_definition(path)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_stage_registry_projects_default_pipeline_definition() -> None:
    registry = StageRegistry(Path(__file__).resolve().parents[2])
    stages = registry.list()

    assert [stage.id for stage in stages] == [
        "requirements",
        "solution",
        "code",
        "test",
        "review",
        "integration",
    ]
    assert registry.get("review").available is True


def _pipeline_payload(stages: list[dict]) -> dict:
    return {
        "id": "test-pipeline",
        "name": "Test Pipeline",
        "version": "1.0.0",
        "agents": [{"id": "agent", "name": "Agent"}],
        "stages": [
            {
                "agent_ids": ["agent"],
                "module": "fake.stage",
                **stage,
            }
            for stage in stages
        ],
    }


def _tmp_root() -> Path:
    return Path(__file__).resolve().parents[2] / "tmp" / "api_server_tests" / uuid4().hex
