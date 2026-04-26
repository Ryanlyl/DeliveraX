from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class RepoFetchMetadata(TypedDict, total=False):
    repo_root: str
    repo_name: str
    repo_url: str | None
    requested_ref: str | None
    resolved_ref: str | None
    commit_sha: str | None
    fetch_method: str
    cache_key: str | None
    cached: bool
    fetched_at: str
    package_json_path: str | None
    frontend_repo_valid: bool
    validation_warnings: list[str]
    fallback_reason: NotRequired[str]


class RepoContext(TypedDict, total=False):
    repo_root: str
    repo_name: str
    repo_source: str
    repo_url: str | None
    requested_ref: str | None
    resolved_ref: str | None
    commit_sha: str | None
    fetch_method: str | None
    cache_key: str | None
    cached: bool
    package_json_path: str | None
    frontend_repo_valid: bool
    validation_warnings: list[str]
    repo_ref: NotRequired[str | None]
    tree: str
    detected_stack: dict[str, Any]
    key_files: list[dict[str, str]]
    candidate_files: list[str]
    omitted_files: list[str]


class SolutionDesignState(TypedDict, total=False):
    requirement_path: str
    repo_url: str | None
    repo_path: str | None
    repo_ref: str | None
    output_dir: str
    template_path: str
    workspace_dir: str | None
    task_id: str | None
    local_only: bool
    max_context_files: int
    requirement_markdown: str
    requirement_sections: dict[str, str]
    repo_root: str
    repo_fetch: RepoFetchMetadata
    repo_context: RepoContext
    architecture_summary: str
    impact_analysis: str
    technical_design: str
    format_validation: dict[str, Any]
    format_repaired: bool
    review_notes: str
    output_path: str
    errors: list[str]
