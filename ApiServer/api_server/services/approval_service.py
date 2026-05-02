from __future__ import annotations

from api_server.schemas import ApprovalRequest, PipelineRecord, StageRecord
from api_server.storage.json_store import JsonPipelineStore


class ApprovalService:
    def __init__(self, store: JsonPipelineStore) -> None:
        self.store = store

    def approve(self, pipeline_id: str, stage_id: str, approval: ApprovalRequest) -> PipelineRecord:
        pipeline = self.store.get(pipeline_id)
        stage = self._stage(pipeline, stage_id)
        stage.status = "succeeded"
        stage.logs = [
            *stage.logs,
            f"Approved by {approval.reviewer or 'human'}" + (f": {approval.comment}" if approval.comment else ""),
        ]
        pipeline.status = self._derive_status(pipeline)
        return self.store.save(pipeline)

    def reject(self, pipeline_id: str, stage_id: str, approval: ApprovalRequest) -> PipelineRecord:
        pipeline = self.store.get(pipeline_id)
        stage = self._stage(pipeline, stage_id)
        stage.status = "rejected"
        stage.logs = [
            *stage.logs,
            f"Rejected by {approval.reviewer or 'human'}" + (f": {approval.comment}" if approval.comment else ""),
        ]
        pipeline.status = "rejected"
        return self.store.save(pipeline)

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
