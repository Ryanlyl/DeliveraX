// ── Types (mirror of server/api_server/schemas.py and engine/models.py) ──

export type PipelineStatus =
  | "queued"
  | "running"
  | "paused"
  | "pending_approval"
  | "succeeded"
  | "failed"
  | "rejected"
  | "cancelled"
  | "terminated";

export type StageStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "pending_approval"
  | "rejected"
  | "cancelled"
  | "skipped";

export interface ArtifactRef {
  name: string;
  type: string;
  path: string;
  role?: string;
}

export interface StageError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface LLMSelection {
  provider?: string | null;
  model?: string | null;
  temperature?: number | null;
  local_only?: boolean | null;
  use_real_llm?: boolean | null;
  options: Record<string, unknown>;
}

export interface StageRecord {
  id: string;
  name: string;
  agent: string;
  status: StageStatus;
  checkpoint: boolean;
  checkpoint_label?: string | null;
  checkpoint_description?: string | null;
  run_id?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  duration_ms: number;
  input_artifacts: ArtifactRef[];
  output_artifacts: ArtifactRef[];
  human_output?: string | null;
  data: Record<string, unknown>;
  logs: string[];
  error?: StageError | null;
}

export interface PipelineRecord {
  id: string;
  name: string;
  status: PipelineStatus;
  project_id?: string | null;
  provider: string;
  model?: string | null;
  temperature?: number | null;
  stage_overrides: Record<string, LLMSelection>;
  requirement: string;
  repo_path?: string | null;
  created_at: string;
  updated_at: string;
  options: Record<string, unknown>;
  latest_run_id?: string | null;
  stages: StageRecord[];
}

export interface PipelineRun {
  id: string;
  pipeline_id: string;
  pipeline_definition_id?: string | null;
  status: string;
  stage_order: string[];
  current_stage_id?: string | null;
  next_stage_id?: string | null;
  completed_stage_ids: string[];
  failed_stage_id?: string | null;
  rejected_stage_id?: string | null;
  pause_requested: boolean;
  terminate_requested: boolean;
  artifact_refs_by_stage: Record<string, ArtifactRef[]>;
  pending_input_artifacts_by_stage: Record<string, ArtifactRef[]>;
  checkpoint_ids: string[];
  error?: StageError | null;
  logs: string[];
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  ended_at?: string | null;
}

export type CheckpointStatus = "pending" | "approved" | "rejected";

export interface CheckpointRecord {
  id: string;
  pipeline_id: string;
  run_id?: string | null;
  pipeline_run_id?: string | null;
  stage_id: string;
  status: CheckpointStatus;
  title: string;
  description?: string | null;
  reviewer?: string | null;
  comment?: string | null;
  reason?: string | null;
  reject_reason?: string | null;
  artifact_refs: ArtifactRef[];
  created_at: string;
  decided_at?: string | null;
  rerun_stage_id?: string | null;
  reject_artifact?: ArtifactRef | null;
}

export interface CurrentCheckpointResponse {
  pipeline_id: string;
  run_id?: string | null;
  checkpoint?: CheckpointRecord | null;
  stage?: StageRecord | null;
  artifacts: ArtifactRef[];
  human_output?: string | null;
}

export interface ReviewAssetItem {
  path?: string | null;
  content?: string | null;
}

export interface ReviewAssetsResponse {
  pipeline_id: string;
  stage_id: string;
  human_output?: ReviewAssetItem | null;
  diff?: ReviewAssetItem | null;
  review_report?: ReviewAssetItem | null;
  artifacts: ArtifactRef[];
}

export interface ProviderInfo {
  id: string;
  name: string;
  kind: string;
  default_model?: string | null;
  default_base_url?: string | null;
  api_key_env?: string | null;
  available: boolean;
  configured: boolean;
  notes?: string | null;
  models: string[];
}

// ── Stage definition (GET /api/stages) ──

export interface StageDefinition {
  id: string;
  name: string;
  agent: string;
  checkpoint: boolean;
  description?: string | null;
  available: boolean;
}

// ── Project types ──

export type CloneStatus = "pending" | "cloning" | "ready" | "failed";

export interface ProjectRecord {
  id: string;
  name: string;
  description?: string | null;
  github_url: string;
  clone_status: CloneStatus;
  clone_path?: string | null;
  clone_error?: string | null;
  created_at: string;
  updated_at: string;
  pipeline_ids: string[];
}

export interface ProjectCreateRequest {
  name: string;
  description?: string | null;
  github_url: string;
}

// ── Artifact response types ──

export interface ArtifactListResponse {
  pipeline_id: string;
  stage_id: string;
  artifacts: ArtifactRef[];
  standard_artifacts: Record<string, string | null>;
}

