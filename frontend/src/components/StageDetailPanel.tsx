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

function toDisplayList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  return value.map((item) =>
    typeof item === "string" ? item : JSON.stringify(item),
  );
}

type ErrorLike = {
  code?: string;
  message?: string;
  details?: Record<string, unknown>;
};

function resolveStageError(stage: StageRecord): ErrorLike | null {
  if (stage.error) return stage.error;
  const nested = stage.data?.error;
  if (nested && typeof nested === "object") {
    return nested as ErrorLike;
  }
  return null;
}

function StageErrorBlock({ stage }: { stage: StageRecord }) {
  const effectiveError = resolveStageError(stage);
  const dataErrors = toDisplayList(stage.data?.errors);
  const dataWarnings = toDisplayList(stage.data?.warnings);

  return (
    <div className="stage-error-block" style={{ marginTop: "12px", padding: "12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", fontSize: "13px", lineHeight: "1.6" }}>
      <h4 style={{ margin: "0 0 8px", color: "#b91c1c", fontSize: "14px" }}>Execution Error Details</h4>

      {effectiveError && (
        <div style={{ marginBottom: "8px" }}>
          {effectiveError.code && (
            <p style={{ margin: "0 0 4px" }}><strong>Error Code:</strong> <code>{effectiveError.code}</code></p>
          )}
          {effectiveError.message && (
            <p style={{ margin: "0 0 4px", color: "#991b1b" }}><strong>Message:</strong> {effectiveError.message}</p>
          )}
          {effectiveError.details && Object.keys(effectiveError.details).length > 0 && (
            <details style={{ marginTop: "4px" }}>
              <summary style={{ cursor: "pointer", color: "#b91c1c" }}>Error Details</summary>
              <pre style={{ margin: "4px 0 0", padding: "8px", background: "#fff", border: "1px solid #fecaca", borderRadius: "4px", overflow: "auto", fontSize: "12px" }}>
                {JSON.stringify(effectiveError.details, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}

      {dataErrors.length > 0 && (
        <details style={{ marginBottom: "8px" }}>
          <summary style={{ cursor: "pointer", color: "#b91c1c" }}>Data Errors ({dataErrors.length})</summary>
          <ul style={{ margin: "4px 0 0", paddingLeft: "20px", color: "#991b1b" }}>
            {dataErrors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </details>
      )}

      {dataWarnings.length > 0 && (
        <details style={{ marginBottom: "8px" }}>
          <summary style={{ cursor: "pointer", color: "#92400e" }}>Data Warnings ({dataWarnings.length})</summary>
          <ul style={{ margin: "4px 0 0", paddingLeft: "20px", color: "#92400e" }}>
            {dataWarnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </details>
      )}

      <div style={{ marginTop: "8px", padding: "8px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "4px", color: "#92400e", fontSize: "12px" }}>
        <strong>Troubleshooting Suggestions:</strong>
        <ul style={{ margin: "4px 0 0", paddingLeft: "20px" }}>
          <li>Check that the project repository is cloned and accessible.</li>
          <li>Verify the technical design artifact exists from the solution stage.</li>
          <li>In local-only mode, an empty diff is expected — ensure local_only=true is set.</li>
          <li>Check stage logs below for more details.</li>
        </ul>
      </div>
    </div>
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
        <div>
          <p>No output artifacts available.</p>
          {stage.status === "failed" && (
            <p style={{ color: "#b91c1c", fontSize: "12px", marginTop: "4px" }}>
              Stage failed before artifacts could be produced. See error details above and stage logs below.
            </p>
          )}
          {stage.status === "running" && (
            <p style={{ color: "#2563eb", fontSize: "12px", marginTop: "4px" }}>
              Stage is still running — artifacts will appear when complete.
            </p>
          )}
        </div>
      )}
      {stage.logs && stage.logs.length > 0 && (
        <details open={stage.status === "failed"}>
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

      {stage.status === "failed" && <StageErrorBlock stage={stage} />}

      <AgentLogs logs={stage.logs} model={stage.agent} />
    </section>
  );
}
