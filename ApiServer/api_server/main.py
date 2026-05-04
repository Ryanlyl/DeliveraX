from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_server.config import get_settings
from api_server.routers import artifacts, checkpoints, health, pipelines, providers, stages
from api_server.engine.run_store import JsonPipelineRunStore
from api_server.engine.runner import PipelineRunner
from api_server.services.approval_service import ApprovalService
from api_server.services.artifact_service import ArtifactService
from api_server.services.checkpoint_service import CheckpointService
from api_server.services.pipeline_service import PipelineService
from api_server.services.stage_executor import StageExecutor
from api_server.stage_registry import StageRegistry
from api_server.storage.json_store import JsonPipelineStore

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """Load .env from repo root into os.environ. Does nothing if file is missing."""
    # Repo root is two levels above this file: ApiServer/api_server/main.py → repo_root
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        # Fallback: parse manually
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _verify_api_keys() -> None:
    """Log a prominent warning if no LLM provider API keys are configured."""
    from api_server.providers.registry import provider_registry
    configured: list[str] = []
    unconfigured: list[str] = []
    for pid, pdef in provider_registry().items():
        if not pdef.available:
            continue
        if pdef.api_key_env and os.getenv(pdef.api_key_env):
            configured.append(f"{pdef.name} ({pdef.api_key_env})")
        elif pdef.api_key_env:
            unconfigured.append(f"{pdef.name} ({pdef.api_key_env})")
    if configured:
        logger.info("LLM providers with API keys: %s", ", ".join(configured))
    else:
        logger.warning(
            "NO LLM API KEYS FOUND. Set one of: %s. "
            "Copy .env.example to .env and fill in your keys.",
            ", ".join(unconfigured) if unconfigured else "DEEPSEEK_API_KEY, QWEN_API_KEY",
        )
    if unconfigured:
        logger.info("LLM providers without API keys: %s", ", ".join(unconfigured))


def create_app() -> FastAPI:
    _load_dotenv()
    _verify_api_keys()

    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    registry = StageRegistry(settings.repo_root)
    store = JsonPipelineStore(settings.resolved_artifacts_root)
    executor = StageExecutor(registry)

    app.state.settings = settings
    app.state.stage_registry = registry
    app.state.pipeline_store = store
    app.state.pipeline_run_store = JsonPipelineRunStore(settings.resolved_artifacts_root)
    app.state.stage_executor = executor
    app.state.pipeline_service = PipelineService(
        store=store,
        registry=registry,
        executor=executor,
        artifacts_root=str(settings.resolved_artifacts_root),
    )
    app.state.pipeline_runner = PipelineRunner(
        service=app.state.pipeline_service,
        run_store=app.state.pipeline_run_store,
    )
    app.state.artifact_service = ArtifactService(settings.resolved_artifacts_root)
    app.state.checkpoint_service = CheckpointService(
        store=store,
        registry=registry,
        pipeline_service=app.state.pipeline_service,
        run_store=app.state.pipeline_run_store,
        artifacts_root=settings.resolved_artifacts_root,
    )
    app.state.pipeline_service.checkpoint_service = app.state.checkpoint_service
    app.state.approval_service = ApprovalService(store, app.state.checkpoint_service)

    app.include_router(health.router)
    app.include_router(stages.router, prefix=settings.api_prefix)
    app.include_router(pipelines.router, prefix=settings.api_prefix)
    app.include_router(checkpoints.router, prefix=settings.api_prefix)
    app.include_router(providers.router, prefix=settings.api_prefix)
    app.include_router(artifacts.router, prefix=settings.api_prefix)
    return app


app = create_app()
