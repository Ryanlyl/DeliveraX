export type StageStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "pending_approval"
  | "rejected"
  | "cancelled"
  | "skipped";

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

export type ArtifactRef = {
  name: string;
  type: string;
  path: string;
  role?: string | null;
  metadata: Record<string, unknown>;
};

export type StageError = {
  code: string;
  message: string;
  details: Record<string, unknown>;
};

export type StageDefinition = {
  id: string;
  name: string;
  agent: string;
  checkpoint: boolean;
  description?: string | null;
  available: boolean;
};

export type StageRecord = {
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
};

export type PipelineRecord = {
  id: string;
  name: string;
  status: PipelineStatus;
  provider: string;
  model?: string | null;
  temperature?: number | null;
  requirement: string;
  repo_path?: string | null;
  created_at: string;
  updated_at: string;
  options: Record<string, unknown>;
  latest_run_id?: string | null;
  stage_overrides?: Record<string, unknown>;
  stages: StageRecord[];
};

export type PipelineCreateRequest = {
  name?: string;
  requirement: string;
  pipeline_id?: string | null;
  provider?: string;
  model?: string | null;
  temperature?: number | null;
  repo_path?: string | null;
  stage_overrides?: Record<string, unknown>;
  options?: Record<string, unknown>;
};

export type PipelineRunInput = {
  start_stage_id?: string | null;
  repo_path?: string | null;
  options?: Record<string, unknown>;
};

export type StageRunInput = {
  run_id?: string | null;
  input_artifacts?: ArtifactRef[];
  repo_path?: string | null;
  options?: Record<string, unknown>;
};

export type ApprovalRequest = {
  reviewer?: string | null;
  comment?: string | null;
  continue_pipeline?: boolean;
};

export type CheckpointStatus = "pending" | "approved" | "rejected";

export type CheckpointRecord = {
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
};

export type CurrentCheckpointResponse = {
  pipeline_id: string;
  run_id?: string | null;
  checkpoint?: CheckpointRecord | null;
  stage?: StageRecord | null;
  artifacts: ArtifactRef[];
  human_output?: string | null;
};

export type CheckpointDecisionRequest = {
  reviewer?: string | null;
  comment?: string | null;
  reason?: string | null;
  continue_pipeline?: boolean;
};

export type ArtifactListResponse = {
  pipeline_id: string;
  stage_id: string;
  artifacts: ArtifactRef[];
  standard_artifacts: Record<string, string | null>;
};

export type ArtifactTextResponse = {
  path: string;
  content: string;
};

export type Stage = StageRecord;
export type Pipeline = PipelineRecord;

export type ProviderDefinition = {
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
};

export type PipelineRun = {
  id: string;
  pipeline_id: string;
  status: string;
  stage_order: string[];
  current_stage_id?: string | null;
  next_stage_id?: string | null;
  completed_stage_ids: string[];
  failed_stage_id?: string | null;
  rejected_stage_id?: string | null;
  pause_requested: boolean;
  terminate_requested: boolean;
  logs: string[];
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  ended_at?: string | null;
};

export type ReviewAssetItem = {
  path?: string | null;
  content?: string | null;
};

export type ReviewAssetsResponse = {
  pipeline_id: string;
  stage_id: string;
  human_output?: ReviewAssetItem | null;
  diff?: ReviewAssetItem | null;
  review_report?: ReviewAssetItem | null;
  artifacts: ArtifactRef[];
};
