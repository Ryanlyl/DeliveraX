import type { PipelineStatus } from "../api/client";

type Props = {
  pipelineName: string;
  pipelineId: string;
  runId?: string | null;
  status: PipelineStatus;
  totalDuration: string;
  model?: string | null;
  provider?: string;
  onStart?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onTerminate?: () => void;
};

const statusLabel: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  pending_approval: "Pending approval",
  rejected: "Rejected",
  cancelled: "Cancelled",
  paused: "Paused",
  terminated: "Terminated",
};

export default function PipelineHeader({
  pipelineName,
  pipelineId,
  runId,
  status,
  totalDuration,
  model,
  provider,
  onStart,
  onPause,
  onResume,
  onTerminate,
}: Props) {
  const modelLabel = model || provider || "local";
  const isTerminal =
    status === "succeeded" ||
    status === "failed" ||
    status === "terminated" ||
    status === "cancelled" ||
    status === "rejected";
  const isRunning = status === "running";
  const isPaused = status === "paused";
  const isQueued = status === "queued";

  return (
    <header className="pipeline-header pipeline-header-modern">
      <div className="pipeline-nav-area">
        <a href="/dashboard" className="pipeline-back">
          ← Back to Dashboard
        </a>
        <span>DeliveraX</span>
      </div>

      <div className="pipeline-status-area">
        <h1>{pipelineName}</h1>
        <div className="pipeline-meta-chips">
          <span className="meta-chip">Pipeline: {pipelineId}</span>
          {runId && <span className="meta-chip">Run: {runId}</span>}
          <span className={`status-pill ${status}`}>{statusLabel[status] || status}</span>
          <span className="meta-chip">Model: {modelLabel}</span>
          <span className="meta-chip">Duration: {totalDuration}</span>
        </div>
      </div>

      <div className="pipeline-actions">
        <button className="button primary" type="button" disabled={!isQueued} onClick={onStart}>
          Start
        </button>
        <button className="button ghost" type="button" disabled={!isRunning} onClick={onPause}>
          Pause
        </button>
        <button className="button ghost" type="button" disabled={!isPaused} onClick={onResume}>
          Resume
        </button>
        <button className="button danger" type="button" disabled={isTerminal} onClick={onTerminate}>
          Terminate
        </button>
      </div>
    </header>
  );
}
