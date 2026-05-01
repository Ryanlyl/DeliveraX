from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """你是交付集成助手。

请根据已经完成测试和评审的代码变更，生成可合并交付物的中文文档。
不要声称本阶段执行了测试或代码评审；只能把传入的上游状态作为事实引用。
必须只返回严格 JSON，不要输出 Markdown 代码块。JSON key 固定为：
- summary_markdown: change_summary.md 的 Markdown 内容
- pr_body_markdown: github_pr_body.md 的 Markdown 内容
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
            "必须使用中文章节标题和中文说明。文件名、命令、commit、branch、JSON key、技术名词可以保留英文。",
            "summary_markdown 必须包含这些章节：# 交付集成摘要、## 概览、## 上游结果、## 集成文件、## Diff 统计、## 输出产物。",
            "pr_body_markdown 必须包含这些章节：## 变更摘要、## 上游验证、## 变更文件、## 集成元数据。",
            "不要使用英文章节标题，例如 Summary、Overview、Upstream Validation、Changed Files、Integration Metadata。",
            "说明上游测试/评审状态时，必须表达为本阶段读取并消费的结果，而不是本阶段重新执行。",
            "内容面向即将合并分支的维护者，保持简洁、可操作。",
            "如果能从 diff 看出风险或注意事项，可以在中文说明中简短列出。",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
