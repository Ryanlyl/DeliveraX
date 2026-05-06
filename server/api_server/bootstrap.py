from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_repo_paths(root: Path | None = None) -> Path:
    resolved_root = (root or repo_root()).resolve()
    candidates = [resolved_root]
    agents_dir = resolved_root / "agents"
    if agents_dir.is_dir():
        for entry in sorted(agents_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                candidates.append(entry)
    for path in candidates:
        text = str(path)
        if path.exists() and text not in sys.path:
            sys.path.insert(0, text)
    return resolved_root
