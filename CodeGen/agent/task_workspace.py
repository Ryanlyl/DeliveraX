from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def default_codegen_workspace_dir() -> Path:
    return Path(__file__).resolve().parents[1] / ".workspace"


def make_task_id(design_path: str | Path, configured: str | None = None) -> str:
    if configured:
        return _safe_name(configured)
    stem = Path(design_path).stem
    if stem.startswith("technical_design_"):
        stem = stem[len("technical_design_") :]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return _safe_name(f"{stem}_{timestamp}")


def extract_expected_commit(metadata: dict[str, str]) -> str | None:
    for key in ("实际 commit SHA", "Actual commit SHA", "commit SHA", "Commit SHA"):
        value = metadata.get(key)
        if value:
            cleaned = value.strip().strip("`")
            if cleaned and cleaned not in {"未记录", "无", "N/A", "unknown"}:
                return cleaned
    return None


def prepare_task_repository(
    *,
    source_repo_root: str | Path,
    design_metadata: dict[str, str],
    task_id: str,
) -> dict[str, str | None]:
    source = Path(source_repo_root).resolve()
    workspace = default_codegen_workspace_dir()
    task_dir = (workspace / "tasks" / _safe_name(task_id)).resolve()
    tasks_root = (workspace / "tasks").resolve()
    repo = task_dir / "repo"
    expected_commit = extract_expected_commit(design_metadata)

    if task_dir.exists():
        _safe_rmtree(task_dir, tasks_root)
    repo.parent.mkdir(parents=True, exist_ok=True)

    source_commit = get_git_head(source) if is_git_repo(source) else None
    if expected_commit and source_commit and not _same_commit(expected_commit, source_commit):
        raise RuntimeError(
            "CodeGen baseline mismatch: technical design expects commit "
            f"{expected_commit}, but cached repository is at {source_commit}."
        )

    if source_commit:
        _git(source, ["worktree", "prune"])
        base = expected_commit or source_commit
        try:
            _git(source, ["worktree", "add", "--detach", str(repo), base])
            method = "git_worktree"
            task_base_commit = get_git_head(repo)
        except Exception:
            method = "copy_synthetic_git_base"
            task_base_commit = _copy_to_synthetic_git_repo(source, repo)
    else:
        method = "copy_synthetic_git_base"
        task_base_commit = _copy_to_synthetic_git_repo(source, repo)

    base_metadata = {
        "task_id": task_id,
        "source_repo_root": str(source),
        "task_repo_root": str(repo),
        "expected_commit_sha": expected_commit,
        "source_commit_sha": source_commit,
        "task_base_commit_sha": task_base_commit,
        "worktree_method": method,
    }
    (task_dir / "base.json").write_text(json.dumps(base_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return base_metadata


def is_git_repo(path: str | Path) -> bool:
    root = Path(path)
    return (root / ".git").exists() and get_git_head(root) is not None


def get_git_head(repo_root: str | Path) -> str | None:
    try:
        return _git(Path(repo_root), ["rev-parse", "HEAD"]).strip()
    except Exception:
        return None


def _copy_to_synthetic_git_repo(source: Path, repo: Path) -> str:
    if repo.exists():
        _safe_rmtree(repo, repo.parent)
    shutil.copytree(
        source,
        repo,
        ignore=shutil.ignore_patterns(".git", ".solution_design_fetch.json", "__pycache__"),
    )
    _git(repo, ["init"])
    _git(repo, ["add", "-A"])
    _git(repo, ["commit", "--allow-empty", "-m", "CodeGen synthetic base"])
    return get_git_head(repo) or ""


def _git(repo_root: Path, args: list[str]) -> str:
    command = [
        "git",
        "-c",
        f"safe.directory={repo_root.as_posix()}",
        "-c",
        "user.name=CodeGen",
        "-c",
        "user.email=codegen@example.invalid",
        "-C",
        str(repo_root),
        *args,
    ]
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    return (result.stdout or "").strip()


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "task"


def _same_commit(expected: str, actual: str) -> bool:
    expected = expected.strip()
    actual = actual.strip()
    return expected.startswith(actual) or actual.startswith(expected)


def _safe_rmtree(target: Path, allowed_root: Path) -> None:
    resolved_target = target.resolve()
    resolved_allowed = allowed_root.resolve()
    if resolved_target == resolved_allowed or resolved_allowed not in resolved_target.parents:
        raise RuntimeError(f"Refusing to remove path outside CodeGen task workspace: {resolved_target}")
    shutil.rmtree(resolved_target)
