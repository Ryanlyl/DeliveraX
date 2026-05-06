from __future__ import annotations

import shutil
from pathlib import Path


def safe_repo_path(repo_root: Path, relative: str) -> Path:
    root = repo_root.resolve()
    target = (root / relative).resolve()
    if root not in target.parents and target != root:
        raise ValueError(f"Path escapes repository root: {relative}")
    return target


def copy_task_repository(*, source_root: Path, dest_root: Path, force: bool) -> None:
    if not source_root.is_dir():
        raise RuntimeError(f"Source repository does not exist: {source_root}")
    if dest_root.exists():
        if not force:
            raise RuntimeError(
                f"Task workspace already exists: {dest_root}. Pass --force to replace."
            )
        shutil.rmtree(dest_root)
    dest_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source_root,
        dest_root,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git",
            "node_modules",
            "dist",
            "build",
            ".next",
            "coverage",
        ),
    )
