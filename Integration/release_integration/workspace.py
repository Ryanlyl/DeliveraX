from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "task"


def branch_safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._/-]+", "-", value).strip("/-")
    return cleaned or "delivery/task"


def git_status(repo_root: str | Path) -> str:
    root = Path(repo_root).resolve()
    if not (root / ".git").exists():
        return "not a git repository"
    try:
        return git(root, ["status", "--short"]).strip()
    except Exception as exc:
        return f"git status failed: {exc}"


def git_head(repo_root: str | Path) -> str | None:
    root = Path(repo_root).resolve()
    try:
        return git(root, ["rev-parse", "HEAD"]).strip()
    except Exception:
        return None


def is_git_repo(repo_root: str | Path) -> bool:
    root = Path(repo_root).resolve()
    return (root / ".git").exists() and git_head(root) is not None


def prepare_integration_repository(
    *,
    source_repo_root: str | Path,
    source_commit_sha: str | None,
    workspace_dir: str | Path,
    task_id: str,
    integration_branch: str | None,
    force: bool,
    allow_source_head_drift: bool,
) -> dict[str, str | None]:
    source = Path(source_repo_root).resolve()
    if not source.exists():
        raise RuntimeError(f"Source repository root does not exist: {source}")

    workspace = Path(workspace_dir).resolve()
    tasks_root = (workspace / "tasks").resolve()
    task_dir = (tasks_root / safe_name(task_id)).resolve()
    repo = task_dir / "repo"
    if task_dir.exists():
        if not force:
            raise RuntimeError(
                f"Integration task workspace already exists: {task_dir}. "
                "Use --force to replace it."
            )
        _remove_existing_task_workspace(source, task_dir, tasks_root, repo)

    repo.parent.mkdir(parents=True, exist_ok=True)
    source_head = git_head(source) if is_git_repo(source) else None
    base_commit = source_commit_sha or source_head
    if source_commit_sha and source_head and not _same_commit(source_commit_sha, source_head):
        if not allow_source_head_drift:
            raise RuntimeError(
                "Source workspace HEAD does not match CodeGen source_commit_sha. "
                f"source_head={source_head}; codegen_source_commit={source_commit_sha}. "
                "Pass --allow-source-head-drift only if this is intentional."
            )

    branch_name = branch_safe_name(integration_branch or f"delivery/{task_id}")
    if is_git_repo(source) and base_commit:
        git(source, ["worktree", "prune"])
        git(source, ["worktree", "add", "--detach", str(repo), base_commit])
        branch_name = _unique_branch_name(repo, branch_name)
        git(repo, ["switch", "-c", branch_name])
        task_base_commit = git_head(repo)
        method = "git_worktree"
    else:
        _copy_to_synthetic_git_repo(source, repo)
        branch_name = _unique_branch_name(repo, branch_name)
        git(repo, ["switch", "-c", branch_name])
        task_base_commit = git_head(repo)
        method = "copy_synthetic_git_base"

    return {
        "task_workspace_dir": str(task_dir),
        "integration_repo_path": str(repo),
        "integration_branch_name": branch_name,
        "task_base_commit_sha": task_base_commit,
        "source_head_sha": source_head,
        "worktree_method": method,
    }


def apply_diff(*, repo_root: str | Path, diff_path: str | Path) -> dict[str, str | bool]:
    root = Path(repo_root).resolve()
    diff = Path(diff_path).resolve()
    if not diff.exists():
        raise RuntimeError(f"Diff path does not exist: {diff}")
    check = git_result(root, ["apply", "--check", "--whitespace=fix", str(diff)])
    if check.returncode != 0:
        return {
            "check_passed": False,
            "applied": False,
            "check_output": _combined_output(check),
            "apply_output": "",
        }
    applied = git_result(root, ["apply", "--whitespace=fix", str(diff)])
    if applied.returncode != 0:
        three_way = git_result(root, ["apply", "--3way", "--whitespace=fix", str(diff)])
        return {
            "check_passed": True,
            "applied": three_way.returncode == 0,
            "check_output": _combined_output(check),
            "apply_output": _combined_output(applied) + "\n" + _combined_output(three_way),
        }
    return {
        "check_passed": True,
        "applied": applied.returncode == 0,
        "check_output": _combined_output(check),
        "apply_output": _combined_output(applied),
    }


