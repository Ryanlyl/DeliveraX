from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_repo_paths(root: Path | None = None) -> Path:
    resolved_root = (root or repo_root()).resolve()
    candidates = [
        resolved_root,
        resolved_root / "ReqAnalysis",
        resolved_root / "SolDesign",
        resolved_root / "CodeGen",
        resolved_root / "Integration",
    ]
    for path in candidates:
        text = str(path)
        if path.exists() and text not in sys.path:
            sys.path.insert(0, text)
    return resolved_root
