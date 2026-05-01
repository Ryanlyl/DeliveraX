export type StageStatus = "waiting" | "running" | "success" | "failed" | "pending_review";

export type PipelineStatus = "Running" | "Waiting for Review" | "Completed";

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

export type Pipeline = {
  id: string;
  name: string;
  status: PipelineStatus;
  provider: LLMProvider;
  totalDuration: string;
  requirement: string;
  stages: Stage[];
};
