from __future__ import annotations

import json
import re
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


def resolve_path_maybe_relative(path_str: str | None, base_dir: Path) -> str | None:
    if not path_str:
        return None
    candidate = Path(path_str)
    if candidate.is_absolute():
        return str(candidate.resolve())
    return str((base_dir / candidate).resolve())


def read_text(path: str | Path) -> str:
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return source.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return source.read_text(encoding="utf-8", errors="replace")


_HUNK_HEADER_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")


def apply_unified_diff_to_repo(*, diff_path: str | Path, repo_root: str | Path) -> list[str]:
    """Apply a git-style unified diff onto a repo working copy.

    Intended for test workspaces (no VCS required). Supports file modifications and additions.
    Returns a list of changed relative paths.
    """
    repo = Path(repo_root)
    text = read_text(diff_path)
    lines = text.splitlines()

    changed: list[str] = []
    i = 0
    current_rel: str | None = None
    hunks: list[list[str]] = []

    def flush() -> None:
        nonlocal current_rel, hunks
        if not current_rel:
            hunks = []
            return
        target = (repo / current_rel).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        # Read original file if it exists; if not, treat as empty (new file)
        original_lines: list[str]
        if target.is_file():
            original_lines = read_text(target).splitlines()
        else:
            original_lines = []

        out_lines = list(original_lines)
        offset = 0

        for hunk in hunks:
            if not hunk:
                continue
            m = _HUNK_HEADER_RE.match(hunk[0])
            if not m:
                raise RuntimeError(f"Invalid hunk header for {current_rel}: {hunk[0]}")
            old_start = int(m.group(1))
            # old_len = int(m.group(2) or "1")
            # new_start = int(m.group(3))

            idx = max(0, old_start - 1 + offset)
            new_chunk: list[str] = []
            consume = 0

            for ln in hunk[1:]:
                if not ln:
                    # blank lines in diff are represented as "" after splitlines()
                    ln = ""
                tag = ln[:1]
                payload = ln[1:] if len(ln) > 0 else ""
                if tag == " ":
                    # context
                    if idx + consume >= len(out_lines) or out_lines[idx + consume] != payload:
                        got = out_lines[idx + consume] if idx + consume < len(out_lines) else "<eof>"
                        raise RuntimeError(
                            f"Patch context mismatch in {current_rel} at line {idx + consume + 1}: "
                            f"expected {payload!r}, got {got!r}"
                        )
                    new_chunk.append(payload)
                    consume += 1
                elif tag == "-":
                    # delete
                    if idx + consume >= len(out_lines) or out_lines[idx + consume] != payload:
                        got = out_lines[idx + consume] if idx + consume < len(out_lines) else "<eof>"
                        raise RuntimeError(
                            f"Patch delete mismatch in {current_rel} at line {idx + consume + 1}: "
                            f"expected {payload!r}, got {got!r}"
                        )
                    consume += 1
                elif tag == "+":
                    # add
                    new_chunk.append(payload)
                else:
                    # Ignore meta lines (e.g. \ No newline at end of file)
                    continue

            out_lines[idx : idx + consume] = new_chunk
            offset += len(new_chunk) - consume

        target.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
        changed.append(current_rel)
        hunks = []

    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git "):
            flush()
            current_rel = None
            hunks = []
            i += 1
            continue
        if line.startswith("+++ "):
            # Prefer b/<path> from +++ line
            path = line[4:].strip()
            if path.startswith("b/"):
                current_rel = path[2:]
            elif path == "/dev/null":
                current_rel = None
            else:
                current_rel = path
            i += 1
            continue
        if line.startswith("@@ "):
            # capture hunk lines until next hunk or next file
            hunk: list[str] = [line]
            i += 1
            while i < len(lines):
                nl = lines[i]
                if nl.startswith("diff --git ") or nl.startswith("@@ "):
                    break
                hunk.append(nl)
                i += 1
            hunks.append(hunk)
            continue
        i += 1

    flush()
    return changed
