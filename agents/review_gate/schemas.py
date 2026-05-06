from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class IssueItem(TypedDict, total=False):
    id: str
    severity: str
    category: str
    file: str
    line: int | None
    evidence: str
    fix_suggestion: str


class TestGap(TypedDict, total=False):
    summary: str
    suggested_test: str


class ReviewResultPayload(TypedDict, total=False):
    schema_version: str
    task_id: str
    prompt_schema_version: str
    status: str  # DeliveryIntegration-compatible
    merge_recommendation: str
    summary: str
    risk_note: str
    local_only: bool
    llm_calls: int
    max_llm_calls: int
    design_path: str
    diff_path: str
    test_result_path: str
    requirement_path: NotRequired[str]
    codegen_result_path: NotRequired[str]
    policy_pack_path: NotRequired[str]
    issues: list[dict[str, Any]]
    test_gaps: list[dict[str, Any]]
    warnings: list[str]
    code_review_report_path: str
    feedback_review_path: NotRequired[str]
    result_json_path: str


def empty_result(*, task_id: str, local_only: bool) -> ReviewResultPayload:
    return ReviewResultPayload(
        schema_version="1.0",
        task_id=task_id,
        prompt_schema_version="codereview-v1",
        status="changes_requested",
        merge_recommendation="changes_requested",
        summary="Placeholder (local-only or error). Human review required.",
        risk_note="",
        local_only=local_only,
        llm_calls=0,
        max_llm_calls=0,
        design_path="",
        diff_path="",
        test_result_path="",
        issues=[],
        test_gaps=[],
        warnings=[],
        result_json_path="",
    )
