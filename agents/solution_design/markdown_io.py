from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_markdown(path: str | Path) -> str:
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return source.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return source.read_text(encoding="utf-8", errors="replace")


def parse_markdown_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"__root__": []}
    current = "__root__"
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

    for line in markdown.splitlines():
        match = heading_pattern.match(line)
        if match:
            current = match.group(2).strip()
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)

    return {title: "\n".join(lines).strip() for title, lines in sections.items() if "\n".join(lines).strip()}


def read_template(path: str | Path) -> str:
    return read_markdown(path)


def make_output_path(output_dir: str | Path, requirement_path: str | Path) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    requirement_stem = Path(requirement_path).stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", requirement_stem).strip("_") or "requirement"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return output / f"technical_design_{safe_stem}_{timestamp}.md"


def write_markdown(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


