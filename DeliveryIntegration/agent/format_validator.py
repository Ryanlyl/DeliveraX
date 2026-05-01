from __future__ import annotations


SUMMARY_REQUIRED_HEADINGS = [
    "# 交付集成摘要",
    "## 概览",
    "## 上游结果",
    "## 集成文件",
    "## Diff 统计",
    "## 输出产物",
]

PR_BODY_REQUIRED_HEADINGS = [
    "## 变更摘要",
    "## 上游验证",
    "## 变更文件",
    "## 集成元数据",
]

BLOCKED_ENGLISH_HEADINGS = [
    "## Summary",
    "## Overview",
    "## Upstream",
    "## Upstream Validation",
    "## Changed Files",
    "## Integration Metadata",
    "## Outputs",
    "## Warnings",
    "## Merge Notes",
]


def validate_delivery_documents(summary_markdown: str, pr_body_markdown: str) -> list[str]:
    errors: list[str] = []
    errors.extend(_missing_headings("change_summary.md", summary_markdown, SUMMARY_REQUIRED_HEADINGS))
    errors.extend(_missing_headings("github_pr_body.md", pr_body_markdown, PR_BODY_REQUIRED_HEADINGS))
    errors.extend(_blocked_english_headings("change_summary.md", summary_markdown))
    errors.extend(_blocked_english_headings("github_pr_body.md", pr_body_markdown))
    return errors


def _missing_headings(document_name: str, markdown: str, required: list[str]) -> list[str]:
    return [f"{document_name} 缺少中文章节：{heading}" for heading in required if heading not in markdown]


def _blocked_english_headings(document_name: str, markdown: str) -> list[str]:
    lines = {line.strip() for line in markdown.splitlines()}
    return [f"{document_name} 不应使用英文章节标题：{heading}" for heading in BLOCKED_ENGLISH_HEADINGS if heading in lines]

