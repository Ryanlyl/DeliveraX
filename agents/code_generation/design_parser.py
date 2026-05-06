from __future__ import annotations

import ast
import re
from typing import Any

from .schemas import ChangeFile, ImplementationContract


def parse_technical_design(markdown: str) -> tuple[ImplementationContract, dict[str, str], list[str]]:
    warnings: list[str] = []
    metadata = _parse_metadata_table(markdown)
    contract_block = _extract_contract_block(markdown)
    contract: ImplementationContract = {}

    if contract_block:
        try:
            contract = _parse_contract_yaml_subset(contract_block)
        except Exception as exc:
            warnings.append(f"implementation_contract parsing failed: {exc}")
    else:
        warnings.append("No implementation_contract fenced block found.")

    if not contract.get("change_files"):
        table_changes = _parse_change_file_table(markdown)
        if table_changes:
            contract["change_files"] = table_changes
            warnings.append("Used 文件变更清单 table as fallback for change_files.")

    if not contract.get("must_read_files"):
        contract["must_read_files"] = [
            item["path"]
            for item in contract.get("change_files", [])
            if item.get("path") and _normalize_operation(item.get("operation", "")) in {"Modify", "Delete"}
        ]

    contract["change_files"] = _normalize_change_files(contract.get("change_files", []))
    contract["must_read_files"] = [_clean_path(path) for path in contract.get("must_read_files", []) if path]
    return contract, metadata, warnings


def _extract_contract_block(markdown: str) -> str | None:
    fenced_pattern = re.compile(
        r"```(?:ya?ml)?\s*\n(?P<body>.*?implementation_contract\s*:\s*.*?)(?:\n```)",
        re.IGNORECASE | re.DOTALL,
    )
    match = fenced_pattern.search(markdown)
    if match:
        return match.group("body").strip()
    inline_pattern = re.compile(r"(implementation_contract\s*:\s*(?:\n[ \t]+.*)+)", re.IGNORECASE)
    match = inline_pattern.search(markdown)
    return match.group(1).strip() if match else None


def _parse_contract_yaml_subset(block: str) -> ImplementationContract:
    lines = [line.rstrip() for line in block.splitlines()]
    start = next((index for index, line in enumerate(lines) if line.strip().startswith("implementation_contract:")), -1)
    if start < 0:
        raise ValueError("missing implementation_contract root")

    root: dict[str, Any] = {}
    current_key: str | None = None
    current_dict: dict[str, Any] | None = None

    for raw in lines[start + 1 :]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent < 2:
            break
        if indent == 2 and not line.startswith("- "):
            key, value = _split_key_value(line)
            if value == "":
                root[key] = []
                current_key = key
                current_dict = None
            else:
                root[key] = _parse_scalar(value)
                current_key = None
                current_dict = None
            continue
        if indent >= 4 and line.startswith("- "):
            if current_key is None:
                continue
            root.setdefault(current_key, [])
            if not isinstance(root[current_key], list):
                root[current_key] = []
            item = line[2:].strip()
            if _looks_like_inline_mapping(item):
                key, value = _split_key_value(item)
                current_dict = {key: _parse_scalar(value)}
                root[current_key].append(current_dict)
            else:
                root[current_key].append(_parse_scalar(item))
                current_dict = None
            continue
        if indent >= 6 and current_dict is not None:
            key, value = _split_key_value(line)
            current_dict[key] = _parse_scalar(value)

    return root  # type: ignore[return-value]


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value == "[]":
        return []
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    try:
        return ast.literal_eval(value)
    except Exception:
        return value.strip("\"'")


def _split_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        return line.strip(), ""
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _looks_like_inline_mapping(item: str) -> bool:
    if not item or ":" not in item:
        return False
    first = item.split(":", 1)[0]
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", first.strip()))


def _parse_metadata_table(markdown: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    section = _section_body(markdown, "0. 元信息")
    if not section:
        return metadata
    for row in _iter_markdown_rows(section):
        if len(row) >= 2 and row[0] not in {"字段", "---"}:
            metadata[row[0]] = row[1]
    return metadata


def _parse_change_file_table(markdown: str) -> list[ChangeFile]:
    section = _section_body(markdown, "5. 文件变更清单")
    if not section:
        return []
    rows = list(_iter_markdown_rows(section))
    if not rows:
        return []
    header = rows[0]
    changes: list[ChangeFile] = []
    for row in rows[1:]:
        if len(row) < 2 or row[0] == "---":
            continue
        item: ChangeFile = {
            "path": _clean_path(row[0]),
            "operation": _normalize_operation(row[1]),
        }
        if len(row) >= 3:
            item["description"] = row[2]
        if item["path"] and item["path"] not in {"文件路径", ""} and header:
            changes.append(item)
    return changes


def _section_body(markdown: str, title: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(title)}\s*$", re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return ""
    next_match = re.search(r"^##\s+", markdown[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(markdown)
    return markdown[match.end() : end]


def _iter_markdown_rows(text: str):
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [_clean_cell(cell) for cell in stripped.strip("|").split("|")]
        if all(set(cell) <= {"-"} for cell in cells if cell):
            yield ["---"]
        else:
            yield cells


def _clean_cell(value: str) -> str:
    return re.sub(r"<br\s*/?>", "\n", value.strip(), flags=re.IGNORECASE)


def _normalize_change_files(change_files: list) -> list[ChangeFile]:
    normalized: list[ChangeFile] = []
    seen: set[str] = set()
    for item in change_files:
        if isinstance(item, str):
            path = _clean_path(item)
            operation = "Modify"
            description = ""
        else:
            # tolerate partially-typed payloads
            item_dict = item if isinstance(item, dict) else {}
            path = _clean_path(str(item_dict.get("path", "")))
            operation = str(item_dict.get("operation", ""))
            description = str(item_dict.get("description", "")).strip()
        if not path or path in seen:
            continue
        seen.add(path)
        normalized.append(
            {
                "path": path,
                "operation": _normalize_operation(operation),
                "description": description,
            }
        )
    return normalized


def _normalize_operation(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"add", "added", "new", "新增"}:
        return "Add"
    if lowered in {"delete", "remove", "removed", "删除"}:
        return "Delete"
    if lowered in {"modify", "modified", "update", "change", "修改"}:
        return "Modify"
    return value.strip() or "Modify"


def _clean_path(path: str) -> str:
    cleaned = path.strip().strip("`").strip("\"'").replace("\\", "/")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned.lstrip("/")

