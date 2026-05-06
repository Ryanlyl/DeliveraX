from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from api_server.bootstrap import repo_root


class Settings(BaseModel):
    app_name: str = "DeliveraX API"
    api_prefix: str = "/api"
    repo_root: Path = Field(default_factory=repo_root)
    artifacts_root: Path | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    @property
    def resolved_artifacts_root(self) -> Path:
        return (self.artifacts_root or self.repo_root / "artifacts").resolve()


@lru_cache
def get_settings() -> Settings:
    resolved_repo_root = Path(os.getenv("DELIVERAX_REPO_ROOT", repo_root())).resolve()
    artifacts_root = os.getenv("DELIVERAX_ARTIFACTS_ROOT")
    cors_origins = os.getenv("DELIVERAX_CORS_ORIGINS")
    return Settings(
        repo_root=resolved_repo_root,
        artifacts_root=Path(artifacts_root).resolve() if artifacts_root else None,
        cors_origins=[item.strip() for item in cors_origins.split(",")] if cors_origins else Settings().cors_origins,
    )
