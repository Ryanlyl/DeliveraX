from __future__ import annotations


SUMMARY_REQUIRED_HEADINGS = [
    "# Delivery Integration Summary",
    "## Overview",
    "## Upstream Results",
    "## Integrated Files",
    "## Diff Statistics",
    "## Output Artifacts",
]

PR_BODY_REQUIRED_HEADINGS = [
    "## Change Summary",
    "## Upstream Validation",
    "## Changed Files",
    "## Integration Metadata",
]


def validate_delivery_documents(summary_markdown: str, pr_body_markdown: str) -> list[str]:
    errors: list[str] = []
    errors.extend(_missing_headings("change_summary.md", summary_markdown, SUMMARY_REQUIRED_HEADINGS))
    errors.extend(_missing_headings("github_pr_body.md", pr_body_markdown, PR_BODY_REQUIRED_HEADINGS))
    return errors


def _missing_headings(document_name: str, markdown: str, required: list[str]) -> list[str]:
    return [f"{document_name} is missing required heading: {heading}" for heading in required if heading not in markdown]
