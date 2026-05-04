import { apiRequest } from "./client";
import type {
  ApprovalRequest,
  CheckpointDecisionRequest,
  CurrentCheckpointResponse,
  PipelineCreateRequest,
  PipelineRecord,
  PipelineRun,
  PipelineRunInput,
  StageRunInput,
} from "../types/pipeline";

export function createPipeline(payload: PipelineCreateRequest) {
  return apiRequest<PipelineRecord>("/api/pipelines", {
    method: "POST",
    body: payload,
  });
}

export function listPipelines() {
  return apiRequest<PipelineRecord[]>("/api/pipelines");
}

export function getPipeline(pipelineId: string) {
  return apiRequest<PipelineRecord>(`/api/pipelines/${encodeURIComponent(pipelineId)}`);
}

export function runPipeline(pipelineId: string, payload: PipelineRunInput = {}) {
  return apiRequest<PipelineRecord>(`/api/pipelines/${encodeURIComponent(pipelineId)}/run`, {
    method: "POST",
    body: payload,
  });
}

export function startPipeline(pipelineId: string, payload: PipelineRunInput = {}) {
  return apiRequest<PipelineRun>(`/api/pipelines/${encodeURIComponent(pipelineId)}/start`, {
    method: "POST",
    body: payload,
  });
}

export function pausePipeline(pipelineId: string, runId?: string | null) {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return apiRequest<PipelineRun>(`/api/pipelines/${encodeURIComponent(pipelineId)}/pause${query}`, {
    method: "POST",
  });
}

export function resumePipeline(pipelineId: string, runId?: string | null) {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return apiRequest<PipelineRun>(`/api/pipelines/${encodeURIComponent(pipelineId)}/resume${query}`, {
    method: "POST",
  });
}

export function terminatePipeline(pipelineId: string, runId?: string | null) {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return apiRequest<PipelineRun>(`/api/pipelines/${encodeURIComponent(pipelineId)}/terminate${query}`, {
    method: "POST",
  });
}

export function getPipelineRun(pipelineId: string, runId: string) {
  return apiRequest<PipelineRun>(`/api/pipelines/${encodeURIComponent(pipelineId)}/runs/${encodeURIComponent(runId)}`);
}

export function runStage(pipelineId: string, stageId: string, payload: StageRunInput = {}) {
  return apiRequest<PipelineRecord>(
    `/api/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/run`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export function approveStage(pipelineId: string, stageId: string, payload: ApprovalRequest = {}) {
  return apiRequest<PipelineRecord>(
    `/api/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/approve`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export function rejectStage(pipelineId: string, stageId: string, payload: ApprovalRequest = {}) {
  return apiRequest<PipelineRecord>(
    `/api/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/reject`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export function getCurrentCheckpoint(pipelineId: string) {
  return apiRequest<CurrentCheckpointResponse>(
    `/api/pipelines/${encodeURIComponent(pipelineId)}/checkpoints/current`,
  );
}

export function approveCheckpoint(checkpointId: string, payload: CheckpointDecisionRequest = {}) {
  return apiRequest<PipelineRecord>(`/api/checkpoints/${encodeURIComponent(checkpointId)}/approve`, {
    method: "POST",
    body: payload,
  });
}

export function rejectCheckpoint(checkpointId: string, payload: CheckpointDecisionRequest = {}) {
  return apiRequest<PipelineRecord>(`/api/checkpoints/${encodeURIComponent(checkpointId)}/reject`, {
    method: "POST",
    body: payload,
  });
}
