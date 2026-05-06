from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from api_server.storage.projects import JsonProjectStore, ProjectNotFoundError

logger = logging.getLogger(__name__)


def clone_project_repo(project_id: str, project_store: JsonProjectStore, artifacts_root: Path) -> None:
    try:
        project = project_store.get(project_id)
    except ProjectNotFoundError:
        logger.warning("Project %s not found before clone task started", project_id)
        return

    repos_root = artifacts_root.resolve() / "_repos"
    target_dir = repos_root / project.id

    project.clone_status = "cloning"
    project.clone_path = None
    project.clone_error = None
    project_store.save(project)

    try:
        repos_root.mkdir(parents=True, exist_ok=True)

        if target_dir.exists():
            # Reuse existing valid git checkout to keep behavior stable and fast.
            if (target_dir / ".git").is_dir() and any(target_dir.iterdir()):
                project.clone_status = "ready"
                project.clone_path = str(target_dir.resolve())
                project.clone_error = None
                project_store.save(project)
                return
            shutil.rmtree(target_dir, ignore_errors=True)

        result = subprocess.run(
            ["git", "clone", project.github_url, str(target_dir)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git clone failed")

        project.clone_status = "ready"
        project.clone_path = str(target_dir.resolve())
        project.clone_error = None
        project_store.save(project)
    except Exception as exc:
        logger.exception("Failed to clone project repo for project_id=%s into %s", project_id, target_dir)
        try:
            project = project_store.get(project_id)
            project.clone_status = "failed"
            project.clone_path = None
            project.clone_error = str(exc).strip() or exc.__class__.__name__
            project_store.save(project)
        except Exception:
            logger.exception("Failed to persist clone failure status for project_id=%s", project_id)
