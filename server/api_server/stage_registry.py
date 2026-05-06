from __future__ import annotations

import importlib
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from api_server.bootstrap import ensure_repo_paths
from api_server.engine.config_loader import load_default_pipeline_definition
from api_server.engine.models import PipelineDefinition
from api_server.engine.planner import topological_stage_order

ensure_repo_paths()

from stage_contracts import StageRunRequest, StageRunResult

StageRunner = Callable[[StageRunRequest], StageRunResult | Awaitable[StageRunResult]]


@dataclass(frozen=True)
class StageDefinition:
    id: str
    name: str
    agent: str
    module: str | None
    checkpoint: bool = False
    checkpoint_label: str | None = None
    checkpoint_description: str | None = None
    description: str | None = None
    depends_on: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return bool(self.module)


def _legacy_stage_definitions(definition: PipelineDefinition) -> tuple[StageDefinition, ...]:
    stages_by_id: dict[str, StageDefinition] = {}
    for stage in definition.stages:
        agent_names: list[str] = []
        for agent_id in stage.agent_ids:
            try:
                agent_names.append(definition.agent_by_id(agent_id).name)
            except KeyError:
                agent_names.append(agent_id)
        stages_by_id[stage.id] = StageDefinition(
            id=stage.id,
            name=stage.name,
            agent=", ".join(agent_names),
            module=stage.module,
            depends_on=tuple(stage.depends_on),
            checkpoint=stage.checkpoint,
            checkpoint_label=stage.checkpoint_label,
            checkpoint_description=stage.checkpoint_description,
            description=stage.description,
        )

    return tuple(stages_by_id[stage_id] for stage_id in topological_stage_order(definition))


STAGE_DEFINITIONS: tuple[StageDefinition, ...] = _legacy_stage_definitions(load_default_pipeline_definition())


class StageNotFoundError(ValueError):
    pass


class StageUnavailableError(RuntimeError):
    pass


class StageRegistry:
    def __init__(self, repo_root: Path, pipeline_definition: PipelineDefinition | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.pipeline_definition = pipeline_definition or load_default_pipeline_definition()
        self._definitions = _legacy_stage_definitions(self.pipeline_definition)
        self._definitions_by_id = {stage.id: stage for stage in self._definitions}
        self._ensure_import_paths()

    def list(self) -> list[StageDefinition]:
        return list(self._definitions)

    def get(self, stage_id: str) -> StageDefinition:
        try:
            return self._definitions_by_id[stage_id]
        except KeyError as exc:
            raise StageNotFoundError(f"Unknown stage_id: {stage_id}") from exc

    def next_stage_after(self, stage_id: str) -> StageDefinition | None:
        stages = self.list()
        for index, stage in enumerate(stages):
            if stage.id == stage_id and index + 1 < len(stages):
                return stages[index + 1]
        return None

    def runner_for(self, stage_id: str) -> tuple[StageDefinition, StageRunner]:
        stage = self.get(stage_id)
        if not stage.module:
            raise StageUnavailableError(f"Stage is not connected yet: {stage_id}")
        module = importlib.import_module(stage.module)
        runner = getattr(module, "run_stage", None)
        if runner is None or not callable(runner):
            raise StageUnavailableError(f"Stage module does not expose run_stage(): {stage.module}")
        return stage, runner

    def is_async_runner(self, runner: StageRunner) -> bool:
        return inspect.iscoroutinefunction(runner)

    def _ensure_import_paths(self) -> None:
        ensure_repo_paths(self.repo_root)
