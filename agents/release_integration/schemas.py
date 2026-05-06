from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class UpstreamResult(TypedDict, total=False):
    status: str
    source: str
    path: NotRequired[str | None]
    detail: NotRequired[str]


class AppliedDiff(TypedDict, total=False):
    check_passed: bool
    applied: bool
    check_output: str
    apply_output: str


class IntegrationState(TypedDict, total=False):
    codegen_result_path: str | None
    changeset_path: str | None
    test_result_path: str | None
    review_result_path: str | None
    test_status: str | None
    review_status: str | None
    task_id: str | None
    workspace_dir: str
    output_dir: str
    integration_branch: str | None
    force: bool
    create_commit: bool
    allow_source_head_drift: bool
    use_llm: bool
    require_llm: bool
    summary_max_diff_chars: int
    changeset: dict[str, Any]
    codegen_result: dict[str, Any]
    source_repo_root: str
    source_commit_sha: str | None
    source_head_sha: str | None
    source_git_status: str
    diff_path: str
    changed_files: list[str]
    test: UpstreamResult
    review: UpstreamResult
    task_workspace_dir: str
    integration_repo_path: str
    integration_branch_name: str
    task_base_commit_sha: str | None
    applied_diff: AppliedDiff
    final_diff: str
    final_diff_stat: str
    integrated_files: list[str]
    head_commit_sha: str | None
    committed: bool
    merge_ready: bool
    final_diff_path: str
    summary_path: str
    pr_body_path: str
    result_json_path: str
    summary_mode: str
    summary_model: str | None
    summary_format_errors: list[str]
    warnings: list[str]
    errors: list[str]

