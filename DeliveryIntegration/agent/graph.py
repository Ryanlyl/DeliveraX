from __future__ import annotations

from pathlib import Path
from typing import Any

from .nodes import (
    apply_reviewed_diff,
    create_integration_worktree,
    generate_delivery_summary,
    load_prevalidated_changes,
    package_merge_ready_output,
    resolve_solution_workspace_repo,
    verify_integrated_diff,
    verify_test_and_review_results,
)
from .schemas import DeliveryIntegrationState


PIPELINE = [
    load_prevalidated_changes,
    verify_test_and_review_results,
    resolve_solution_workspace_repo,
    create_integration_worktree,
    apply_reviewed_diff,
    verify_integrated_diff,
    generate_delivery_summary,
    package_merge_ready_output,
]


def build_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError:
        return None

    workflow = StateGraph(DeliveryIntegrationState)
    workflow.add_node("load_prevalidated_changes", load_prevalidated_changes)
    workflow.add_node("verify_test_and_review_results", verify_test_and_review_results)
    workflow.add_node("resolve_solution_workspace_repo", resolve_solution_workspace_repo)
    workflow.add_node("create_integration_worktree", create_integration_worktree)
    workflow.add_node("apply_reviewed_diff", apply_reviewed_diff)
    workflow.add_node("verify_integrated_diff", verify_integrated_diff)
    workflow.add_node("generate_delivery_summary", generate_delivery_summary)
    workflow.add_node("package_merge_ready_output", package_merge_ready_output)

    workflow.set_entry_point("load_prevalidated_changes")
    workflow.add_edge("load_prevalidated_changes", "verify_test_and_review_results")
    workflow.add_edge("verify_test_and_review_results", "resolve_solution_workspace_repo")
    workflow.add_edge("resolve_solution_workspace_repo", "create_integration_worktree")
    workflow.add_edge("create_integration_worktree", "apply_reviewed_diff")
    workflow.add_edge("apply_reviewed_diff", "verify_integrated_diff")
    workflow.add_edge("verify_integrated_diff", "generate_delivery_summary")
    workflow.add_edge("generate_delivery_summary", "package_merge_ready_output")
    workflow.add_edge("package_merge_ready_output", END)
    return workflow.compile()


def run_delivery_integration(
    *,
    codegen_result_path: str | None,
    changeset_path: str | None,
    test_result_path: str | None,
    review_result_path: str | None,
    test_status: str | None,
    review_status: str | None,
    task_id: str | None,
    workspace_dir: str,
    output_dir: str,
    integration_branch: str | None,
    force: bool,
    create_commit: bool,
    allow_source_head_drift: bool,
    use_llm: bool,
    require_llm: bool,
    summary_max_diff_chars: int,
) -> DeliveryIntegrationState:
    initial_state: DeliveryIntegrationState = {
        "codegen_result_path": str(Path(codegen_result_path).resolve()) if codegen_result_path else None,
        "changeset_path": str(Path(changeset_path).resolve()) if changeset_path else None,
        "test_result_path": str(Path(test_result_path).resolve()) if test_result_path else None,
        "review_result_path": str(Path(review_result_path).resolve()) if review_result_path else None,
        "test_status": test_status,
        "review_status": review_status,
        "task_id": task_id,
        "workspace_dir": str(Path(workspace_dir).resolve()),
        "output_dir": str(Path(output_dir).resolve()),
        "integration_branch": integration_branch,
        "force": force,
        "create_commit": create_commit,
        "allow_source_head_drift": allow_source_head_drift,
        "use_llm": use_llm,
        "require_llm": require_llm,
        "summary_max_diff_chars": summary_max_diff_chars,
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
