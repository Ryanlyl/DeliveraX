from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class TestCaseResult(TypedDict, total=False):
    name: str
    file: str
    passed: bool
    message: str


class CodeTestState(TypedDict, total=False):
    # CLI / resolved
    codegen_result_path: str | None
    design_path: str | None
    diff_path: str | None
    repo_path: str | None
    requirement_path: str | None
    task_id: str
    output_dir: str
    workspace_dir: str
    local_only: bool
    force: bool
    max_llm_calls: int
    repair_feedback_path: NotRequired[str | None]

    # After resolve
    source_codegen_repo: str
    design_markdown: str
    diff_text: str
    requirement_text: str
    task_repo_path: str
    task_workspace_dir: str

    # After materialize
    repo_archetype: str  # "nodejs_sp" | "static_html"
    entry_html_path: str
    checkbox_count: int

    # Two-phase LLM
    llm_calls: int
    test_plan_path: str
    test_plan_dict: dict[str, Any]
    plan_generation_raw: str
    generation_raw: str

    # generation / run
    generated_files: list[str]
    needs_e2e: bool
    test_commands: list[str]
    exit_code: int | None
    duration_ms: int
    stdout_tail: str
    stderr_tail: str
    case_results: list[TestCaseResult]
    log_body: str

    # outputs
    result_json_path: str
    report_path: str
    log_path: str

    status: str
    summary: str
    warnings: list[str]
    errors: list[str]
    extra: NotRequired[dict[str, Any]]

    # optional: frontend autostart for nodejs_sp e2e
    frontend_base_url: str
    frontend_dev_server_started: bool
    frontend_dev_server_pid: int