def commit_integrated_changes(repo_root: str | Path, message: str) -> str | None:
    root = Path(repo_root).resolve()
    git(root, ["add", "-A"])
    diff = git_result(root, ["diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        return git_head(root)
    git(root, ["commit", "-m", message])
    return git_head(root)


def build_final_diff(repo_root: str | Path, base_commit: str | None, *, committed: bool) -> str:
    root = Path(repo_root).resolve()
    if not base_commit:
        return git(root, ["diff", "--no-ext-diff", "--unified=3"])
    if committed:
        return git(root, ["diff", "--no-ext-diff", "--unified=3", f"{base_commit}..HEAD"])
    return git(root, ["diff", "--no-ext-diff", "--unified=3", base_commit])


def build_diff_stat(repo_root: str | Path, base_commit: str | None, *, committed: bool) -> str:
    root = Path(repo_root).resolve()
    if not base_commit:
        return git(root, ["diff", "--stat"])
    if committed:
        return git(root, ["diff", "--stat", f"{base_commit}..HEAD"])
    return git(root, ["diff", "--stat", base_commit])


def list_changed_files(repo_root: str | Path, base_commit: str | None, *, committed: bool) -> list[str]:
    root = Path(repo_root).resolve()
    if not base_commit:
        output = git(root, ["diff", "--name-only"])
    elif committed:
        output = git(root, ["diff", "--name-only", f"{base_commit}..HEAD"])
    else:
        output = git(root, ["diff", "--name-only", base_commit])
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def assert_safe_changed_files(repo_root: str | Path, files: list[str]) -> None:
    root = Path(repo_root).resolve()
    for rel_path in files:
        cleaned = rel_path.replace("\\", "/").lstrip("/")
        if not cleaned:
            raise RuntimeError("Empty changed file path is not allowed.")
        candidate = (root / cleaned).resolve()
        if candidate != root and root not in candidate.parents:
            raise RuntimeError(f"Changed file escapes repository root: {rel_path}")


def git(repo_root: str | Path, args: list[str], *, timeout: int = 180) -> str:
    result = git_result(repo_root, args, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(_combined_output(result) or f"git {' '.join(args)} failed")
    return result.stdout or ""


def git_result(repo_root: str | Path, args: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    root = Path(repo_root).resolve()
    command = [
        "git",
        "-c",
        f"safe.directory={root.as_posix()}",
        "-c",
        "user.name=Integration",
        "-c",
        "user.email=delivery-integration@example.invalid",
        "-C",
        str(root),
        *args,
    ]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _copy_to_synthetic_git_repo(source: Path, repo: Path) -> None:
    if repo.exists():
        _safe_rmtree(repo, repo.parent)
    shutil.copytree(
        source,
        repo,
        ignore=shutil.ignore_patterns(".git", ".solution_design_fetch.json", "__pycache__"),
    )
    git(repo, ["init"])
    git(repo, ["add", "-A"])
    git(repo, ["commit", "--allow-empty", "-m", "Integration synthetic base"])


def _unique_branch_name(repo_root: Path, branch_name: str) -> str:
    if not _branch_exists(repo_root, branch_name):
        return branch_name
    suffix = datetime.now().strftime("%Y%m%d%H%M%S")
    candidate = f"{branch_name}-{suffix}"
    if not _branch_exists(repo_root, candidate):
        return candidate
    return f"{candidate}-{safe_name(str(repo_root.parent.name))}"


def _branch_exists(repo_root: Path, branch_name: str) -> bool:
    result = git_result(repo_root, ["rev-parse", "--verify", f"refs/heads/{branch_name}"])
    return result.returncode == 0


def _remove_existing_task_workspace(source: Path, task_dir: Path, tasks_root: Path, repo: Path) -> None:
    if is_git_repo(source) and repo.exists():
        git_result(source, ["worktree", "remove", "--force", str(repo)])
        git_result(source, ["worktree", "prune"])
    _safe_rmtree(task_dir, tasks_root)


def _safe_rmtree(target: Path, allowed_root: Path) -> None:
    resolved_target = target.resolve()
    resolved_allowed = allowed_root.resolve()
    if resolved_target == resolved_allowed or resolved_allowed not in resolved_target.parents:
        raise RuntimeError(f"Refusing to remove path outside Integration workspace: {resolved_target}")
    shutil.rmtree(resolved_target)


def _same_commit(expected: str, actual: str) -> bool:
    expected = expected.strip()
    actual = actual.strip()
    return expected.startswith(actual) or actual.startswith(expected)


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part.strip() for part in (result.stdout, result.stderr) if part and part.strip())

