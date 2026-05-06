import type { LLMProvider, PipelineStatus } from "../types/pipeline";

type Props = {
  status: PipelineStatus;
  totalDuration: string;
  model: LLMProvider;
};

const statusLabel: Record<PipelineStatus, string> = {
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

export default function PipelineHeader({ status, totalDuration, model }: Props) {
  return (
    <header className="pipeline-header">
      <div className="pipeline-nav-area">
        <a href="/" className="pipeline-back">← 返回工作台</a>
        <span>DeliveraX</span>
      </div>
      <div className="pipeline-status-area">
        <h1>AI DevFlow Pipeline</h1>
        <span className={`status-pill ${status}`}>{statusLabel[status]}</span>
        <span>模型：{model}</span>
        <span>耗时：{totalDuration}</span>
      </div>
      <div className="pipeline-actions">
        <button className="button ghost" type="button">暂停</button>
        <button className="button ghost" type="button">继续</button>
        <button className="button danger" type="button">终止</button>
      </div>
    </header>
  );
}
