from __future__ import annotations

from pathlib import Path
from typing import Any

from .nodes import (
    compute_static_html_facts,
    detect_archetype,
    generate_test_files,
    generate_test_plan,
    materialize_task_copy,
    resolve_inputs,
    run_tests,
    write_outputs,
    _max_llm_calls,
)
from .schemas import CodeTestState


PIPELINE = [
    resolve_inputs,
    materialize_task_copy,
    detect_archetype,
    compute_static_html_facts,
    generate_test_plan,
    generate_test_files,
    run_tests,
    write_outputs,
]


def build_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError:
        return None

    workflow = StateGraph(CodeTestState)

    workflow.add_node("resolve_inputs", resolve_inputs)
    workflow.add_node("materialize_task_copy", materialize_task_copy)
    workflow.add_node("detect_archetype", detect_archetype)
    workflow.add_node("compute_static_html_facts", compute_static_html_facts)
    workflow.add_node("generate_test_plan", generate_test_plan)
    workflow.add_node("generate_test_files", generate_test_files)
    workflow.add_node("run_tests", run_tests)
    workflow.add_node("write_outputs", write_outputs)

    workflow.set_entry_point("resolve_inputs")
    workflow.add_edge("resolve_inputs", "materialize_task_copy")
    workflow.add_edge("materialize_task_copy", "detect_archetype")
    workflow.add_edge("detect_archetype", "compute_static_html_facts")
    workflow.add_edge("compute_static_html_facts", "generate_test_plan")
    workflow.add_edge("generate_test_plan", "generate_test_files")
    workflow.add_edge("generate_test_files", "run_tests")
    workflow.add_edge("run_tests", "write_outputs")
    workflow.add_edge("write_outputs", END)

    return workflow.compile()


def run_codetest(
    *,
    codegen_result_path: str | None,
    design_path: str | None,
    diff_path: str | None,
    repo_path: str | None,
    requirement_path: str | None,
    task_id: str | None,
    output_dir: str,
    workspace_dir: str,
    local_only: bool,
    force: bool,
    max_llm_calls: int | None = None,
    repair_feedback_path: str | None = None,
) -> CodeTestState:
    cap = max_llm_calls if max_llm_calls is not None else _max_llm_calls()
    initial: CodeTestState = {
        "codegen_result_path": str(Path(codegen_result_path).resolve()) if codegen_result_path else None,
        "design_path": design_path,
        "diff_path": diff_path,
        "repo_path": str(Path(repo_path).resolve()) if repo_path else None,
        "requirement_path": str(Path(requirement_path).resolve()) if requirement_path else None,
        "task_id": task_id or "",
        "output_dir": str(Path(output_dir).resolve()),
        "workspace_dir": str(Path(workspace_dir).resolve()),
        "local_only": local_only,
        "force": force,
        "max_llm_calls": cap,
        "repair_feedback_path": Path(repair_feedback_path).resolve().as_posix()
        if repair_feedback_path and str(repair_feedback_path).strip()
        else None,
        "llm_calls": 0,
        "warnings": [],
        "errors": [],
    }
    graph = build_graph()
    if graph is not None:
        return graph.invoke(initial)

    state = initial
    for node in PIPELINE:
        state = node(state)
    return state
