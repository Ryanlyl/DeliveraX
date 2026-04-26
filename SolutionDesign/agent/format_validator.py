from __future__ import annotations

import re
from typing import Any

from .schemas import RepoContext


REQUIRED_HEADINGS = [
    "# 技术方案设计",
    "## 0. 元信息",
    "## 1. 需求理解",
    "## 2. 现有架构分析",
    "## 3. 影响范围",
    "## 4. 推荐技术方案",
    "## 5. 文件变更清单",
    "## 6. API 设计",
    "## 7. 数据结构与状态设计",
    "## 8. 实施步骤",
    "## 9. 测试计划",
    "## 10. 风险与待确认问题",
    "## 11. 给下一个实现 Agent 的执行指令",
    "## 12. 一致性自检",
]

ADD_OPERATIONS = {"add", "new", "create", "新增", "新建", "创建"}
EXISTING_OPERATIONS = {
    "modify",
    "update",
    "change",
    "delete",
    "remove",
    "existing",
    "修改",
    "更新",
    "变更",
    "删除",
    "移除",
}


def validate_technical_design(markdown: str, repo_context: RepoContext) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    missing_headings = [heading for heading in REQUIRED_HEADINGS if not _has_heading(markdown, heading)]
    if missing_headings:
        errors.append("Missing required headings: " + ", ".join(missing_headings))

    file_change_section = _extract_section(markdown, "## 5. 文件变更清单")
    if not file_change_section.strip():
        errors.append("Missing content under `## 5. 文件变更清单`.")
    elif not _has_markdown_table(file_change_section):
        errors.append("`## 5. 文件变更清单` must contain a Markdown table.")

    api_section = _extract_section(markdown, "## 6. API 设计")
    if not api_section.strip():
        errors.append("Missing content under `## 6. API 设计`.")

    if not _has_implementation_contract(markdown):
        errors.append("Missing fenced YAML block containing `implementation_contract:`.")

    path_errors, path_warnings = _validate_file_change_paths(file_change_section, repo_context)
    errors.extend(path_errors)
    warnings.extend(path_warnings)

    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "missing_headings": missing_headings,
    }


def format_validation_report(result: dict[str, Any]) -> str:
    lines = [
        f"- Passed: `{result.get('passed', False)}`",
        "- Errors:",
    ]
    errors = result.get("errors") or []
    if errors:
        lines.extend(f"  - {error}" for error in errors)
    else:
        lines.append("  - None")

    lines.append("- Warnings:")
    warnings = result.get("warnings") or []
    if warnings:
        lines.extend(f"  - {warning}" for warning in warnings)
    else:
        lines.append("  - None")
    return "\n".join(lines)


def _has_heading(markdown: str, required_heading: str) -> bool:
    pattern = re.compile(rf"^{re.escape(required_heading)}(?:\s|[:：]|$)", re.MULTILINE)
    return bool(pattern.search(markdown))


def _extract_section(markdown: str, heading: str) -> str:
    start_pattern = re.compile(rf"^{re.escape(heading)}(?:\s|[:：]|$).*$", re.MULTILINE)
    start_match = start_pattern.search(markdown)
    if not start_match:
        return ""

    heading_level = len(heading) - len(heading.lstrip("#"))
    next_heading_pattern = re.compile(rf"^#{{1,{heading_level}}}\s+", re.MULTILINE)
    next_match = next_heading_pattern.search(markdown, start_match.end())
    end = next_match.start() if next_match else len(markdown)
    return markdown[start_match.end() : end].strip()


def _has_markdown_table(section: str) -> bool:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    for index, line in enumerate(lines[:-1]):
        if "|" not in line:
            continue
        separator = lines[index + 1]
        if re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$", separator):
            return True
    return False


def _has_implementation_contract(markdown: str) -> bool:
    pattern = re.compile(r"```\s*ya?ml\s+[\s\S]*?implementation_contract\s*:[\s\S]*?```", re.IGNORECASE)
    return bool(pattern.search(markdown))


def _validate_file_change_paths(section: str, repo_context: RepoContext) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    table = _parse_first_table(section)
    if not table:
        return errors, warnings

    headers, rows = table
    path_index = _find_column(headers, ("文件路径", "path", "file"))
    op_index = _find_column(headers, ("操作", "action", "operation"))
    if path_index is None:
        errors.append("File change table must include a file path column.")
        return errors, warnings

    existing_paths = _existing_repo_paths(repo_context)
    for row in rows:
        if path_index >= len(row):
            continue
        raw_path = _clean_cell(row[path_index])
        if _should_skip_path(raw_path):
            continue

        operation = _clean_cell(row[op_index]) if op_index is not None and op_index < len(row) else ""
        normalized_path = _normalize_path(raw_path, repo_context.get("repo_root", ""))
        exists = normalized_path in existing_paths
        op_lower = operation.lower()
        is_add = any(token in op_lower or token in operation for token in ADD_OPERATIONS)
        is_existing_operation = any(token in op_lower or token in operation for token in EXISTING_OPERATIONS)

        if is_existing_operation and not is_add and not exists:
            errors.append(
                f"File change table claims existing path `{raw_path}` with operation `{operation}`, "
                "but repo scanner did not find it."
            )
        elif is_add and exists:
            warnings.append(f"File change table marks `{raw_path}` as Add/New, but the path already exists.")
        elif not exists and not is_add and operation:
            warnings.append(
                f"File change table path `{raw_path}` was not found. Mark it as Add/New or move it to pending confirmation."
            )
    return errors, warnings


def _parse_first_table(section: str) -> tuple[list[str], list[list[str]]] | None:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    for index, line in enumerate(lines[:-1]):
        if "|" not in line:
            continue
        separator = lines[index + 1]
        if not re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$", separator):
            continue
        headers = _split_table_row(line)
        rows: list[list[str]] = []
        for row_line in lines[index + 2 :]:
            if "|" not in row_line:
                break
            rows.append(_split_table_row(row_line))
        return headers, rows
    return None


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _find_column(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    for index, header in enumerate(headers):
        lowered = header.lower()
        if any(candidate.lower() in lowered for candidate in candidates):
            return index
    return None


def _clean_cell(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"`+", "", value)
    return value.strip()


def _should_skip_path(path: str) -> bool:
    if not path:
        return True
    placeholders = ("tbd", "待确认", "待补充", "待 llm", "n/a", "none", "-")
    lowered = path.lower()
    return any(token in lowered for token in placeholders)


def _existing_repo_paths(repo_context: RepoContext) -> set[str]:
    paths = set(repo_context.get("candidate_files", []))
    for item in repo_context.get("key_files", []):
        if item.get("path"):
            paths.add(item["path"])
    return {_normalize_path(path, repo_context.get("repo_root", "")) for path in paths}


def _normalize_path(path: str, repo_root: str) -> str:
    normalized = path.strip().replace("\\", "/")
    normalized = re.sub(r"^\./", "", normalized)
    root_normalized = repo_root.replace("\\", "/").rstrip("/")
    if root_normalized and normalized.startswith(root_normalized + "/"):
        normalized = normalized[len(root_normalized) + 1 :]
    return normalized.strip("/")
