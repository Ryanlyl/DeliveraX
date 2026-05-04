from __future__ import annotations

import asyncio
from threading import Thread
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from api_server.engine.models import PipelineRun
from api_server.engine.planner import collect_upstream_artifacts, topological_stage_order
from api_server.engine.run_store import JsonPipelineRunStore, PipelineRunNotFoundError
from api_server.engine.state_machine import TransitionError, transition_run
from api_server.schemas import PipelineRunInput, StageRunInput
from api_server.services.pipeline_service import PipelineService
from stage_contracts import StageError


class PipelineRunner:
    def __init__(
        self,
        *,
        service: PipelineService,
        run_store: JsonPipelineRunStore,
    ) -> None:
        self.service = service
        self.run_store = run_store

    def start_run(self, pipeline_id: str, payload: PipelineRunInput) -> PipelineRun:
        pipeline = self.service.get(pipeline_id)
        definition = self.service._pipeline_definition()  # noqa: SLF001
        full_stage_order = [
            stage_id
            for stage_id in topological_stage_order(definition)
            if stage_id in {stage.id for stage in pipeline.stages}
        ]
        start_index = full_stage_order.index(payload.start_stage_id) if payload.start_stage_id else 0
        stage_order = full_stage_order[start_index:]

        run = PipelineRun(
            id=uuid4().hex,
            pipeline_id=pipeline_id,
            pipeline_definition_id=getattr(definition, "id", None),
            status="queued",
            stage_order=stage_order,
            current_stage_id=None,
            next_stage_id=stage_order[0] if stage_order else None,
            completed_stage_ids=[],
            failed_stage_id=None,
            rejected_stage_id=None,
            pause_requested=False,
            terminate_requested=False,
            artifact_refs_by_stage={},
            checkpoint_ids=[],
            error=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            started_at=None,
            ended_at=None,
            logs=["Created by start_run"],
        )
        self.run_store.create(run)

        # Mirror into pipeline record for compatibility
        self.service.mirror_run_status_to_pipeline(run)

        self._spawn_background(pipeline_id, run.id, payload)
        return run

    def get_run(self, pipeline_id: str, run_id: str) -> PipelineRun:
        return self.run_store.get(pipeline_id, run_id)

    def pause_run(self, pipeline_id: str, run_id: str | None = None) -> PipelineRun:
        run = self._resolve_run(pipeline_id, run_id)
        run.pause_requested = True
        run.logs.append("Pause requested")
        self.run_store.save(run)
        return run

    def resume_run(self, pipeline_id: str, run_id: str | None = None) -> PipelineRun:
        run = self._resolve_run(pipeline_id, run_id)
        # allow resume from paused/pending_approval/rejected/failed
        if run.status in {"succeeded", "terminated"}:
            return run
        run.pause_requested = False
        run.terminate_requested = False
        run.logs.append("Resume requested")
        self.run_store.save(run)
        self._spawn_background(pipeline_id, run.id, PipelineRunInput())
        return run

    def reject_run(
        self,
        pipeline_id: str,
        run_id: str | None,
        *,
        stage_id: str,
        reason: str | None = None,
    ) -> PipelineRun:
        run = self._resolve_run(pipeline_id, run_id)
        run.rejected_stage_id = stage_id
        if reason:
            run.logs.append(reason)
        transition_run(run, "rejected", reason="Rejected via API")
        self.run_store.save(run)
        self.service.mirror_run_status_to_pipeline(run)
        return run

    def terminate_run(self, pipeline_id: str, run_id: str | None = None) -> PipelineRun:
        run = self._resolve_run(pipeline_id, run_id)
        run.terminate_requested = True
        run.logs.append("Terminate requested")
        self.run_store.save(run)
        return run

    async def execute_run(self, pipeline_id: str, run_id: str, payload: PipelineRunInput | None = None) -> None:
        try:
            run = self.run_store.get(pipeline_id, run_id)
        except PipelineRunNotFoundError:
            return

        if run.status in {"succeeded", "terminated"}:
            return

        # Transition to running if possible
        if run.status != "running":
            try:
                transition_run(run, "running", reason="Runner started")
            except TransitionError:
                # if already failed/rejected etc, allow to go running via state machine
                try:
                    transition_run(run, "running", reason="Runner resumed")
                except TransitionError:
                    return
            self.run_store.save(run)
            self.service.mirror_run_status_to_pipeline(run)

        stage_order = list(run.stage_order)
        # rebuild stage_order if empty
        if not stage_order:
            pipeline = self.service.get(pipeline_id)
            definition = self.service._pipeline_definition()  # noqa: SLF001
            stage_order = [
                stage_id
                for stage_id in topological_stage_order(definition)
                if stage_id in {stage.id for stage in pipeline.stages}
            ]
            run.stage_order = stage_order

        for stage_id in stage_order:
            run = self.run_store.get(pipeline_id, run_id)

            if stage_id in run.completed_stage_ids:
                continue

            # If we were blocked on approval and the stage has been approved externally,
            # do not re-run the stage; just mark it as completed and continue.
            if run.current_stage_id == stage_id:
                pipeline_view = self.service.get(pipeline_id)
                approved_stage = next(s for s in pipeline_view.stages if s.id == stage_id)
                if approved_stage.status == "succeeded":
                    run.completed_stage_ids.append(stage_id)
                    run.artifact_refs_by_stage[stage_id] = list(approved_stage.output_artifacts)
                    run.current_stage_id = None
                    # move run back to running to proceed
                    try:
                        transition_run(run, "running", reason="Approved externally")
                    except TransitionError:
                        pass
                    self.run_store.save(run)
                    self.service.mirror_run_status_to_pipeline(run)
                    continue

            run.current_stage_id = stage_id
            next_ids = [sid for sid in stage_order if sid not in run.completed_stage_ids and sid != stage_id]
            run.next_stage_id = next_ids[0] if next_ids else None
            self.run_store.save(run)

            if run.terminate_requested:
                transition_run(run, "terminated", reason="Terminated before stage execution")
                self.run_store.save(run)
                self.service.mirror_run_status_to_pipeline(run)
                return

            if run.pause_requested:
                transition_run(run, "paused", reason="Paused before stage execution")
                self.run_store.save(run)
                self.service.mirror_run_status_to_pipeline(run)
                return

            # input artifacts strictly from ArtifactRef aggregation
            input_artifacts = collect_upstream_artifacts(
                stage_id,
                run.artifact_refs_by_stage,
                self.service._registry_pipeline_definition(),  # noqa: SLF001
            )

            try:
                pipeline = await self.service.run_stage(
                    pipeline_id,
                    stage_id,
                    StageRunInput(
                        run_id=f"{run.id}-{stage_id}",
                        input_artifacts=input_artifacts,
                        repo_path=payload.repo_path if payload else None,
                        options=payload.options if payload else {},
                    ),
                )
            except Exception as exc:
                run = self.run_store.get(pipeline_id, run_id)
                run.failed_stage_id = stage_id
                run.error = StageError(code=exc.__class__.__name__, message=str(exc))
                transition_run(run, "failed", reason=f"Stage crashed: {exc}")
                self.run_store.save(run)
                self.service.mirror_run_status_to_pipeline(run)
                return

            # read stage status from pipeline record
            stage_record = next(stage for stage in pipeline.stages if stage.id == stage_id)
            run = self.run_store.get(pipeline_id, run_id)

            if stage_record.status == "succeeded" or stage_record.status == "skipped":
                run.completed_stage_ids.append(stage_id)
                run.artifact_refs_by_stage[stage_id] = list(stage_record.output_artifacts)
                run.current_stage_id = None
                self.run_store.save(run)
                continue

            if stage_record.status == "pending_approval":
                transition_run(run, "pending_approval", reason="Blocked on approval")
                self.run_store.save(run)
                self.service.mirror_run_status_to_pipeline(run)
                return

            if stage_record.status == "rejected":
                run.rejected_stage_id = stage_id
                transition_run(run, "rejected", reason="Stage rejected")
                self.run_store.save(run)
                self.service.mirror_run_status_to_pipeline(run)
                return

            if stage_record.status in {"failed", "cancelled"}:
                run.failed_stage_id = stage_id
                run.error = stage_record.error
                transition_run(run, "failed", reason="Stage failed")
                self.run_store.save(run)
                self.service.mirror_run_status_to_pipeline(run)
                return

        run = self.run_store.get(pipeline_id, run_id)
        transition_run(run, "succeeded", reason="All stages completed")
        run.current_stage_id = None
        run.next_stage_id = None
        self.run_store.save(run)
        self.service.mirror_run_status_to_pipeline(run)

    def _resolve_run(self, pipeline_id: str, run_id: str | None) -> PipelineRun:
        if run_id:
            return self.run_store.get(pipeline_id, run_id)
        latest = self.run_store.latest(pipeline_id)
        if latest is None:
            raise PipelineRunNotFoundError(f"No runs for pipeline {pipeline_id}")
        return latest

    def _spawn_background(self, pipeline_id: str, run_id: str, payload: PipelineRunInput) -> None:
        def runner() -> None:
            try:
                asyncio.run(self.execute_run(pipeline_id, run_id, payload))
            except Exception as exc:  # noqa: BLE001
                try:
                    run = self.run_store.get(pipeline_id, run_id)
                    run.failed_stage_id = run.current_stage_id
                    run.error = StageError(code=exc.__class__.__name__, message=str(exc))
                    run.logs.append(f"Runner crashed: {exc}")
                    try:
                        transition_run(run, "failed", reason="Runner crashed")
                    except TransitionError:
                        run.status = "failed"
                    self.run_store.save(run)
                    self.service.mirror_run_status_to_pipeline(run)
                except Exception:
                    return

        Thread(target=runner, daemon=True).start()
