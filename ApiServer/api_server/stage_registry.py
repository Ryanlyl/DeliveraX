from __future__ import annotations

import importlib
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from api_server.bootstrap import ensure_repo_paths

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

    @property
    def available(self) -> bool:
        return bool(self.module)


STAGE_DEFINITIONS: tuple[StageDefinition, ...] = (
    StageDefinition(
        id="requirements",
        name="需求分析",
        agent="ReqAnalysis",
        module="requirement_analysis.stage",
        checkpoint=True,
        checkpoint_label="需求确认 / Requirement Review",
        checkpoint_description="AI 已生成结构化需求文档，请确认需求范围、验收标准与待确认问题是否准确。",
        description="自然语言需求转结构化需求与 PRD。",
    ),
    StageDefinition(
        id="solution",
        name="方案设计",
        agent="SolDesign",
        module="solution_design.stage",
        description="基于 PRD 与仓库上下文生成技术方案。",
    ),
    StageDefinition(
        id="code",
        name="代码生成",
        agent="CodeGen",
        module="code_generation.stage",
        description="基于技术方案生成代码变更 diff 和报告。",
    ),
    StageDefinition(
        id="test",
        name="测试生成",
        agent="CodeTest",
        module=None,
        description="占位阶段，等待 CodeTest 接入统一 run_stage 契约。",
    ),
    StageDefinition(
        id="review",
        name="代码评审",
        agent="ReviewGate",
        module=None,
        checkpoint=True,
        checkpoint_label="代码评审确认",
        checkpoint_description="AI 已生成代码评审报告，请确认是否允许进入交付集成阶段。",
        description="占位阶段，等待 ReviewGate 接入统一 run_stage 契约。",
    ),
    StageDefinition(
        id="integration",
        name="交付集成",
        agent="Integration",
        module="release_integration.stage",
        description="汇总代码、测试、评审结果并生成最终交付材料。",
    ),
)


class StageNotFoundError(ValueError):
    pass


class StageUnavailableError(RuntimeError):
    pass


class StageRegistry:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self._ensure_import_paths()

    def list(self) -> list[StageDefinition]:
        return list(STAGE_DEFINITIONS)

    def get(self, stage_id: str) -> StageDefinition:
        for stage in STAGE_DEFINITIONS:
            if stage.id == stage_id:
                return stage
        raise StageNotFoundError(f"Unknown stage_id: {stage_id}")

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
