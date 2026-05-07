import type { StageRecord } from "../api/client";

type Props = {
  stages: StageRecord[];
  activeStageId: string;
  selectedStageId: string;
  onSelectStage: (stageId: string) => void;
};

const statusLabel: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  pending_approval: "Pending approval",
  rejected: "Rejected",
  cancelled: "Cancelled",
  skipped: "Skipped",
};

function statusGlyph(status: string): string {
  if (status === "succeeded") return "✓";
  if (status === "running") return "●";
  if (status === "failed") return "✕";
  if (status === "pending_approval") return "!";
  if (status === "rejected") return "✕";
  if (status === "cancelled") return "○";
  if (status === "skipped") return "○";
  return "○";
}

export default function PipelineCanvas({ stages, activeStageId, selectedStageId, onSelectStage }: Props) {
  if (!stages || stages.length === 0) {
    return (
      <div className="pipeline-canvas">
        <p className="canvas-empty">No stage data available.</p>
      </div>
    );
  }

  return (
    <div className="pipeline-canvas">
      <div className="canvas-flow">
        {stages.map((stage, index) => {
          const isActive = stage.id === activeStageId;
          const isSelected = stage.id === selectedStageId;
          const isQueued = stage.status === "queued";

          return (
            <div key={stage.id} className="canvas-stage-group">
              {index > 0 && (
                <div className={`canvas-connector ${isActive ? "active" : ""}`} aria-hidden="true">
                  <svg width="24" height="14" viewBox="0 0 24 14" fill="none">
                    <line
                      x1="0"
                      y1="7"
                      x2="18"
                      y2="7"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeDasharray={isActive ? "0" : "4 3"}
                    />
                    <polygon points="18,2 24,7 18,12" fill="currentColor" />
                  </svg>
                </div>
              )}

              <button
                className={`canvas-node ${isActive ? "active" : ""} ${isSelected ? "selected" : ""} ${
                  isQueued ? "queued" : ""
                } status-${stage.status}`}
                type="button"
                onClick={() => !isQueued && onSelectStage(stage.id)}
                disabled={isQueued}
                aria-current={isActive ? "step" : undefined}
              >
                <span className="canvas-node-icon" aria-hidden="true">
                  {statusGlyph(stage.status)}
                </span>
                <div className="canvas-node-body">
                  <span className="canvas-node-name">{stage.name}</span>
                  <span className="canvas-node-agent">{stage.agent}</span>
                </div>
                <div className="canvas-node-meta">
                  <span className={`canvas-status-badge ${stage.status}`}>
                    {statusLabel[stage.status] || stage.status}
                  </span>
                </div>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
