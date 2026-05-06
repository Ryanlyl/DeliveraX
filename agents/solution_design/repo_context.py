from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.parse import quote, urlparse

from .schemas import RepoContext, RepoFetchMetadata


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

FETCH_METADATA_FILE = ".solution_design_fetch.json"
DEFAULT_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
T = TypeVar("T")


def resolve_workspace_dir(configured: str | None = None) -> Path:
    if configured:
        return Path(configured).resolve()
    env_dir = os.getenv("SOLUTION_DESIGN_WORKSPACE_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return Path(__file__).resolve().parents[1] / ".workspace"


def prepare_repository(
    repo_url: str | None,
    repo_path: str | None,
    repo_ref: str | None,
    workspace_dir: str | None,
    task_id: str | None = None,
) -> RepoFetchMetadata:
    if repo_path:
        root = Path(repo_path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Repository path does not exist: {root}")
        validation = _validate_repository_root(root)
        return _make_fetch_metadata(
            repo_root=root,
            repo_url=None,
            requested_ref=repo_ref,
            resolved_ref=_get_git_current_ref(root) or repo_ref,
            commit_sha=_get_git_commit_sha(root),
            fetch_method="local",
            cache_key=None,
            cached=False,
            validation=validation,
        )

    if not repo_url:
        raise ValueError("Either repo_url or repo_path is required.")

    workspace = resolve_workspace_dir(workspace_dir)
    _cleanup_workspace_cache(workspace)
    repos_dir = _resolve_repos_dir(workspace, task_id)
    repos_dir.mkdir(parents=True, exist_ok=True)
    cache_key = _repo_cache_key(repo_url, repo_ref)
    target = repos_dir / cache_key

    with _directory_lock(target):
        if target.exists() and any(target.iterdir()):
            try:
                validation = _validate_repository_root(target)
                cached_metadata = _read_fetch_metadata(target)
                if cached_metadata:
                    cached_metadata.update(validation)
                    cached_metadata["cached"] = True
                    return cached_metadata
                return _make_fetch_metadata(
                    repo_root=target,
                    repo_url=repo_url,
                    requested_ref=repo_ref,
                    resolved_ref=_get_git_current_ref(target) or repo_ref,
                    commit_sha=_get_git_commit_sha(target),
                    fetch_method="cache",
                    cache_key=cache_key,
                    cached=True,
                    validation=validation,
                )
            except Exception:
                _safe_rmtree(target, repos_dir)

        git_error: Exception | None = None
        try:
            metadata = _retry(lambda: _clone_with_git(repo_url, repo_ref, target), label="git clone")
        except Exception as exc:
            git_error = exc
            if target.exists():
                _safe_rmtree(target, repos_dir)
            try:
                metadata = _retry(
                    lambda: _download_github_archive(repo_url, repo_ref, target),
                    label="GitHub archive download",
                )
            except Exception as archive_error:
                raise RuntimeError(
                    "Failed to fetch repository via both git clone and GitHub archive. "
                    f"Git error: {_redact_secret(str(git_error))}. "
                    f"Archive error: {_redact_secret(str(archive_error))}."
                ) from archive_error

        validation = _validate_repository_root(target)
        metadata.update(validation)
        metadata.update(
            {
                "repo_root": str(target),
                "repo_url": repo_url,
                "requested_ref": repo_ref,
                "cache_key": cache_key,
                "cached": False,
            }
        )
        _write_fetch_metadata(target, metadata)
        if git_error:
            metadata["fallback_reason"] = _redact_secret(str(git_error))
        return metadata


def build_repo_context(
    repo_root: str | Path,
    requirement_text: str,
    *,
    max_context_files: int = 24,
    max_file_chars: int = 9000,
    repo_fetch: RepoFetchMetadata | None = None,
) -> RepoContext:
    root = Path(repo_root).resolve()
    package_json_path = _find_package_json(root)
    all_files = _iter_candidate_files(root)
    detected_stack = _detect_stack(root, package_json_path)
    selected = _select_context_files(root, all_files, requirement_text, max_context_files)

    key_files: list[dict[str, str]] = []
    omitted_files: list[str] = []
    for rel_path in selected:
        full_path = root / rel_path
        try:
            text = _read_text_file(full_path, max_file_chars)
            key_files.append({"path": rel_path, "content": text})
        except Exception as exc:
            omitted_files.append(f"{rel_path}: {exc}")

    fetch = repo_fetch or {}
    return {
        "repo_root": str(root),
        "repo_name": root.name,
        "repo_source": fetch.get("repo_url") or str(root),
        "repo_url": fetch.get("repo_url"),
        "requested_ref": fetch.get("requested_ref"),
        "resolved_ref": fetch.get("resolved_ref"),
        "commit_sha": fetch.get("commit_sha"),
        "fetch_method": fetch.get("fetch_method"),
        "cache_key": fetch.get("cache_key"),
        "cached": fetch.get("cached", False),
        "package_json_path": _relative_or_none(root, package_json_path),
        "frontend_repo_valid": bool(fetch.get("frontend_repo_valid", package_json_path is not None)),
        "validation_warnings": fetch.get("validation_warnings", []),
        "tree": _build_tree(root, all_files, max_entries=220),
        "detected_stack": detected_stack,
        "key_files": key_files,
        "candidate_files": all_files[:500],
        "omitted_files": omitted_files,
    }


def format_repo_context_for_prompt(context: RepoContext) -> str:
    file_blocks = []
    for item in context.get("key_files", []):
        file_blocks.append(
            f"### File: {item['path']}\n"
            "```text\n"
            f"{item['content']}\n"
            "```"
        )
    metadata = {
        "repo_source": context.get("repo_source"),
        "requested_ref": context.get("requested_ref"),
        "resolved_ref": context.get("resolved_ref"),
        "commit_sha": context.get("commit_sha"),
        "fetch_method": context.get("fetch_method"),
        "cached": context.get("cached"),
        "package_json_path": context.get("package_json_path"),
        "frontend_repo_valid": context.get("frontend_repo_valid"),
        "validation_warnings": context.get("validation_warnings", []),
    }
    return "\n\n".join(
        [
            f"Repository: {context.get('repo_name', '')}",
            "Repository metadata:",
            json.dumps(metadata, ensure_ascii=False, indent=2),
            "Detected stack:",
            json.dumps(context.get("detected_stack", {}), ensure_ascii=False, indent=2),
            "Repository tree:",
            "```text\n" + context.get("tree", "") + "\n```",
            "Selected file contents:",
            "\n\n".join(file_blocks),
        ]
    )


def _repo_cache_key(repo_url: str, repo_ref: str | None) -> str:
    parsed = urlparse(repo_url)
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    owner_repo = re.sub(r"[^A-Za-z0-9._-]+", "_", path.strip("/"))
    ref = re.sub(r"[^A-Za-z0-9._-]+", "_", repo_ref or "default")
    digest = hashlib.sha1(f"{repo_url}@{repo_ref or 'default'}".encode("utf-8")).hexdigest()[:8]
    return f"{owner_repo}_{ref}_{digest}"


def _clone_with_git(repo_url: str, repo_ref: str | None, target: Path) -> RepoFetchMetadata:
    if target.exists():
        _safe_rmtree(target, target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)

    clone_url = _authenticated_clone_url(repo_url)
    command = ["git", "clone", "--depth", "1"]
    if repo_ref and not _looks_like_commit_sha(repo_ref):
        command.extend(["--branch", repo_ref])
    command.extend([clone_url, str(target)])
    _run_git(command, cwd=None)

    try:
        if repo_ref and _looks_like_commit_sha(repo_ref):
            _run_git(["git", "fetch", "--depth", "1", "origin", repo_ref], cwd=target)
            _run_git(["git", "checkout", "--detach", repo_ref], cwd=target)
    finally:
        _sanitize_git_origin(target, repo_url)

    return _make_fetch_metadata(
        repo_root=target,
        repo_url=repo_url,
        requested_ref=repo_ref,
        resolved_ref=_get_git_current_ref(target) or repo_ref,
        commit_sha=_get_git_commit_sha(target),
        fetch_method="git",
        cache_key=None,
        cached=False,
        validation={},
    )


def _download_github_archive(repo_url: str, repo_ref: str | None, target: Path) -> RepoFetchMetadata:
    if target.exists():
        _safe_rmtree(target, target.parent)
    owner, repo = _parse_github_owner_repo(repo_url)
    resolved_ref, commit_sha = _resolve_github_commit(owner, repo, repo_ref)
    archive_ref = commit_sha or resolved_ref
    archive_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{quote(archive_ref, safe='')}"
    target.parent.mkdir(parents=True, exist_ok=True)
    zip_path = target.parent / f"{target.name}.zip"

    _download_file(archive_url, zip_path)
    extract_root = target.parent / f"{target.name}_extract"
    if extract_root.exists():
        _safe_rmtree(extract_root, target.parent)
    extract_root.mkdir(parents=True, exist_ok=True)

    try:
        _safe_extract_zip(zip_path, extract_root)
        children = [child for child in extract_root.iterdir() if child.is_dir()]
        if not children:
            raise RuntimeError(f"Downloaded archive has no repository directory: {archive_url}")
        shutil.move(str(children[0]), str(target))
    finally:
        if extract_root.exists():
            _safe_rmtree(extract_root, target.parent)
        zip_path.unlink(missing_ok=True)

    return _make_fetch_metadata(
        repo_root=target,
        repo_url=repo_url,
        requested_ref=repo_ref,
        resolved_ref=resolved_ref,
        commit_sha=commit_sha,
        fetch_method="github_archive",
        cache_key=None,
        cached=False,
        validation={},
    )


def _resolve_github_commit(owner: str, repo: str, repo_ref: str | None) -> tuple[str, str | None]:
    ref = repo_ref or _get_github_default_branch(owner, repo)
    payload = _github_api_get_json(f"https://api.github.com/repos/{owner}/{repo}/commits/{quote(ref, safe='')}")
    return ref, payload.get("sha")


def _get_github_default_branch(owner: str, repo: str) -> str:
    payload = _github_api_get_json(f"https://api.github.com/repos/{owner}/{repo}")
    return payload.get("default_branch") or "main"


def _github_api_get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=_github_headers())
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_file(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers=_github_headers())
    with urllib.request.urlopen(request, timeout=120) as response:
        with target.open("wb") as output:
            shutil.copyfileobj(response, output)


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "DeliveraX-SolDesign",
    }
    token = _github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_github_owner_repo(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url)
    if parsed.netloc.lower() != "github.com":
        raise ValueError("Archive fallback currently supports github.com repositories only.")
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return parts[0], repo


