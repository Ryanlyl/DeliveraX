from __future__ import annotations

from api_server.schemas import ApprovalRequest, CheckpointDecisionRequest, PipelineRecord, StageRecord
from api_server.services.checkpoint_service import CheckpointService
from api_server.storage.json_store import JsonPipelineStore


class ApprovalService:
    def __init__(self, store: JsonPipelineStore, checkpoint_service: CheckpointService | None = None) -> None:
        self.store = store
        self.checkpoint_service = checkpoint_service

    def approve(self, pipeline_id: str, stage_id: str, approval: ApprovalRequest) -> PipelineRecord:
        return self._checkpoint_service().approve_stage(
            pipeline_id,
            stage_id,
            self._decision_payload(approval),
        )

    def reject(self, pipeline_id: str, stage_id: str, approval: ApprovalRequest) -> PipelineRecord:
        return self._checkpoint_service().reject_stage(
            pipeline_id,
            stage_id,
            self._decision_payload(approval),
        )

    def _checkpoint_service(self) -> CheckpointService:
        if self.checkpoint_service is None:
            self.checkpoint_service = CheckpointService(
                store=self.store,
                artifacts_root=self.store.root,
            )
        return self.checkpoint_service

    def _decision_payload(self, approval: ApprovalRequest) -> CheckpointDecisionRequest:
        return CheckpointDecisionRequest(
            reviewer=approval.reviewer,
            comment=approval.comment,
            reason=approval.reason or approval.comment,
            continue_pipeline=approval.continue_pipeline,
        )

    def _stage(self, pipeline: PipelineRecord, stage_id: str) -> StageRecord:
        for stage in pipeline.stages:
            if stage.id == stage_id:
                return stage
        raise KeyError(stage_id)

    def _derive_status(self, pipeline: PipelineRecord) -> str:
        statuses = [stage.status for stage in pipeline.stages]
        if any(status == "failed" for status in statuses):
            return "failed"
        if any(status == "pending_approval" for status in statuses):
            return "pending_approval"
        if any(status == "running" for status in statuses):
            return "running"
        if all(status in {"succeeded", "skipped"} for status in statuses):
            return "succeeded"
        return "queued"
