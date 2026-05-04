import type { PipelineStatus } from "../types/pipeline";

type Props = {
  status: PipelineStatus;
  totalDuration: string;
  model: string;
};

const statusLabel: Record<PipelineStatus, string> = {
  queued: "Queued",
  running: "Running",
  paused: "Paused",
  pending_approval: "Waiting for Review",
  succeeded: "Completed",
  failed: "Failed",
  rejected: "Rejected",
  cancelled: "Cancelled",
  terminated: "Terminated",
};

export default function PipelineHeader({ status, totalDuration, model }: Props) {
  return (
    <header className="pipeline-header">
      <div>
        <span className="eyebrow">DeliveraX / DevFlow Engine</span>
        <h1>AI DevFlow Pipeline</h1>
      </div>
      <div className="pipeline-meta">
        <span className={`status-pill ${status}`}>{statusLabel[status] ?? status}</span>
        <span>LLM: {model}</span>
        <span>总耗时: {totalDuration}</span>
      </div>
    </header>
  );
}
