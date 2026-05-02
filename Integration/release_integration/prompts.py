from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """You are the Integration stage assistant for DeliveraX.
Generate merge-ready delivery documents from a reviewed CodeGen diff and upstream test/review facts.
Return strict JSON only. Do not wrap the response in Markdown fences.

Required JSON keys:
- summary_markdown: content for change_summary.md
- pr_body_markdown: content for github_pr_body.md

Use the required headings exactly so downstream validation can remain deterministic.
Do not claim that this stage executed tests or reviews; only cite the upstream facts that were provided.
"""


def delivery_summary_prompt(*, facts: dict[str, Any], final_diff: str, max_diff_chars: int) -> str:
    diff = final_diff
    truncated = False
    if max_diff_chars > 0 and len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars]
        truncated = True

    payload = {
        "facts": facts,
        "diff_truncated": truncated,
        "final_diff": diff,
        "instructions": [
            "summary_markdown must include these headings exactly: # Delivery Integration Summary, ## Overview, ## Upstream Results, ## Integrated Files, ## Diff Statistics, ## Output Artifacts.",
            "pr_body_markdown must include these headings exactly: ## Change Summary, ## Upstream Validation, ## Changed Files, ## Integration Metadata.",
            "Keep file paths, commands, branches, commits, JSON keys, and technical names exact.",
            "When describing test and review status, state that these were consumed upstream results.",
            "If the diff reveals residual risk or operator notes, include them briefly under the most relevant heading.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
