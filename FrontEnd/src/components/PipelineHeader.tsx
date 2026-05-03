import type { LLMProvider, PipelineStatus } from "../types/pipeline";

type Props = {
  status: PipelineStatus;
  totalDuration: string;
  model: LLMProvider;
};

const statusLabel: Record<PipelineStatus, string> = {
  queued: "Queued",
  running: "Running",
  pending_approval: "Waiting for Review",
  succeeded: "Completed",
  failed: "Failed",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

export default function PipelineHeader({ status, totalDuration, model }: Props) {
  return (
    <header className="pipeline-header">
      <div>
        <span className="eyebrow">DeliveraX / DevFlow Engine</span>
        <h1>AI DevFlow Pipeline</h1>
      </div>
      <div className="pipeline-meta">
        <span className={`status-pill ${status}`}>{statusLabel[status]}</span>
        <span>LLM Provider: {model}</span>
        <span>总耗时: {totalDuration}</span>
      </div>
      <div className="pipeline-actions">
        <button className="button ghost" type="button">Pause</button>
        <button className="button ghost" type="button">Resume</button>
        <button className="button danger" type="button">Terminate</button>
      </div>
    </header>
  );
}
