from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class ChangeFile(TypedDict, total=False):
    path: str
    operation: str
    description: str


class ImplementationContract(TypedDict, total=False):
    objective: str
    repo_root: str
    must_read_files: list[str]
    change_files: list[ChangeFile]
    api_changes: list[Any]
    state_changes: list[str]
    test_commands: list[str]
    acceptance_checks: list[str]
    constraints: list[str]


class FileContext(TypedDict):
    path: str
    exists: bool
    content: str


class GeneratedFileChange(TypedDict, total=False):
    path: str
    operation: str
    content: NotRequired[str | None]
    reason: NotRequired[str]


class SmokeCheck(TypedDict):
    name: str
    passed: bool
    detail: str


class CodeGenState(TypedDict, total=False):
    design_path: str
    repo_path: str | None
    workspace_dir: str | None
    task_id: str | None
    task_workspace_dir: str
    output_dir: str
    local_only: bool
    max_context_files: int
    max_file_chars: int
    design_markdown: str
    design_metadata: dict[str, str]
    implementation_contract: ImplementationContract
    parser_warnings: list[str]
    source_repo_root: str
    source_commit_sha: str | None
    source_git_status: str
    expected_commit_sha: str | None
    task_base_commit_sha: str | None
    worktree_method: str
    repo_root: str
    repo_name: str
    repo_context: dict[str, Any]
    generation_raw: str
    generated_changes: list[GeneratedFileChange]
    applied_changes: list[GeneratedFileChange]
    diff: str
    diff_path: str
    report_path: str
    result_json_path: str
    smoke_checks: list[SmokeCheck]
    warnings: list[str]
    errors: list[str]
