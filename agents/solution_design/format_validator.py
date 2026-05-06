from __future__ import annotations

import re
from typing import Any

from .schemas import RepoContext


REQUIRED_HEADING_GROUPS = [
    ("# Technical Solution Design",),
    ("## 0. Metadata",),
    ("## 1. Requirement Understanding",),
    ("## 2. Current Architecture",),
    ("## 3. Impact Scope",),
    ("## 4. Recommended Technical Approach",),
    ("## 5. File Change Plan", "## 5. File Change List"),
    ("## 6. API Design",),
    ("## 7. Data And State Design", "## 7. Data and State Design"),
    ("## 8. Implementation Steps",),
    ("## 9. Test Plan",),
    ("## 10. Risks And Open Questions",),
    ("## 11. Implementation Contract",),
    ("## 12. Self Check",),
]

FILE_CHANGE_HEADINGS = ("## 5. File Change Plan", "## 5. File Change List")
API_HEADINGS = ("## 6. API Design",)

ADD_OPERATIONS = {"add", "new", "create"}
EXISTING_OPERATIONS = {"modify", "update", "change", "delete", "remove", "existing"}


def validate_technical_design(markdown: str, repo_context: RepoContext) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    missing_headings = [
        aliases[0] for aliases in REQUIRED_HEADING_GROUPS if not any(_has_heading(markdown, heading) for heading in aliases)
    ]
    if missing_headings:
        errors.append("Missing required headings: " + ", ".join(missing_headings))

    file_change_section = _extract_first_available_section(markdown, FILE_CHANGE_HEADINGS)
    if not file_change_section.strip():
        errors.append("Missing content under `## 5. File Change Plan`.")
    elif not _has_markdown_table(file_change_section):
        errors.append("`## 5. File Change Plan` must contain a Markdown table.")

    api_section = _extract_first_available_section(markdown, API_HEADINGS)
    if not api_section.strip():
        errors.append("Missing content under `## 6. API Design`.")

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


def _extract_first_available_section(markdown: str, headings: tuple[str, ...]) -> str:
    for heading in headings:
        section = _extract_section(markdown, heading)
        if section:
            return section
    return ""


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
    path_index = _find_column(headers, ("file path", "path", "file"))
    op_index = _find_column(headers, ("action", "operation"))
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
        is_add = any(token in op_lower for token in ADD_OPERATIONS)
        is_existing_operation = any(token in op_lower for token in EXISTING_OPERATIONS)

        if is_existing_operation and not is_add and not exists:
            errors.append(
                f"File change table claims existing path `{raw_path}` with operation `{operation}`, "
                "but repo scanner did not find it."
            )
        elif is_add and exists:
            warnings.append(f"File change table marks `{raw_path}` as Add/New, but the path already exists.")
        elif not exists and not is_add and operation:
            warnings.append(
                f"File change table path `{raw_path}` was not found. Mark it as Add/New or move it to open questions."
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
    placeholders = ("tbd", "pending", "n/a", "none", "-")
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