def _validate_repository_root(root: Path) -> dict[str, Any]:
    if not root.exists() or not root.is_dir():
        raise RuntimeError(f"Repository root is not a directory: {root}")

    non_git_files = [
        path
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts and path.name != FETCH_METADATA_FILE
    ]
    if not non_git_files:
        raise RuntimeError(f"Repository is empty after fetch: {root}")

    package_json_path = _find_package_json(root)
    warnings: list[str] = []
    if not package_json_path:
        message = "Repository does not look like a frontend project: package.json was not found."
        if _require_package_json():
            raise RuntimeError(message)
        warnings.append(message)

    return {
        "package_json_path": _relative_or_none(root, package_json_path),
        "frontend_repo_valid": package_json_path is not None,
        "validation_warnings": warnings,
    }


def _find_package_json(root: Path) -> Path | None:
    direct = root / "package.json"
    if direct.exists():
        return direct

    candidates: list[Path] = []
    for path in root.rglob("package.json"):
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS for part in rel_parts):
            continue
        if len(rel_parts) <= 4:
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (len(item.relative_to(root).parts), item.as_posix()))
    return candidates[0]


def _iter_candidate_files(root: Path) -> list[str]:
    files: list[str] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if path.name == FETCH_METADATA_FILE:
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


def _detect_stack(root: Path, package_json_path: Path | None = None) -> dict[str, object]:
    package_json = package_json_path or root / "package.json"
    package_root = package_json.parent if package_json.exists() else root
    stack: dict[str, object] = {
        "has_package_json": package_json.exists(),
        "package_json_path": _relative_or_none(root, package_json) if package_json.exists() else None,
        "frameworks": [],
        "scripts": {},
        "package_manager": None,
    }
    if (package_root / "pnpm-lock.yaml").exists() or (root / "pnpm-lock.yaml").exists():
        stack["package_manager"] = "pnpm"
    elif (package_root / "yarn.lock").exists() or (root / "yarn.lock").exists():
        stack["package_manager"] = "yarn"
    elif (package_root / "package-lock.json").exists() or (root / "package-lock.json").exists():
        stack["package_manager"] = "npm"

    if package_json.exists():
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
            deps = {**payload.get("dependencies", {}), **payload.get("devDependencies", {})}
            stack["scripts"] = payload.get("scripts", {})
            for name in ("react", "vue", "svelte", "next", "nuxt", "vite", "typescript", "tailwindcss"):
                if name in deps:
                    stack["frameworks"].append(name)
        except Exception as exc:
            stack["package_json_error"] = str(exc)
    return stack


