import type { Stage } from "../types/pipeline";

type Props = {
  stage: Stage;
  active: boolean;
  selected: boolean;
  disabled: boolean;
  isLast: boolean;
  onSelect: () => void;
};

const statusLabel: Record<Stage["status"], string> = {
  waiting: "待执行",
  running: "执行中",
  success: "已完成",
  failed: "执行失败",
  pending_review: "已完成（待审核）",
};

const statusIcon: Record<Stage["status"], string> = {
  waiting: "⏳",
  running: "●",
  success: "✔",
  failed: "!",
  pending_review: "✔",
};

export default function StageCard({ stage, active, selected, disabled, isLast, onSelect }: Props) {
  const isCheckpointPending = stage.checkpoint && stage.status === "pending_review";
  const shouldShowDuration = stage.status !== "waiting" && stage.duration !== "0.0s";

  return (
    <button
      className={`stage-card ${active ? "active" : ""} ${selected ? "selected" : ""} ${disabled ? "disabled" : ""} ${isCheckpointPending ? "checkpoint" : ""} ${isLast ? "last" : ""}`}
      type="button"
      onClick={onSelect}
      disabled={disabled}
      aria-current={active ? "step" : undefined}
    >
      <span className={`stage-node ${stage.status}`} aria-hidden="true">
        {stage.status === "success" ? "✓" : stage.status === "failed" ? "!" : ""}
      </span>
      <span className="stage-main">
        <span className="stage-name">{stage.name}</span>
        {isCheckpointPending && <span className="checkpoint-chip">等待人工确认</span>}
      </span>
      <span className="stage-side">
        <span className={`mini-status ${stage.status}`}>
          <span aria-hidden="true">{statusIcon[stage.status]}</span>
          {stage.status === "success" && stage.checkpoint ? "已完成（已审核）" : statusLabel[stage.status]}
        </span>
        {shouldShowDuration && <span className="duration">{stage.duration}</span>}
      </span>
    </button>
  );
}
