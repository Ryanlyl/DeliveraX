from __future__ import annotations

import json
from typing import Any

from .schemas import ImplementationContract


SYSTEM_PROMPT = """You are CodeGen Agent, a careful senior frontend engineer.
Your job is to turn an approved technical design into concrete repository file changes.
Follow the implementation_contract exactly, modify only the requested files, preserve the project's existing style, and return machine-parseable JSON only."""


def code_generation_prompt(
    *,
    design_markdown: str,
    contract: ImplementationContract,
    repo_context: dict[str, Any],
) -> str:
    selected_files = repo_context.get("selected_files", [])
    file_blocks = []
    for item in selected_files:
        exists = "exists" if item.get("exists") else "missing"
        file_blocks.append(
            f"### File: {item.get('path')} ({exists})\n"
            "```text\n"
            f"{item.get('content', '')}\n"
            "```"
        )

    allowed_files = [
        {
            "path": item.get("path"),
            "operation": item.get("operation"),
            "description": item.get("description", ""),
        }
        for item in contract.get("change_files", [])
    ]

    return "\n\n".join(
        [
            "Generate the final file contents needed to implement this technical design.",
            "Return strict JSON only. Do not wrap the JSON in Markdown fences.",
            "JSON schema:",
            """{
  "files": [
    {
      "path": "relative/path/from/repo/root",
      "operation": "Add | Modify | Delete",
      "content_b64": "BASE64 of complete final file content for Add/Modify (UTF-8). null for Delete",
      "content": "OPTIONAL (discouraged): raw content string. Prefer content_b64 to avoid JSON escaping issues.",
      "reason": "short implementation note"
    }
  ],
  "notes": ["optional warning or follow-up"]
}""",
            "Rules:",
            "- Only include files listed in allowed_change_files.",
            "- For Modify and Add, prefer content_b64 (UTF-8). It must decode to the complete final file content, not a patch.",
            "- If you provide content (raw string), it must be valid JSON string with proper escaping; content_b64 is safer.",
            "- For Delete, set content_b64 to null (and content to null if present).",
            "- Do not invent external dependencies unless the design explicitly requires them.",
            "- Keep code changes scoped to the implementation_contract.",
            "implementation_contract:",
            json.dumps(contract, ensure_ascii=False, indent=2),
            "allowed_change_files:",
            json.dumps(allowed_files, ensure_ascii=False, indent=2),
            "repository_context:",
            json.dumps(
                {
                    "repo_name": repo_context.get("repo_name"),
                    "tree": repo_context.get("tree"),
                    "detected_stack": repo_context.get("detected_stack"),
                    "git_status": repo_context.get("git_status"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            "selected_file_contents:",
            "\n\n".join(file_blocks),
            "technical_design_markdown:",
            "```markdown\n" + design_markdown[:60000] + "\n```",
        ]
    )

