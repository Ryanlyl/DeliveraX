from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from api_server.engine.models import CheckpointRecord, PipelineRun
from api_server.schemas import (
    CheckpointDecisionRequest,
    CurrentCheckpointResponse,
    PipelineRecord,
    PipelineStatus,
    StageRecord,
)
from api_server.storage.json_store import JsonPipelineStore
from stage_contracts import ArtifactRef

if TYPE_CHECKING:
    from api_server.engine.run_store import JsonPipelineRunStore
    from api_server.services.pipeline_service import PipelineService
    from api_server.stage_registry import StageRegistry


class CheckpointNotFoundError(KeyError):
    pass


class CheckpointService:
    def __init__(
        self,
        *,
        store: JsonPipelineStore,
        artifacts_root: str | Path,
        pipeline_service: "PipelineService | None" = None,
        registry: "StageRegistry | None" = None,
        run_store: "JsonPipelineRunStore | None" = None,
    ) -> None:
        self.store = store
        self.artifacts_root = Path(artifacts_root).resolve()
        self.checkpoints_dir = self.artifacts_root / "_checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline_service = pipeline_service
        self.registry = registry
        self.run_store = run_store

    def get_current_checkpoint(self, pipeline_id: str) -> CurrentCheckpointResponse:
        pipeline = self.store.get(pipeline_id)
        stage = self._current_pending_stage(pipeline)
        if stage is None:
            return CurrentCheckpointResponse(
                pipeline_id=pipeline.id,
                run_id=pipeline.latest_run_id,
                checkpoint=None,
                stage=None,
                artifacts=[],
                human_output=None,
            )

        checkpoint = self.create_or_update_pending_checkpoint(pipeline, stage)
        return CurrentCheckpointResponse(
            pipeline_id=pipeline.id,
            run_id=checkpoint.run_id,
            checkpoint=checkpoint,
            stage=stage,
            artifacts=list(stage.output_artifacts),
            human_output=stage.human_output,
        )

    def create_or_update_pending_checkpoint(
        self,
        pipeline: PipelineRecord,
        stage: StageRecord,
    ) -> CheckpointRecord:
        run_id = pipeline.latest_run_id or stage.run_id
        checkpoint_id = self.build_checkpoint_id(pipeline.id, stage.id, run_id)
        checkpoint = self._load_optional(checkpoint_id)
        now = datetime.now(timezone.utc)
        if checkpoint is None:
            checkpoint = CheckpointRecord(
                id=checkpoint_id,
                pipeline_id=pipeline.id,
                run_id=run_id,
                pipeline_run_id=run_id,
                stage_id=stage.id,
                status="pending",
                title=stage.checkpoint_label or stage.name,
                description=stage.checkpoint_description,
                artifact_refs=list(stage.output_artifacts),
                created_at=now,
            )
        else:
            checkpoint.pipeline_id = pipeline.id
            checkpoint.run_id = run_id
            checkpoint.pipeline_run_id = run_id
            checkpoint.stage_id = stage.id
            if checkpoint.status != "pending":
                checkpoint.status = "pending"
                checkpoint.created_at = now
                checkpoint.decided_at = None
                checkpoint.reviewer = None
                checkpoint.comment = None
                checkpoint.reason = None
                checkpoint.reject_reason = None
                checkpoint.rerun_stage_id = None
                checkpoint.reject_artifact = None
            checkpoint.title = stage.checkpoint_label or stage.name
            checkpoint.description = stage.checkpoint_description
            checkpoint.artifact_refs = list(stage.output_artifacts)
        checkpoint = self._save(checkpoint)
        self._attach_checkpoint_to_run(pipeline, checkpoint)
        return checkpoint

    def approve(
        self,
        checkpoint_id: str,
        payload: CheckpointDecisionRequest,
    ) -> PipelineRecord:
        checkpoint = self._load(checkpoint_id)
        pipeline = self.store.get(checkpoint.pipeline_id)
        stage = self._stage(pipeline, checkpoint.stage_id)
        now = datetime.now(timezone.utc)

        checkpoint.status = "approved"
        checkpoint.reviewer = payload.reviewer
        checkpoint.comment = payload.comment
        checkpoint.decided_at = now
        checkpoint.reason = None
        checkpoint.reject_reason = None

        stage.status = "succeeded"
        stage.logs = [
            *stage.logs,
            f"Checkpoint approved by {payload.reviewer or 'human'}"
            + (f": {payload.comment}" if payload.comment else ""),
        ]
        pipeline.status = self._derive_status(pipeline)
        self._save(checkpoint)
        return self.store.save(pipeline)

    def reject(
        self,
        checkpoint_id: str,
        payload: CheckpointDecisionRequest,
    ) -> PipelineRecord:
        checkpoint = self._load(checkpoint_id)
        pipeline = self.store.get(checkpoint.pipeline_id)
        stage = self._stage(pipeline, checkpoint.stage_id)
        reason = (
            payload.reason
            or payload.comment
            or "Rejected by human checkpoint reviewer."
        )
        now = datetime.now(timezone.utc)

        rerun_stage = self._rerun_target_stage(pipeline, stage)
        reject_artifact = self._write_reject_artifact(
            checkpoint=checkpoint,
            rejected_stage=stage,
            rerun_stage=rerun_stage,
            reason=reason,
            payload=payload,
        )

        checkpoint.status = "rejected"
        checkpoint.reviewer = payload.reviewer
        checkpoint.comment = payload.comment
        checkpoint.reason = reason
        checkpoint.reject_reason = reason
        checkpoint.decided_at = now
        checkpoint.rerun_stage_id = rerun_stage.id
        checkpoint.reject_artifact = reject_artifact
        checkpoint.artifact_refs = self._append_artifact(checkpoint.artifact_refs, reject_artifact)

        stage.status = "rejected"
        stage.logs = [
            *stage.logs,
            f"Checkpoint rejected by {payload.reviewer or 'human'}: {reason}",
        ]

        self._mark_stage_for_rerun(rerun_stage, reject_artifact, stage.id)
        self._mark_run_for_rerun(pipeline, checkpoint, reject_artifact, rerun_stage.id)

        pipeline.status = "rejected"
        self._save(checkpoint)
        return self.store.save(pipeline)

    def approve_stage(
        self,
        pipeline_id: str,
        stage_id: str,
        payload: CheckpointDecisionRequest,
    ) -> PipelineRecord:
        pipeline = self.store.get(pipeline_id)
        stage = self._stage(pipeline, stage_id)
        checkpoint = self._find_or_create_stage_checkpoint(pipeline, stage)
        return self.approve(checkpoint.id, payload)

    def reject_stage(
        self,
        pipeline_id: str,
        stage_id: str,
        payload: CheckpointDecisionRequest,
    ) -> PipelineRecord:
        pipeline = self.store.get(pipeline_id)
        stage = self._stage(pipeline, stage_id)
        checkpoint = self._find_or_create_stage_checkpoint(pipeline, stage)
        return self.reject(checkpoint.id, payload)

    def build_checkpoint_id(self, pipeline_id: str, stage_id: str, run_id: str | None = None) -> str:
        if run_id:
            return f"{pipeline_id}:{run_id}:{stage_id}"
        return f"{pipeline_id}:{stage_id}"

    def _find_or_create_stage_checkpoint(
        self,
        pipeline: PipelineRecord,
        stage: StageRecord,
    ) -> CheckpointRecord:
        existing = self._find_latest_for_stage(pipeline.id, stage.id, status="pending")
        if existing is not None:
            return existing
        return self.create_or_update_pending_checkpoint(pipeline, stage)

    def _current_pending_stage(self, pipeline: PipelineRecord) -> StageRecord | None:
        for stage in pipeline.stages:
            if stage.status == "pending_approval":
                return stage
        return None

    def _stage(self, pipeline: PipelineRecord, stage_id: str) -> StageRecord:
        for stage in pipeline.stages:
            if stage.id == stage_id:
                return stage
        raise KeyError(stage_id)

    def _rerun_target_stage(self, pipeline: PipelineRecord, stage: StageRecord) -> StageRecord:
        dependency_ids = self._dependency_ids(stage.id)
        for dependency_id in reversed(dependency_ids):
            try:
                return self._stage(pipeline, dependency_id)
            except KeyError:
                continue

        for index, candidate in enumerate(pipeline.stages):
            if candidate.id == stage.id and index > 0:
                return pipeline.stages[index - 1]
        return stage

    def _dependency_ids(self, stage_id: str) -> list[str]:
        registry = self.registry or getattr(self.pipeline_service, "registry", None)
        if registry is None:
            return []
        try:
            return list(getattr(registry.get(stage_id), "depends_on", ()) or ())
        except Exception:
            return []

    def _mark_stage_for_rerun(
        self,
        stage: StageRecord,
        reject_artifact: ArtifactRef,
        rejected_stage_id: str,
    ) -> None:
        data = dict(stage.data)
        if stage.output_artifacts:
            data["previous_output_artifacts"] = [
                artifact.model_dump(mode="json") for artifact in stage.output_artifacts
            ]
        rerun_inputs = list(data.get("rerun_input_artifacts") or [])
        reject_payload = reject_artifact.model_dump(mode="json")
        if not any(item.get("name") == reject_artifact.name and item.get("path") == reject_artifact.path for item in rerun_inputs if isinstance(item, dict)):
            rerun_inputs.append(reject_payload)
        data["rerun_required"] = True
        data["rerun_rejected_stage_id"] = rejected_stage_id
        data["rerun_input_artifacts"] = rerun_inputs

        stage.status = "queued"
        stage.output_artifacts = []
        stage.data = data
        stage.error = None
        stage.logs = [
            *stage.logs,
            f"Queued for rerun after checkpoint rejection of {rejected_stage_id}",
        ]

    def _mark_run_for_rerun(
        self,
        pipeline: PipelineRecord,
        checkpoint: CheckpointRecord,
        reject_artifact: ArtifactRef,
        rerun_stage_id: str,
    ) -> None:
        if self.run_store is None:
            return
        run_id = checkpoint.run_id or pipeline.latest_run_id
        if not run_id:
            return
        try:
            run = self.run_store.get(pipeline.id, run_id)
        except Exception:
            return

        run.rejected_stage_id = checkpoint.stage_id
        run.next_stage_id = rerun_stage_id
        pending = dict(getattr(run, "pending_input_artifacts_by_stage", {}) or {})
        pending_refs = list(pending.get(rerun_stage_id) or [])
        if not any(ref.name == reject_artifact.name and ref.path == reject_artifact.path for ref in pending_refs):
            pending_refs.append(reject_artifact)
        pending[rerun_stage_id] = pending_refs
        run.pending_input_artifacts_by_stage = pending

        if rerun_stage_id in run.stage_order:
            rerun_index = run.stage_order.index(rerun_stage_id)
            rerun_and_downstream = set(run.stage_order[rerun_index:])
            run.completed_stage_ids = [
                stage_id for stage_id in run.completed_stage_ids if stage_id not in rerun_and_downstream
            ]
            run.artifact_refs_by_stage = {
                stage_id: refs
                for stage_id, refs in run.artifact_refs_by_stage.items()
                if stage_id not in rerun_and_downstream
            }
        if run.status not in {"terminated", "succeeded"}:
            run.status = "rejected"
            run.ended_at = datetime.now(timezone.utc)
        run.logs = [
            *run.logs,
            f"Checkpoint {checkpoint.id} rejected; rerun required from {rerun_stage_id}",
        ]
        self.run_store.save(run)

    def _attach_checkpoint_to_run(
        self,
        pipeline: PipelineRecord,
        checkpoint: CheckpointRecord,
    ) -> None:
        if self.run_store is None or not checkpoint.run_id:
            return
        try:
            run = self.run_store.get(pipeline.id, checkpoint.run_id)
        except Exception:
            return
        if checkpoint.id not in run.checkpoint_ids:
            run.checkpoint_ids.append(checkpoint.id)
            self.run_store.save(run)

    def _write_reject_artifact(
        self,
        *,
        checkpoint: CheckpointRecord,
        rejected_stage: StageRecord,
        rerun_stage: StageRecord,
        reason: str,
        payload: CheckpointDecisionRequest,
    ) -> ArtifactRef:
        artifact_dir = self.artifacts_root / checkpoint.pipeline_id / "checkpoints" / self._safe(checkpoint.id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        path = artifact_dir / "reject_reason.md"
        lines = [
            "# Checkpoint Rejection",
            "",
            f"- Checkpoint: `{checkpoint.id}`",
            f"- Rejected stage: `{rejected_stage.id}`",
            f"- Rerun stage: `{rerun_stage.id}`",
            f"- Reviewer: {payload.reviewer or 'human'}",
            f"- Decided at: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Reason",
            "",
            reason.strip(),
        ]
        if payload.comment and payload.comment != reason:
            lines.extend(["", "## Comment", "", payload.comment.strip()])
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return ArtifactRef(
            name="reject_reason",
            type="markdown",
            path=str(path),
            role="feedback",
            metadata={
                "checkpoint_id": checkpoint.id,
                "rejected_stage_id": rejected_stage.id,
                "rerun_stage_id": rerun_stage.id,
            },
        )

    def _append_artifact(self, refs: list[ArtifactRef], artifact: ArtifactRef) -> list[ArtifactRef]:
        existing = [ref for ref in refs if not (ref.name == artifact.name and ref.path == artifact.path)]
        return [*existing, artifact]

    def _find_latest_for_stage(
        self,
        pipeline_id: str,
        stage_id: str,
        *,
        status: str | None = None,
    ) -> CheckpointRecord | None:
        checkpoints = []
        for path in self.checkpoints_dir.glob("*.json"):
            try:
                checkpoint = CheckpointRecord.model_validate_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if checkpoint.pipeline_id != pipeline_id or checkpoint.stage_id != stage_id:
                continue
            if status is not None and checkpoint.status != status:
                continue
            checkpoints.append(checkpoint)
        checkpoints.sort(key=lambda item: item.created_at, reverse=True)
        return checkpoints[0] if checkpoints else None

    def _load_optional(self, checkpoint_id: str) -> CheckpointRecord | None:
        path = self._path_for(checkpoint_id)
        if not path.exists():
            return None
        return CheckpointRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def _load(self, checkpoint_id: str) -> CheckpointRecord:
        checkpoint = self._load_optional(checkpoint_id)
        if checkpoint is None:
            raise CheckpointNotFoundError(checkpoint_id)
        return checkpoint

    def _save(self, checkpoint: CheckpointRecord) -> CheckpointRecord:
        checkpoint.pipeline_run_id = checkpoint.run_id
        if checkpoint.reason is None and checkpoint.reject_reason is not None:
            checkpoint.reason = checkpoint.reject_reason
        payload = json.dumps(checkpoint.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
        path = self._path_for(checkpoint.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(path)
        return checkpoint

    def _path_for(self, checkpoint_id: str) -> Path:
        return self.checkpoints_dir / f"{self._safe(checkpoint_id)}.json"

    def _safe(self, value: str) -> str:
        return (
            value.replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace("*", "_")
            .replace("?", "_")
            .replace('"', "_")
            .replace("<", "_")
            .replace(">", "_")
            .replace("|", "_")
        )

    def _derive_status(self, pipeline: PipelineRecord) -> PipelineStatus:
        statuses = [stage.status for stage in pipeline.stages]
        if any(status == "failed" for status in statuses):
            return "failed"
        if any(status == "rejected" for status in statuses):
            return "rejected"
        if any(status == "cancelled" for status in statuses):
            return "cancelled"
        if any(status == "pending_approval" for status in statuses):
            return "pending_approval"
        if any(status == "running" for status in statuses):
            return "running"
        if all(status in {"succeeded", "skipped"} for status in statuses):
            return "succeeded"
        return "queued"
