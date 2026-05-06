import type { StageRecord, ReviewAssetsResponse } from "../api/client";
import AgentLogs from "./AgentLogs";

type Props = {
  stage: StageRecord;
  reviewAssets: ReviewAssetsResponse | null;
  isLoadingAssets: boolean;
  onApprove?: () => void;
  onReject?: (reason: string) => void;
};

const statusLabel: Record<string, string> = {
  queued: "待执行",
  running: "AI 正在执行",
  succeeded: "已完成",
  failed: "执行失败",
  pending_approval: "等待人工审核",
  rejected: "已拒绝",
  cancelled: "已取消",
  skipped: "已跳过",
};

const agentLabel: Record<string, string> = {
  requirements: "需求分析",
  solution: "技术方案设计",
  code: "代码生成",
  test: "测试生成",
  review: "代码评审",
  integration: "交付集成",
};

function stageDisplayName(stage: StageRecord): string {
  return agentLabel[stage.id] || stage.name || stage.agent;
}

function MarkdownBlock({ content }: { content: string }) {
  return (
    <div className="markdown-content">
      <pre className="content-pre">{content}</pre>
    </div>
  );
}

function DiffBlock({ content }: { content: string }) {
  return (
    <pre className="code-block diff-block">
      {content.split("\n").map((line, index) => (
        <span
          key={`${line.slice(0, 20)}-${index}`}
          className={
            line.startsWith("+") ? "diff-add" : line.startsWith("-") ? "diff-remove" : ""
          }
        >
          {line || " "}
        </span>
      ))}
    </pre>
  );
}

function ArtifactsList({ stage, reviewAssets }: { stage: StageRecord; reviewAssets: ReviewAssetsResponse | null }) {
  const artifacts = reviewAssets?.artifacts ?? [];

  return (
    <div className="artifacts-fallback">
      <h4>Stage Output Artifacts</h4>
      {artifacts.length > 0 ? (
        <ul>
          {artifacts.map((a) => (
            <li key={`${a.name}-${a.path}`}>
              <strong>{a.name}</strong> <code>{a.path}</code> ({a.type})
            </li>
          ))}
        </ul>
      ) : stage.output_artifacts && stage.output_artifacts.length > 0 ? (
        <ul>
          {stage.output_artifacts.map((a) => (
            <li key={`${a.name}-${a.path}`}>
              <strong>{a.name}</strong> <code>{a.path}</code> ({a.type})
            </li>
          ))}
        </ul>
      ) : (
        <p>No output artifacts available.</p>
      )}
      {stage.logs && stage.logs.length > 0 && (
        <details>
          <summary>Stage Logs</summary>
          <pre className="raw-logs">{stage.logs.join("\n")}</pre>
        </details>
      )}
      {stage.data && Object.keys(stage.data).length > 0 && (
        <details>
          <summary>Stage Data (raw)</summary>
          <pre className="raw-json">{JSON.stringify(stage.data, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}

export const DESIGN_NAV_GROUPS: Array<{ group: string; items: Array<{ id: string; label: string }> }> = [];

export default function StageDetailPanel({ stage, reviewAssets, isLoadingAssets }: Props) {
  const displayStatus = statusLabel[stage.status] || stage.status;
  const displayName = stageDisplayName(stage);

  const renderContent = () => {
    if (isLoadingAssets) {
      return (
        <div className="loading-assets">
          <span className="spinner" aria-hidden="true" />
          <p>Loading stage assets…</p>
        </div>
      );
    }

    if (reviewAssets) {
      if (reviewAssets.diff?.content) {
        return <DiffBlock content={reviewAssets.diff.content} />;
      }
      if (reviewAssets.review_report?.content) {
        return <MarkdownBlock content={reviewAssets.review_report.content} />;
      }
      if (reviewAssets.human_output?.content) {
        return <MarkdownBlock content={reviewAssets.human_output.content} />;
      }
    }

    if (stage.human_output) {
      return <MarkdownBlock content={stage.human_output} />;
    }

    return <ArtifactsList stage={stage} reviewAssets={reviewAssets} />;
  };

  return (
    <section className="detail-panel">
      <div className="detail-header">
        <div>
          <span className="eyebrow">AI 执行结果</span>
          <h2>{displayName}</h2>
        </div>
        <span className={`status-pill ${stage.status}`}>{displayStatus}</span>
      </div>

      {/* ── stage meta ── */}
      <div className="stage-meta">
        <span>Agent: <strong>{stage.agent}</strong></span>
        {stage.checkpoint && (
          <span className="checkpoint-chip">人工检查点</span>
        )}
        {stage.duration_ms > 0 && (
          <span>耗时: {(stage.duration_ms / 1000).toFixed(1)}s</span>
        )}
      </div>

      <div className="content-box">
        {renderContent()}
      </div>

      <AgentLogs logs={stage.logs} model={stage.agent} />
    </section>
  );
}
