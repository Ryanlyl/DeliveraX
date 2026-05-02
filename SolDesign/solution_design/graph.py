from __future__ import annotations

from pathlib import Path
from typing import Any

from .nodes import (
    analyze_architecture,
    analyze_impact,
    load_requirement,
    plan_design,
    prepare_repository,
    review_design,
    scan_repository,
    validate_format,
    write_output,
)
from .schemas import SolDesignState


PIPELINE = [
    load_requirement,
    prepare_repository,
    scan_repository,
    analyze_architecture,
    analyze_impact,
    plan_design,
    validate_format,
    review_design,
    write_output,
]


def build_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError:
        return None

    workflow = StateGraph(SolDesignState)

    workflow.add_node("load_requirement", load_requirement)
    workflow.add_node("prepare_repository", prepare_repository)
    workflow.add_node("scan_repository", scan_repository)
    workflow.add_node("analyze_architecture", analyze_architecture)
    workflow.add_node("analyze_impact", analyze_impact)
    workflow.add_node("plan_design", plan_design)
    workflow.add_node("validate_format", validate_format)
    workflow.add_node("review_design", review_design)
    workflow.add_node("write_output", write_output)

    workflow.set_entry_point("load_requirement")
    workflow.add_edge("load_requirement", "prepare_repository")
    workflow.add_edge("prepare_repository", "scan_repository")
    workflow.add_edge("scan_repository", "analyze_architecture")
    workflow.add_edge("analyze_architecture", "analyze_impact")
    workflow.add_edge("analyze_impact", "plan_design")
    workflow.add_edge("plan_design", "validate_format")
    workflow.add_edge("validate_format", "review_design")
    workflow.add_edge("review_design", "write_output")
    workflow.add_edge("write_output", END)

    return workflow.compile()


def run_solution_design(
    *,
    requirement_path: str,
    repo_url: str | None,
    repo_path: str | None,
    repo_ref: str | None,
    output_dir: str,
    template_path: str,
    workspace_dir: str | None = None,
    task_id: str | None = None,
    local_only: bool = False,
    max_context_files: int = 24,
) -> SolDesignState:
    initial_state: SolDesignState = {
        "requirement_path": str(Path(requirement_path).resolve()),
        "repo_url": repo_url,
        "repo_path": str(Path(repo_path).resolve()) if repo_path else None,
        "repo_ref": repo_ref,
        "output_dir": str(Path(output_dir).resolve()),
        "template_path": str(Path(template_path).resolve()),
        "workspace_dir": workspace_dir,
        "task_id": task_id,
        "local_only": local_only,
        "max_context_files": max_context_files,
        "errors": [],
    }
    graph = build_graph()
    if graph is not None:
        return graph.invoke(initial_state)

    state = initial_state
    for node in PIPELINE:
        state = node(state)
    return state

