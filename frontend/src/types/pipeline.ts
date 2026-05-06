export type StageStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "pending_approval"
  | "rejected"
  | "cancelled"
  | "skipped";

export type PipelineStatus = "queued" | "running" | "succeeded" | "failed" | "pending_approval" | "rejected" | "cancelled" | "paused" | "terminated";

export type StageTab = "Output" | "Input" | "JSON";

export type LLMProvider = "GPT-4" | "Claude 3";

export type Stage = {
  id: string;
  name: string;
  agent: string;
  status: StageStatus;
  duration: string;
  checkpoint?: boolean;
  checkpointLabel?: string;
  checkpointDescription?: string;
  input: string;
  output: string;
  json: Record<string, unknown>;
  logs: string[];
};

export type Project = {
  id: string;
  name: string;
  description: string | null;
  github_url: string;
  clone_status: "pending" | "cloning" | "ready" | "failed";
  clone_path: string | null;
  created_at: string;
  updated_at: string;
  pipeline_ids: string[];
};

export type Pipeline = {
  id: string;
  name: string;
  status: PipelineStatus;
  provider: LLMProvider;
  totalDuration: string;
  requirement: string;
  stages: Stage[];
};