export interface ArtifactTextResponse {
  path: string;
  content: string;
}

// ── Request bodies ──

export interface PipelineCreateRequest {
  name?: string;
  requirement: string;
  pipeline_id?: string | null;
  project_id?: string | null;
  provider?: string;
  model?: string | null;
  temperature?: number | null;
  stage_overrides?: Record<string, LLMSelection>;
  repo_path?: string | null;
  options?: Record<string, unknown>;
}

export interface PipelineRunInput {
  start_stage_id?: string | null;
  repo_path?: string | null;
  options?: Record<string, unknown>;
}

export interface CheckpointDecisionRequest {
  reviewer?: string | null;
  comment?: string | null;
  reason?: string | null;
  continue_pipeline?: boolean;
}

export interface ApprovalRequest {
  reviewer?: string | null;
  comment?: string | null;
  reason?: string | null;
  continue_pipeline?: boolean;
}

export interface StageRunInput {
  run_id?: string | null;
  input_artifacts?: ArtifactRef[];
  repo_path?: string | null;
  options?: Record<string, unknown>;
}

// ── API helpers ──

const API_BASE = "/api";

class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function extractErrorMessage(detail: unknown, fallback: string): string {
  if (!detail) return fallback;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg?: unknown }).msg ?? "");
        }
        return "";
      })
      .filter(Boolean);

    return messages.length > 0 ? messages.join("; ") : fallback;
  }

  if (typeof detail === "object") {
    const obj = detail as Record<string, unknown>;

    if (typeof obj.message === "string") return obj.message;
    if (typeof obj.error === "string") return obj.error;

    if (typeof obj.detail === "string") return obj.detail;

    if (obj.detail && typeof obj.detail === "object") {
      const nested = obj.detail as Record<string, unknown>;
      if (typeof nested.message === "string") return nested.message;
      if (typeof nested.error === "string") return nested.error;
    }

    if (Array.isArray(obj.detail)) {
      return extractErrorMessage(obj.detail, fallback);
    }
  }

  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    let detail: unknown;
    try {
      detail = await res.json();
    } catch {
      // ignore parse failures
    }
    const fallback = `API ${res.status}: ${res.statusText}`;
    throw new ApiError(res.status, extractErrorMessage(detail, fallback), detail);
  }
  return res.json() as Promise<T>;
}

// ── Health ──
// Note: /health is at root, not under /api, so we fetch directly.

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch("/health");
  if (!res.ok) {
    let detail: unknown;
    try {
      detail = await res.json();
    } catch {
      // ignore parse failures
    }
    const fallback = `API ${res.status}: ${res.statusText}`;
    throw new ApiError(res.status, extractErrorMessage(detail, fallback), detail);
  }
  return res.json() as Promise<{ status: string }>;
}

// ── Stage definition endpoints ──

export function listStages(): Promise<StageDefinition[]> {
  return request<StageDefinition[]>("/stages");
}

// ── Provider endpoints ──

export function listProviders(): Promise<ProviderInfo[]> {
  return request<ProviderInfo[]>("/providers");
}

// ── Project endpoints ──

export function listProjects(): Promise<ProjectRecord[]> {
  return request<ProjectRecord[]>("/projects");
}

