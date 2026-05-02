from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .schemas import ChangeFile, FileContext, ImplementationContract


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".turbo",
    ".vite",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "vendor",
}

TEXT_EXTENSIONS = {
    ".cjs",
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".scss",
    ".svelte",
    ".ts",
    ".tsx",
    ".vue",
    ".yaml",
    ".yml",
}

HIGH_VALUE_NAMES = {
    "README.md",
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "vite.config.ts",
    "vite.config.js",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "tsconfig.json",
    "tailwind.config.js",
    "tailwind.config.ts",
    "src/main.tsx",
    "src/main.ts",
    "src/App.tsx",
    "src/App.ts",
    "src/router.tsx",
    "src/routes.tsx",
}


def default_workspace_dir() -> Path:
    configured = os.getenv("CODEGEN_WORKSPACE_DIR")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2] / "SolDesign" / ".workspace"


def resolve_repo_root(
    *,
    contract_repo_root: str | None,
    workspace_dir: str | None,
    repo_path: str | None,
    task_id: str | None,
) -> Path:
    if repo_path:
        root = Path(repo_path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Repository path does not exist: {root}")
        return root

    if not contract_repo_root:
        raise ValueError("implementation_contract.repo_root is required when --repo-path is not provided.")

    workspace = Path(workspace_dir).resolve() if workspace_dir else default_workspace_dir()
    raw = contract_repo_root.strip().strip("\"'").replace("\\", "/")
    direct = Path(raw)
    if direct.is_absolute() and direct.exists():
        return direct.resolve()

    candidates = [
        workspace / raw,
        workspace / "repos" / raw,
    ]
    if task_id:
        safe_task_id = re.sub(r"[^A-Za-z0-9._-]+", "_", task_id).strip("_") or "task"
        candidates.append(workspace / "tasks" / safe_task_id / "repos" / raw)

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    found = _search_workspace_for_repo(workspace, raw)
    if found:
        return found

    raise FileNotFoundError(
        "Unable to resolve repository root. "
        f"Tried repo_root `{contract_repo_root}` under workspace `{workspace}`. "
        "Pass --repo-path to override."
    )


def normalize_contract_paths(contract: ImplementationContract, repo_root: Path) -> ImplementationContract:
    repo_name = repo_root.name
    normalized = dict(contract)
    normalized["must_read_files"] = [
        normalize_repo_relative_path(path, repo_name) for path in contract.get("must_read_files", [])
    ]
    changes: list[ChangeFile] = []
    for item in contract.get("change_files", []):
        change = dict(item)
        change["path"] = normalize_repo_relative_path(str(item.get("path", "")), repo_name)
        changes.append(change)
    normalized["change_files"] = changes
    return normalized  # type: ignore[return-value]


def normalize_repo_relative_path(path: str, repo_name: str) -> str:
    cleaned = path.strip().strip("`").strip("\"'").replace("\\", "/").lstrip("/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    if cleaned == repo_name:
        return ""
    prefix = repo_name.rstrip("/") + "/"
    if cleaned.startswith(prefix):
        cleaned = cleaned[len(prefix) :]
    return cleaned


def safe_repo_path(repo_root: str | Path, rel_path: str) -> Path:
    root = Path(repo_root).resolve()
    cleaned = rel_path.replace("\\", "/").lstrip("/")
    if not cleaned:
        raise ValueError("Empty repository-relative path is not allowed.")
    candidate = (root / cleaned).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Path escapes repository root: {rel_path}")
    return candidate


def build_repo_context(
    *,
    repo_root: str | Path,
    contract: ImplementationContract,
    max_context_files: int,
    max_file_chars: int,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    candidate_files = iter_candidate_files(root)
    selected = select_context_files(contract, candidate_files, max_context_files)
    file_contexts: list[FileContext] = []
    for rel_path in selected:
        target = safe_repo_path(root, rel_path)
        if target.exists():
            file_contexts.append(
                {
                    "path": rel_path,
                    "exists": True,
                    "content": read_text_file(target, max_file_chars=max_file_chars),
                }
            )
        else:
            file_contexts.append({"path": rel_path, "exists": False, "content": ""})
    return {
        "repo_root": str(root),
        "repo_name": root.name,
        "tree": build_tree(root, candidate_files, max_entries=220),
        "candidate_files": candidate_files[:500],
        "selected_files": file_contexts,
        "git_status": git_status(root),
        "detected_stack": detect_stack(root),
    }


def read_text_file(path: str | Path, max_file_chars: int | None = None, max_chars: int | None = None) -> str:
    limit = max_file_chars if max_file_chars is not None else max_chars
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = source.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = source.read_text(encoding="utf-8", errors="replace")
    if limit and len(text) > limit:
        return text[:limit] + "\n\n[...truncated...]"
    return text


def iter_candidate_files(root: Path) -> list[str]:
    files: list[str] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS for part in relative_parts):
            continue
        if path.suffix not in TEXT_EXTENSIONS and path.name not in HIGH_VALUE_NAMES:
            continue
        try:
            if path.stat().st_size > 350_000:
                continue
        except OSError:
            continue
        files.append(path.relative_to(root).as_posix())
    return sorted(files)


def select_context_files(contract: ImplementationContract, candidate_files: list[str], max_context_files: int) -> list[str]:
    selected: list[str] = []
    for path in contract.get("must_read_files", []):
        if path and path not in selected:
            selected.append(path)
    for item in contract.get("change_files", []):
        path = item.get("path", "")
        if path and path not in selected:
            selected.append(path)
    for name in HIGH_VALUE_NAMES:
        if name in candidate_files and name not in selected:
            selected.append(name)
    return selected[:max_context_files]


def build_tree(root: Path, files: list[str], max_entries: int) -> str:
    lines = [root.name + "/"]
    for rel_path in files[:max_entries]:
        depth = rel_path.count("/")
        indent = "  " * depth
        lines.append(f"{indent}- {rel_path}")
    if len(files) > max_entries:
        lines.append(f"... {len(files) - max_entries} more files omitted")
    return "\n".join(lines)


def detect_stack(root: Path) -> dict[str, Any]:
    package_json = root / "package.json"
    stack: dict[str, Any] = {
        "has_package_json": package_json.exists(),
        "package_manager": None,
        "scripts": {},
        "frameworks": [],
    }
    if (root / "pnpm-lock.yaml").exists():
        stack["package_manager"] = "pnpm"
    elif (root / "yarn.lock").exists():
        stack["package_manager"] = "yarn"
    elif (root / "package-lock.json").exists():
        stack["package_manager"] = "npm"
    if package_json.exists():
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
            stack["scripts"] = payload.get("scripts", {})
            dependencies = {
                **payload.get("dependencies", {}),
                **payload.get("devDependencies", {}),
            }
            for framework in ("next", "react", "vue", "svelte", "vite", "astro"):
                if framework in dependencies:
                    stack["frameworks"].append(framework)
        except Exception as exc:
            stack["package_json_error"] = str(exc)
    return stack


def git_status(root: Path) -> str:
    if not (root / ".git").exists():
        return "not a git repository"
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={root.as_posix()}", "status", "--short"],
            cwd=str(root),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        lines = [
            line
            for line in result.stdout.strip().splitlines()
            if not line.strip().endswith(".solution_design_fetch.json")
        ]
        return "\n".join(lines).strip()
    except Exception as exc:
        return f"git status failed: {exc}"


def _search_workspace_for_repo(workspace: Path, raw: str) -> Path | None:
    if not workspace.exists():
        return None
    target_names = {raw.rstrip("/").split("/")[-1], raw.replace("/", "_")}
    repos_roots = [workspace / "repos"]
    tasks_root = workspace / "tasks"
    if tasks_root.exists():
        repos_roots.extend(path / "repos" for path in tasks_root.iterdir() if path.is_dir())
    for repos_root in repos_roots:
        if not repos_root.exists():
            continue
        for child in repos_root.iterdir():
            if not child.is_dir():
                continue
            if child.name in target_names or any(child.name.startswith(name + "_") for name in target_names if name):
                return child.resolve()
    return None
