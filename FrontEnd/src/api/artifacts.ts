import { apiRequest } from "./client";
import type { ArtifactListResponse, ArtifactTextResponse } from "../types/pipeline";

export function listStageArtifacts(pipelineId: string, stageId: string) {
  return apiRequest<ArtifactListResponse>(
    `/api/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/artifacts`,
  );
}

export function readArtifactFile(path: string) {
  return apiRequest<ArtifactTextResponse>(`/api/artifacts/file?path=${encodeURIComponent(path)}`);
}