def _select_context_files(root: Path, all_files: list[str], requirement_text: str, max_files: int) -> list[str]:
    scored: list[tuple[int, str]] = []
    keywords = _extract_keywords(requirement_text)

    for rel_path in all_files:
        score = 0
        normalized = rel_path.lower()
        if rel_path in HIGH_VALUE_NAMES:
            score += 100
        if "/src/" in f"/{normalized}" or normalized.startswith("src/"):
            score += 20
        if any(token in normalized for token in ("api", "service", "request", "client", "route", "router", "store", "state")):
            score += 18
        if any(token in normalized for token in ("component", "page", "view", "screen", "layout")):
            score += 14
        score += sum(8 for keyword in keywords if keyword and keyword.lower() in normalized)
        if Path(rel_path).name in {"package.json", "README.md"}:
            score += 50
        scored.append((score, rel_path))

    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = [rel_path for score, rel_path in scored if score > 0][:max_files]
    if len(selected) < max_files:
        for _, rel_path in scored:
            if rel_path not in selected:
                selected.append(rel_path)
            if len(selected) >= max_files:
                break
    return selected


def _extract_keywords(text: str) -> list[str]:
    ascii_words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
    chinese_chunks = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    stop_words = {
        "requirement",
        "feature",
        "page",
        "user",
        "system",
        "current",
        "implementation",
        "description",
        "status",
    }
    keywords = []
    for token in ascii_words + chinese_chunks:
        if token in stop_words:
            continue
        if token not in keywords:
            keywords.append(token)
    return keywords[:40]


