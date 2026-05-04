import { apiRequest } from "./client";
import type { ArtifactListResponse, ArtifactTextResponse, ReviewAssetsResponse } from "../types/pipeline";

export function listStageArtifacts(pipelineId: string, stageId: string) {
  return apiRequest<ArtifactListResponse>(
    `/api/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/artifacts`,
  );
}

export function readArtifactFile(path: string) {
  return apiRequest<ArtifactTextResponse>(`/api/artifacts/file?path=${encodeURIComponent(path)}`);
}

export function getStageReviewAssets(pipelineId: string, stageId: string) {
  return apiRequest<ReviewAssetsResponse>(
    `/api/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/review-assets`,
  );
}
