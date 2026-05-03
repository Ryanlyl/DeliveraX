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
  | "pending_approval"
  | "succeeded"
  | "failed"
  | "rejected"
  | "cancelled";

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
  requirement: string;
  repo_path?: string | null;
  created_at: string;
  updated_at: string;
  options: Record<string, unknown>;
  stages: StageRecord[];
};

export type PipelineCreateRequest = {
  name?: string;
  requirement: string;
  pipeline_id?: string | null;
  provider?: string;
  repo_path?: string | null;
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
export type LLMProvider = string;