def _build_tree(root: Path, files: list[str], max_entries: int) -> str:
    lines = [root.name + "/"]
    for rel_path in files[:max_entries]:
        depth = rel_path.count("/")
        indent = "  " * depth
        lines.append(f"{indent}- {rel_path}")
    if len(files) > max_entries:
        lines.append(f"... {len(files) - max_entries} more files omitted")
    return "\n".join(lines)


def _read_text_file(path: Path, max_chars: int) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[...truncated...]"
    return text


def _run_git(command: list[str], cwd: Path | None) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        output = "\n".join(part for part in (exc.stdout, exc.stderr) if part)
        raise RuntimeError(_redact_secret(output or str(exc))) from exc


def _get_git_commit_sha(root: Path) -> str | None:
    if not (root / ".git").exists():
        metadata = _read_fetch_metadata(root)
        return metadata.get("commit_sha") if metadata else None
    try:
        return _run_git(["git", "rev-parse", "HEAD"], cwd=root)
    except Exception:
        return None


def _get_git_current_ref(root: Path) -> str | None:
    if not (root / ".git").exists():
        metadata = _read_fetch_metadata(root)
        return metadata.get("resolved_ref") if metadata else None
    try:
        ref = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
        return None if ref == "HEAD" else ref
    except Exception:
        return None


def _sanitize_git_origin(root: Path, repo_url: str) -> None:
    if not (root / ".git").exists():
        return
    try:
        _run_git(["git", "remote", "set-url", "origin", repo_url], cwd=root)
    except Exception:
        pass


