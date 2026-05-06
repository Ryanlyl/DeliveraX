from __future__ import annotations

from collections.abc import Mapping, Sequence

from api_server.engine.models import PipelineDefinition, PipelineDefinitionError
from stage_contracts import ArtifactRef


def topological_stage_order(definition: PipelineDefinition) -> list[str]:
    stage_ids = [stage.id for stage in definition.stages]
    if len(stage_ids) != len(set(stage_ids)):
        raise PipelineDefinitionError("Pipeline definition contains duplicate stage ids")

    known_stage_ids = set(stage_ids)
    indegree = {stage_id: 0 for stage_id in stage_ids}
    dependents = {stage_id: [] for stage_id in stage_ids}

    for stage in definition.stages:
        for dependency_id in stage.depends_on:
            if dependency_id not in known_stage_ids:
                raise PipelineDefinitionError(
                    f"Stage '{stage.id}' depends on unknown stage '{dependency_id}'"
                )
            indegree[stage.id] += 1
            dependents[dependency_id].append(stage.id)

    ready = [stage_id for stage_id in stage_ids if indegree[stage_id] == 0]
    ordered: list[str] = []

    while ready:
        stage_id = ready.pop(0)
        ordered.append(stage_id)
        for dependent_id in dependents[stage_id]:
            indegree[dependent_id] -= 1
            if indegree[dependent_id] == 0:
                ready.append(dependent_id)

    if len(ordered) != len(stage_ids):
        cycle_stage_ids = [stage_id for stage_id in stage_ids if indegree[stage_id] > 0]
        raise PipelineDefinitionError(
            "Pipeline definition contains a cycle involving stages: "
            + ", ".join(cycle_stage_ids)
        )

    return ordered


def collect_upstream_artifacts(
    stage_id: str,
    completed_artifacts: Mapping[str, Sequence[ArtifactRef]],
    definition: PipelineDefinition | None = None,
) -> list[ArtifactRef]:
    allowed_stage_ids = _upstream_stage_ids(definition, stage_id) if definition is not None else None
    artifacts: list[ArtifactRef] = []

    for completed_stage_id, refs in reversed(list(completed_artifacts.items())):
        if completed_stage_id == stage_id:
            continue
        if allowed_stage_ids is not None and completed_stage_id not in allowed_stage_ids:
            continue
        for ref in refs:
            if not isinstance(ref, ArtifactRef):
                raise TypeError("Pipeline stage artifacts must be ArtifactRef instances")
            artifacts.append(ref)

    return artifacts


def _upstream_stage_ids(definition: PipelineDefinition, stage_id: str) -> set[str]:
    stages_by_id = {stage.id: stage for stage in definition.stages}
    if stage_id not in stages_by_id:
        raise PipelineDefinitionError(f"Unknown stage_id: {stage_id}")

    upstream: set[str] = set()

    def visit(current_stage_id: str) -> None:
        for dependency_id in stages_by_id[current_stage_id].depends_on:
            if dependency_id not in stages_by_id:
                raise PipelineDefinitionError(
                    f"Stage '{current_stage_id}' depends on unknown stage '{dependency_id}'"
                )
            if dependency_id in upstream:
                continue
            upstream.add(dependency_id)
            visit(dependency_id)

    visit(stage_id)
    return upstream
