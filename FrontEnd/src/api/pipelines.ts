import { apiRequest } from "./client";
import type {
  ApprovalRequest,
  PipelineCreateRequest,
  PipelineRecord,
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
