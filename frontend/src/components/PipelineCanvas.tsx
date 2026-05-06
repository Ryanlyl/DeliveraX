import type { StageRecord } from "../api/client";

type Props = {
  stages: StageRecord[];
  activeStageId: string;
  selectedStageId: string;
  onSelectStage: (stageId: string) => void;
};

const statusLabel: Record<string, string> = {
  queued: "待执行",
  running: "AI 执行中",
  succeeded: "已完成",
  failed: "执行失败",
  pending_approval: "待审核",
  rejected: "已拒绝",
  cancelled: "已取消",
  skipped: "已跳过",
};

const statusColor: Record<string, string> = {
  queued: "var(--muted)",
  running: "var(--accent)",
  succeeded: "var(--success)",
  failed: "var(--danger)",
  pending_approval: "var(--warning)",
  rejected: "var(--danger)",
  cancelled: "var(--muted)",
  skipped: "var(--muted)",
};

export default function PipelineCanvas({ stages, activeStageId, selectedStageId, onSelectStage }: Props) {
  if (!stages || stages.length === 0) {
    return (
      <div className="pipeline-canvas">
        <div className="canvas-title">
          <span className="eyebrow">Pipeline Flow</span>
          <h2>流程可视化</h2>
        </div>
        <p className="canvas-empty">暂无阶段数据</p>
      </div>
    );
  }

  return (
    <div className="pipeline-canvas">
      <div className="canvas-title">
        <span className="eyebrow">Pipeline Flow</span>
        <h2>流程可视化</h2>
      </div>
      <div className="canvas-flow">
        {stages.map((stage, index) => {
          const isActive = stage.id === activeStageId;
          const isSelected = stage.id === selectedStageId;
          const isQueued = stage.status === "queued";

          return (
            <div key={stage.id} className="canvas-stage-group">
              {index > 0 && (
                <div className={`canvas-connector ${isActive ? "active" : ""}`} aria-hidden="true">
                  <svg width="20" height="24" viewBox="0 0 20 24" fill="none">
                    <line x1="10" y1="0" x2="10" y2="14" stroke="currentColor" strokeWidth="2" strokeDasharray={isActive ? "0" : "4 3"} />
                    <polygon points="4,14 16,14 10,22" fill="currentColor" />
                  </svg>
                </div>
              )}

              <button
                className={`canvas-node ${isActive ? "active" : ""} ${isSelected ? "selected" : ""} ${isQueued ? "queued" : ""} status-${stage.status}`}
                type="button"
                onClick={() => !isQueued && onSelectStage(stage.id)}
                disabled={isQueued}
                aria-current={isActive ? "step" : undefined}
              >
                <span className="canvas-node-icon" aria-hidden="true">
                  {stage.status === "succeeded" && "✓"}
                  {stage.status === "running" && "●"}
                  {stage.status === "failed" && "✕"}
                  {stage.status === "pending_approval" && "?"}
                  {stage.status === "queued" && "○"}
                  {stage.status === "cancelled" && "✕"}
                  {stage.status === "rejected" && "✕"}
                  {stage.status === "skipped" && "○"}
                </span>
                <div className="canvas-node-body">
                  <span className="canvas-node-name">{stage.name}</span>
                  <span className="canvas-node-agent">{stage.agent}</span>
                </div>
                <div className="canvas-node-meta">
                  <span className={`canvas-status-badge ${stage.status}`}>
                    {statusLabel[stage.status] || stage.status}
                  </span>
                  {stage.checkpoint && (
                    <span className="canvas-checkpoint-chip">人工审核</span>
                  )}
                </div>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
