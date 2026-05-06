from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from api_server.engine.models import PipelineDefinition, PipelineDefinitionError
from api_server.engine.planner import topological_stage_order


def load_pipeline_definition(path: str | Path) -> PipelineDefinition:
    config_path = Path(path)
    payload = _load_payload(config_path)
    try:
        definition = PipelineDefinition.model_validate(payload)
    except ValidationError as exc:
        raise PipelineDefinitionError(f"Invalid pipeline definition: {exc}") from exc
    _validate_pipeline_definition(definition)
    return definition


def load_default_pipeline_definition() -> PipelineDefinition:
    return load_pipeline_definition(Path(__file__).with_name("default_pipeline.json"))


def _load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PipelineDefinitionError(f"Pipeline definition file not found: {path}")

    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PipelineDefinitionError(f"Invalid JSON pipeline definition: {exc}") from exc
    elif suffix in {".yaml", ".yml"}:
        data = _load_yaml(text, path)
    else:
        raise PipelineDefinitionError(
            f"Unsupported pipeline definition format '{path.suffix}'. Use .json, .yaml, or .yml."
        )

    if not isinstance(data, dict):
        raise PipelineDefinitionError("Pipeline definition root must be an object")
    return data


def _load_yaml(text: str, path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise PipelineDefinitionError(
            f"PyYAML is required to load pipeline definition file: {path}"
        ) from exc

    data = yaml.safe_load(text)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise PipelineDefinitionError("Pipeline definition root must be an object")
    return data


def _validate_pipeline_definition(definition: PipelineDefinition) -> None:
    _validate_unique_ids("stage", [stage.id for stage in definition.stages])
    _validate_unique_ids("agent", [agent.id for agent in definition.agents])

    agent_ids = {agent.id for agent in definition.agents}
    stage_ids = {stage.id for stage in definition.stages}

    for stage in definition.stages:
        for agent_id in stage.agent_ids:
            if agent_id not in agent_ids:
                raise PipelineDefinitionError(
                    f"Stage '{stage.id}' references unknown agent '{agent_id}'"
                )
        for dependency_id in stage.depends_on:
            if dependency_id not in stage_ids:
                raise PipelineDefinitionError(
                    f"Stage '{stage.id}' depends on unknown stage '{dependency_id}'"
                )

    topological_stage_order(definition)


def _validate_unique_ids(label: str, ids: list[str]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for item_id in ids:
        if item_id in seen:
            duplicates.append(item_id)
        seen.add(item_id)
    if duplicates:
        raise PipelineDefinitionError(
            f"Pipeline definition contains duplicate {label} ids: {', '.join(duplicates)}"
        )