export function createProject(req: ProjectCreateRequest): Promise<ProjectRecord> {
  return request<ProjectRecord>("/projects", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function getProject(id: string): Promise<ProjectRecord> {
  return request<ProjectRecord>(`/projects/${encodeURIComponent(id)}`);
}

export function deleteProject(id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/projects/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

// ── Pipeline endpoints ──

export function createPipeline(req: PipelineCreateRequest): Promise<PipelineRecord> {
  return request<PipelineRecord>("/pipelines", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function listPipelines(projectId?: string | null): Promise<PipelineRecord[]> {
  const params = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<PipelineRecord[]>(`/pipelines${params}`);
}

export function getPipeline(id: string): Promise<PipelineRecord> {
  return request<PipelineRecord>(`/pipelines/${encodeURIComponent(id)}`);
}

export function runPipeline(id: string, input: PipelineRunInput = {}): Promise<PipelineRecord> {
  return request<PipelineRecord>(`/pipelines/${encodeURIComponent(id)}/run`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function startPipeline(id: string, input: PipelineRunInput = {}): Promise<PipelineRun> {
  return request<PipelineRun>(`/pipelines/${encodeURIComponent(id)}/start`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getRun(pipelineId: string, runId: string): Promise<PipelineRun> {
  return request<PipelineRun>(
    `/pipelines/${encodeURIComponent(pipelineId)}/runs/${encodeURIComponent(runId)}`,
  );
}

export function pausePipeline(pipelineId: string, runId?: string): Promise<PipelineRun> {
  const params = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return request<PipelineRun>(`/pipelines/${encodeURIComponent(pipelineId)}/pause${params}`, {
    method: "POST",
  });
}

export function resumePipeline(pipelineId: string, runId?: string): Promise<PipelineRun> {
  const params = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return request<PipelineRun>(`/pipelines/${encodeURIComponent(pipelineId)}/resume${params}`, {
    method: "POST",
  });
}

export function terminatePipeline(pipelineId: string, runId?: string): Promise<PipelineRun> {
  const params = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return request<PipelineRun>(`/pipelines/${encodeURIComponent(pipelineId)}/terminate${params}`, {
    method: "POST",
  });
}

// ── Stage detail / actions ──

export function getStage(
  pipelineId: string,
  stageId: string,
): Promise<StageRecord> {
  return request<StageRecord>(
    `/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}`,
  );
}

export function runStage(
  pipelineId: string,
  stageId: string,
  input: StageRunInput = {},
): Promise<PipelineRecord> {
  return request<PipelineRecord>(
    `/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/run`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function approveStage(
  pipelineId: string,
  stageId: string,
  payload: ApprovalRequest = {},
): Promise<PipelineRecord> {
  return request<PipelineRecord>(
    `/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/approve`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function rejectStage(
  pipelineId: string,
  stageId: string,
  payload: ApprovalRequest,
): Promise<PipelineRecord> {
  return request<PipelineRecord>(
    `/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/reject`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

// ── Checkpoint endpoints ──

export function getCurrentCheckpoint(pipelineId: string): Promise<CurrentCheckpointResponse> {
  return request<CurrentCheckpointResponse>(
    `/pipelines/${encodeURIComponent(pipelineId)}/checkpoints/current`,
  );
}

export function approveCheckpoint(
  checkpointId: string,
  payload: CheckpointDecisionRequest,
): Promise<PipelineRecord> {
  return request<PipelineRecord>(`/checkpoints/${encodeURIComponent(checkpointId)}/approve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rejectCheckpoint(
  checkpointId: string,
  payload: CheckpointDecisionRequest,
): Promise<PipelineRecord> {
  return request<PipelineRecord>(`/checkpoints/${encodeURIComponent(checkpointId)}/reject`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Artifact / review-assets endpoints ──

export function getStageArtifacts(
  pipelineId: string,
  stageId: string,
): Promise<ArtifactListResponse> {
  return request<ArtifactListResponse>(
    `/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/artifacts`,
  );
}

export function getStageReviewAssets(
  pipelineId: string,
  stageId: string,
): Promise<ReviewAssetsResponse> {
  return request<ReviewAssetsResponse>(
    `/pipelines/${encodeURIComponent(pipelineId)}/stages/${encodeURIComponent(stageId)}/review-assets`,
  );
}

export function readArtifactFile(path: string): Promise<ArtifactTextResponse> {
  const params = `?path=${encodeURIComponent(path)}`;
  return request<ArtifactTextResponse>(`/artifacts/file${params}`);
}

// ── Polling helper ──

const TERMINAL_STATUSES: PipelineStatus[] = [
  "succeeded",
  "failed",
  "rejected",
  "cancelled",
  "terminated",
];

export function isTerminal(status: PipelineStatus): boolean {
  return TERMINAL_STATUSES.includes(status);
}

export function pollUntilTerminal(
  fetchFn: () => Promise<PipelineRecord>,
  onUpdate: (record: PipelineRecord) => void,
  intervalMs = 1000,
): () => void {
  let active = true;

  async function tick() {
    if (!active) return;
    try {
      const record = await fetchFn();
      if (!active) return;
      onUpdate(record);
      if (!isTerminal(record.status)) {
        setTimeout(tick, intervalMs);
      }
    } catch {
      if (active) setTimeout(tick, intervalMs);
    }
  }

  tick();

  return () => {
    active = false;
  };
}

// ── Unified API export ──

export const Api = {
  // health
  healthCheck,

  // stages
  listStages,

  // providers
  listProviders,

  // projects
  listProjects,
  createProject,
  getProject,
  deleteProject,

  // pipelines
  listPipelines,
  createPipeline,
  getPipeline,
  runPipeline,
  startPipeline,
  pausePipeline,
  resumePipeline,
  terminatePipeline,
  getRun,

  // stage detail & actions
  getStage,
  runStage,
  approveStage,
  rejectStage,

  // checkpoints
  getCurrentCheckpoint,
  approveCheckpoint,
  rejectCheckpoint,

  // artifacts & review
  getStageArtifacts,
  getStageReviewAssets,
  readArtifactFile,

  // polling
  pollUntilTerminal,
  isTerminal,
};
