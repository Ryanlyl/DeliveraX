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
  queued: "待执行",
  running: "运行中",
  succeeded: "已完成",
  failed: "失败",
  pending_approval: "等待审核",
  rejected: "已拒绝",
  cancelled: "已取消",
  paused: "已暂停",
  terminated: "已终止",
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
  const isTerminal = status === "succeeded" || status === "failed" || status === "terminated" || status === "cancelled" || status === "rejected";
  const isRunning = status === "running";
  const isPaused = status === "paused";
  const isQueued = status === "queued";

  return (
    <header className="pipeline-header">
      <div className="pipeline-nav-area">
        <a href="/dashboard" className="pipeline-back">← 返回工作台</a>
        <span>DeliveraX</span>
      </div>
      <div className="pipeline-status-area">
        <h1>{pipelineName}</h1>
        <span className="pipeline-meta-id">ID: {pipelineId}</span>
        {runId && <span className="pipeline-meta-run">Run: {runId}</span>}
        <span className={`status-pill ${status}`}>{statusLabel[status] || status}</span>
        <span>模型：{modelLabel}</span>
        <span>耗时：{totalDuration}</span>
      </div>
      <div className="pipeline-actions">
        <button
          className="button primary"
          type="button"
          disabled={!isQueued}
          onClick={onStart}
        >
          启动
        </button>
        <button
          className="button ghost"
          type="button"
          disabled={!isRunning}
          onClick={onPause}
        >
          暂停
        </button>
        <button
          className="button ghost"
          type="button"
          disabled={!isPaused}
          onClick={onResume}
        >
          继续
        </button>
        <button
          className="button danger"
          type="button"
          disabled={isTerminal}
          onClick={onTerminate}
        >
          终止
        </button>
      </div>
    </header>
  );
}
