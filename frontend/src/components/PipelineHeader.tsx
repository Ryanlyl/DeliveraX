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
  queued: "待开始",
  running: "运行中",
  succeeded: "已完成",
  failed: "失败",
  pending_approval: "待审批",
  rejected: "已驳回",
  cancelled: "已取消",
  paused: "已暂停",
  terminated: "已终止",
};

export default function PipelineHeader({
  status,
  totalDuration,
  onStart,
  onPause,
  onResume,
  onTerminate,
}: Props) {
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
          <span className="pipeline-back-arrow" aria-hidden="true">←</span>
          <span>返回看板</span>
        </a>
        <span className="pipeline-product-tag">交付平台</span>
      </div>

      <div className="pipeline-status-area">
        <div className="pipeline-meta-chips">
          <span className={`status-pill ${status}`}>{statusLabel[status] || status}</span>
          <span className="meta-chip">耗时：{totalDuration}</span>
        </div>
      </div>

      <div className="pipeline-actions">
        <button className="button primary action-start" type="button" disabled={!isQueued} onClick={onStart}>
          开始
        </button>
        <button className="button ghost action-pause" type="button" disabled={!isRunning} onClick={onPause}>
          暂停
        </button>
        <button className="button ghost action-resume" type="button" disabled={!isPaused} onClick={onResume}>
          恢复
        </button>
        <button className="button danger action-terminate" type="button" disabled={isTerminal} onClick={onTerminate}>
          终止
        </button>
      </div>
    </header>
  );
}
