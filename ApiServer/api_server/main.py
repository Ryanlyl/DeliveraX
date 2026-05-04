from __future__ import annotations

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


def create_app() -> FastAPI:
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
