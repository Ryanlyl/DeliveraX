from __future__ import annotations

from pathlib import Path
from typing import Any

from .nodes import (
    apply_changes,
    generate_changes,
    generate_diff,
    load_design,
    load_file_context,
    resolve_workspace,
    smoke_check,
    write_outputs,
)
from .schemas import CodeGenState
from .task_workspace import make_task_id


PIPELINE = [
    load_design,
    resolve_workspace,
    load_file_context,
    generate_changes,
    apply_changes,
    generate_diff,
    smoke_check,
    write_outputs,
]


def build_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError:
        return None

    workflow = StateGraph(CodeGenState)

    workflow.add_node("load_design", load_design)
    workflow.add_node("resolve_workspace", resolve_workspace)
    workflow.add_node("load_file_context", load_file_context)
    workflow.add_node("generate_changes", generate_changes)
    workflow.add_node("apply_changes", apply_changes)
    workflow.add_node("generate_diff", generate_diff)
    workflow.add_node("smoke_check", smoke_check)
    workflow.add_node("write_outputs", write_outputs)

    workflow.set_entry_point("load_design")
    workflow.add_edge("load_design", "resolve_workspace")
    workflow.add_edge("resolve_workspace", "load_file_context")
    workflow.add_edge("load_file_context", "generate_changes")
    workflow.add_edge("generate_changes", "apply_changes")
    workflow.add_edge("apply_changes", "generate_diff")
    workflow.add_edge("generate_diff", "smoke_check")
    workflow.add_edge("smoke_check", "write_outputs")
    workflow.add_edge("write_outputs", END)

    return workflow.compile()


def run_codegen(
    *,
    design_path: str,
    repo_path: str | None,
    workspace_dir: str | None,
    task_id: str | None,
    output_dir: str,
    local_only: bool = False,
    max_context_files: int = 32,
    max_file_chars: int = 24000,
) -> CodeGenState:
    resolved_design_path = str(Path(design_path).resolve())
    resolved_task_id = make_task_id(resolved_design_path, task_id)
    initial_state: CodeGenState = {
        "design_path": resolved_design_path,
        "repo_path": str(Path(repo_path).resolve()) if repo_path else None,
        "workspace_dir": str(Path(workspace_dir).resolve()) if workspace_dir else None,
        "task_id": resolved_task_id,
        "output_dir": str(Path(output_dir).resolve()),
        "local_only": local_only,
        "max_context_files": max_context_files,
        "max_file_chars": max_file_chars,
        "warnings": [],
        "errors": [],
    }
    graph = build_graph()
    if graph is not None:
        return graph.invoke(initial_state)

    state = initial_state
    for node in PIPELINE:
        state = node(state)
    return state
