from __future__ import annotations

import subprocess
from pathlib import Path


def build_git_diff(repo_root: str | Path, change_paths: list[str]) -> str:
    root = Path(repo_root).resolve()
    normalized_paths = [path.replace("\\", "/").lstrip("/") for path in change_paths if path]
    _mark_untracked_files_for_diff(root, normalized_paths)

    args = ["diff", "--no-ext-diff", "--unified=3"]
    if normalized_paths:
        args.extend(["--", *normalized_paths])
    return _git(root, args)


def has_git_diff(repo_root: str | Path, rel_path: str) -> bool:
    root = Path(repo_root).resolve()
    normalized = rel_path.replace("\\", "/").lstrip("/")
    if not normalized:
        return False
    _mark_untracked_files_for_diff(root, [normalized])
    result = subprocess.run(
        _git_command(root, ["diff", "--quiet", "--", normalized]),
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode == 1


def _mark_untracked_files_for_diff(root: Path, paths: list[str]) -> None:
    for rel_path in paths:
        target = root / rel_path
        if not target.exists() or _is_tracked(root, rel_path):
            continue
        _git(root, ["add", "-N", "--", rel_path])


def _is_tracked(root: Path, rel_path: str) -> bool:
    result = subprocess.run(
        _git_command(root, ["ls-files", "--error-unmatch", "--", rel_path]),
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode == 0


def _git(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        _git_command(root, args),
        cwd=str(root),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    return result.stdout or ""


def _git_command(root: Path, args: list[str]) -> list[str]:
    return ["git", "-c", f"safe.directory={root.as_posix()}", *args]
