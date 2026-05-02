from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return json.loads(source.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    return json.loads(source.read_text(encoding="utf-8", errors="replace"))


def write_text(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def resolve_relative_path(path: str | None, base_dir: str | Path) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate.resolve())
    return str((Path(base_dir).resolve() / candidate).resolve())


def make_output_paths(output_dir: str | Path, task_id: str) -> tuple[Path, Path, Path, Path]:
    output = Path(output_dir).resolve() / task_id
    output.mkdir(parents=True, exist_ok=True)
    return (
        output / "final_changes.diff",
        output / "change_summary.md",
        output / "github_pr_body.md",
        output / "delivery_integration_result.json",
    )


