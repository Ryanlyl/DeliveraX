from __future__ import annotations

from pathlib import Path


def read_markdown(path: str | Path) -> str:
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return source.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return source.read_text(encoding="utf-8", errors="replace")


def write_text(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def make_output_paths(output_dir: str | Path, task_id: str) -> tuple[Path, Path, Path]:
    output = Path(output_dir) / task_id
    output.mkdir(parents=True, exist_ok=True)
    return output / "code_changes.diff", output / "codegen_report.md", output / "codegen_result.json"
