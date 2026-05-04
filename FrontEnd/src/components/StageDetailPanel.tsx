import type { Stage } from "../types/pipeline";
import AgentLogs from "./AgentLogs";
import CheckpointPanel from "./CheckpointPanel";
import StageArtifactsPanel from "./StageArtifactsPanel";

type Props = {
  stage: Stage;
  model: string;
  pipelineId: string;
  pipelineRequirement: string;
  viewingHistory?: boolean;
  onApprove: () => void;
  onReject: (reason: string) => void;
  onRerunStage?: (stageId: string) => void;
};

function stringifyDetail(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  return JSON.stringify(value, null, 2);
}

function getStageOutputText(stage: Stage): string {
  if (stage.human_output?.trim()) return stage.human_output;
  if (stage.error) return `${stage.error.code}: ${stage.error.message}`;
  if (Object.keys(stage.data).length > 0) return stringifyDetail(stage.data);
  if (stage.output_artifacts.length > 0) return stage.output_artifacts.map((a) => a.path).join("\n");
  return "";
}

const statusLabel: Record<Stage["status"], string> = {
  queued: "待执行",
  running: "AI 正在执行",
  succeeded: "已完成",
  failed: "执行失败",
  pending_approval: "等待人工审核",
  rejected: "已驳回",
  cancelled: "已取消",
  skipped: "已跳过",
};

export default function StageDetailPanel({
  stage,
  model,
  pipelineId,
  viewingHistory = false,
  onApprove,
  onReject,
  onRerunStage,
}: Props) {
  const stageOutput = getStageOutputText(stage);
  const hasRun = stage.status !== "queued";
  const isFailed = stage.status === "failed";
  const canRerun = (stage.status === "succeeded" || stage.status === "failed") && onRerunStage;

  return (
    <section className="detail-panel">
      <div className="detail-header">
        <div>
          <span className="eyebrow">AI 执行结果</span>
          <h2>{stage.name}</h2>
        </div>
        <span className={`status-pill ${stage.status}`}>{statusLabel[stage.status]}</span>
      </div>

      {viewingHistory && (
        <div className="history-view-note">
          正在查看历史阶段，不影响当前 Pipeline 执行。
        </div>
      )}

      {isFailed && stage.error && (
        <div className="stage-error-card">
          <strong>Error: {stage.error.code}</strong>
          <p>{stage.error.message}</p>
          {Object.keys(stage.error.details).length > 0 && (
            <pre>{stringifyDetail(stage.error.details)}</pre>
          )}
        </div>
      )}

      <div className="content-box">
        {hasRun && (
          <StageArtifactsPanel pipelineId={pipelineId} stage={stage} />
        )}

        {hasRun && stageOutput && (
          <div className="stage-output-fallback">
            <details open>
              <summary>Raw Output</summary>
              <pre>{stageOutput}</pre>
            </details>
          </div>
        )}

        {!hasRun && (
          <div className="artifact-loading">
            Stage is queued. Start the pipeline to begin execution.
          </div>
        )}

        {hasRun && !stageOutput && stage.status === "running" && (
          <div className="artifact-loading">
            Stage is running — output will appear here once available.
          </div>
        )}
      </div>

      {stage.input_artifacts.length > 0 && (
        <div className="stage-input-artifacts">
          <strong>Input Artifacts</strong>
          <ul>
            {stage.input_artifacts.map((a) => (
              <li key={a.path}>
                <code>{a.path}</code>
                {a.role && <span className="review-tag neutral">{a.role}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {stage.status === "pending_approval" && (
        <CheckpointPanel
          title={stage.checkpoint_label ?? "Awaiting Human Approval"}
          description={
            stage.checkpoint_description ??
            "AI Agent 已完成当前阶段产物，请人工确认是否继续推进 Pipeline。"
          }
          onApprove={onApprove}
          onReject={onReject}
        />
      )}

      {canRerun && (
        <div className="stage-actions">
          <button
            className="button secondary"
            type="button"
            onClick={() => onRerunStage?.(stage.id)}
          >
            Re-run Stage
          </button>
        </div>
      )}

      <AgentLogs logs={stage.logs} model={model} />
    </section>
  );
}
