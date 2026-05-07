import type { StageRecord, StageStatus } from "../api/client";

type Props = {
  stage: StageRecord;
  active: boolean;
  selected: boolean;
  disabled: boolean;
  isLast: boolean;
  onSelect: () => void;
};

const statusLabel: Record<StageStatus, string> = {
  queued: "\u5f85\u6267\u884c",
  running: "\u6267\u884c\u4e2d",
  succeeded: "\u5df2\u5b8c\u6210",
  failed: "\u6267\u884c\u5931\u8d25",
  pending_approval: "\u5df2\u5b8c\u6210\uff08\u5f85\u5ba1\u6838\uff09",
  rejected: "\u5df2\u62d2\u7edd",
  cancelled: "\u5df2\u53d6\u6d88",
  skipped: "\u5df2\u8df3\u8fc7",
};

const statusIcon: Record<StageStatus, string> = {
  queued: "\u25cb",
  running: "\u25cf",
  succeeded: "\u2713",
  failed: "!",
  pending_approval: "\u2713",
  rejected: "!",
  cancelled: "!",
  skipped: "\u25cb",
};

function fmtDuration(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms}ms`;
}

export default function StageCard({ stage, active, selected, disabled, isLast, onSelect }: Props) {
  const isCheckpointPending = stage.checkpoint && stage.status === "pending_approval";
  const shouldShowDuration = stage.status !== "queued" && stage.duration_ms > 0;

  return (
    <button
      className={`stage-card ${active ? "active" : ""} ${selected ? "selected" : ""} ${disabled ? "disabled" : ""} ${
        isCheckpointPending ? "checkpoint" : ""
      } ${isLast ? "last" : ""}`}
      type="button"
      onClick={onSelect}
      disabled={disabled}
      aria-current={active ? "step" : undefined}
    >
      <span className={`stage-node ${stage.status}`} aria-hidden="true">
        {stage.status === "succeeded" ? "\u2713" : stage.status === "failed" ? "!" : ""}
      </span>
      <span className="stage-main">
        <span className="stage-name">{stage.name}</span>
        {isCheckpointPending && <span className="checkpoint-chip">{"\u7b49\u5f85\u4eba\u5de5\u786e\u8ba4"}</span>}
      </span>
      <span className="stage-side">
        <span className={`mini-status ${stage.status}`}>
          <span aria-hidden="true">{statusIcon[stage.status]}</span>
          {statusLabel[stage.status]}
        </span>
        {shouldShowDuration && <span className="duration">{fmtDuration(stage.duration_ms)}</span>}
      </span>
    </button>
  );
}