def _authenticated_clone_url(repo_url: str) -> str:
    token = _github_token()
    if not token:
        return repo_url
    parsed = urlparse(repo_url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        return repo_url
    return f"{parsed.scheme}://x-access-token:{quote(token, safe='')}@{parsed.netloc}{parsed.path}"


def _github_token() -> str | None:
    return os.getenv("SOLUTION_DESIGN_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")


def _looks_like_commit_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{7,40}", value))


def _make_fetch_metadata(
    *,
    repo_root: Path,
    repo_url: str | None,
    requested_ref: str | None,
    resolved_ref: str | None,
    commit_sha: str | None,
    fetch_method: str,
    cache_key: str | None,
    cached: bool,
    validation: dict[str, Any],
) -> RepoFetchMetadata:
    metadata: RepoFetchMetadata = {
        "repo_root": str(repo_root),
        "repo_name": repo_root.name,
        "repo_url": repo_url,
        "requested_ref": requested_ref,
        "resolved_ref": resolved_ref,
        "commit_sha": commit_sha,
        "fetch_method": fetch_method,
        "cache_key": cache_key,
        "cached": cached,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "package_json_path": validation.get("package_json_path"),
        "frontend_repo_valid": validation.get("frontend_repo_valid", False),
        "validation_warnings": validation.get("validation_warnings", []),
    }
    return metadata


def _read_fetch_metadata(root: Path) -> RepoFetchMetadata | None:
    metadata_path = root / FETCH_METADATA_FILE
    if not metadata_path.exists():
        return None
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_fetch_metadata(root: Path, metadata: RepoFetchMetadata) -> None:
    (root / FETCH_METADATA_FILE).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def _relative_or_none(root: Path, path: Path | None) -> str | None:
    if not path:
        return None
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _resolve_repos_dir(workspace: Path, task_id: str | None) -> Path:
    configured_task_id = task_id or os.getenv("SOLUTION_DESIGN_TASK_ID")
    if configured_task_id:
        safe_task_id = re.sub(r"[^A-Za-z0-9._-]+", "_", configured_task_id).strip("_") or "task"
        return workspace / "tasks" / safe_task_id / "repos"
    return workspace / "repos"


@contextmanager
def _directory_lock(target: Path):
    lock_dir = target.parent / f"{target.name}.lock"
    timeout_seconds = int(os.getenv("SOLUTION_DESIGN_LOCK_TIMEOUT_SECONDS", "60"))
    stale_seconds = int(os.getenv("SOLUTION_DESIGN_LOCK_STALE_SECONDS", "600"))
    start = time.time()
    while True:
        try:
            lock_dir.mkdir(parents=True)
            break
        except FileExistsError:
            try:
                if time.time() - lock_dir.stat().st_mtime > stale_seconds:
                    _safe_rmtree(lock_dir, target.parent)
                    continue
            except FileNotFoundError:
                continue
            if time.time() - start > timeout_seconds:
                raise TimeoutError(f"Timed out waiting for repository cache lock: {lock_dir}")
            time.sleep(0.5)
    try:
        yield
    finally:
        if lock_dir.exists():
            _safe_rmtree(lock_dir, target.parent)


def _cleanup_workspace_cache(workspace: Path) -> None:
    ttl = _cache_ttl_seconds()
    if ttl <= 0:
        return
    now = time.time()
    for base in (workspace / "repos", workspace / "tasks"):
        if not base.exists():
            continue
        for child in base.iterdir():
            if not child.is_dir():
                continue
            if child.name.endswith(".lock"):
                if now - child.stat().st_mtime > int(os.getenv("SOLUTION_DESIGN_LOCK_STALE_SECONDS", "600")):
                    _safe_rmtree(child, base)
                continue
            lock_sibling = child.parent / f"{child.name}.lock"
            if lock_sibling.exists():
                continue
            if now - child.stat().st_mtime > ttl:
                _safe_rmtree(child, base)


def _cache_ttl_seconds() -> int:
    raw = os.getenv("SOLUTION_DESIGN_CACHE_TTL_SECONDS")
    if raw is None:
        return DEFAULT_CACHE_TTL_SECONDS
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_CACHE_TTL_SECONDS


def _require_package_json() -> bool:
    raw = os.getenv("SOLUTION_DESIGN_REQUIRE_PACKAGE_JSON", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _safe_rmtree(target: Path, allowed_root: Path) -> None:
    resolved_target = target.resolve()
    resolved_root = allowed_root.resolve()
    if resolved_target == resolved_root or resolved_root not in resolved_target.parents:
        raise RuntimeError(f"Refusing to delete path outside workspace: {resolved_target}")
    shutil.rmtree(resolved_target)


def _safe_extract_zip(zip_path: Path, extract_root: Path) -> None:
    resolved_root = extract_root.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            destination = (extract_root / member.filename).resolve()
            if destination != resolved_root and resolved_root not in destination.parents:
                raise RuntimeError(f"Unsafe zip entry path: {member.filename}")
        archive.extractall(extract_root)


def _retry(operation: Callable[[], T], *, label: str) -> T:
    attempts = int(os.getenv("SOLUTION_DESIGN_RETRY_ATTEMPTS", "3"))
    delay = float(os.getenv("SOLUTION_DESIGN_RETRY_DELAY_SECONDS", "1.0"))
    last_exc: Exception | None = None
    for attempt in range(1, max(attempts, 1) + 1):
        try:
            return operation()
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            time.sleep(delay * attempt)
    raise RuntimeError(f"{label} failed after {attempts} attempt(s): {_redact_secret(str(last_exc))}") from last_exc


def _redact_secret(text: str) -> str:
    token = _github_token()
    if token:
        text = text.replace(token, "***")
    return re.sub(r"x-access-token:[^@\\s]+@", "x-access-token:***@", text)

