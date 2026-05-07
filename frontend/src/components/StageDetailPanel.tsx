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
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  pending_approval: "Pending approval",
  rejected: "Rejected",
  cancelled: "Cancelled",
  skipped: "Skipped",
};

const agentLabel: Record<string, string> = {
  requirements: "Requirements Analysis",
  solution: "Solution Design",
  code: "Code Generation",
  test: "Test Generation",
  review: "Code Review",
  integration: "Release Integration",
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
          className={line.startsWith("+") ? "diff-add" : line.startsWith("-") ? "diff-remove" : ""}
        >
          {line || " "}
        </span>
      ))}
    </pre>
  );
}

function toDisplayList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => (typeof item === "string" ? item : JSON.stringify(item)));
}

type ErrorLike = {
  code?: string;
  message?: string;
  details?: Record<string, unknown>;
};

function resolveStageError(stage: StageRecord): ErrorLike | null {
  if (stage.error) return stage.error;
  const nested = stage.data?.error;
  if (nested && typeof nested === "object") return nested as ErrorLike;
  return null;
}

function StageErrorBlock({ stage }: { stage: StageRecord }) {
  const effectiveError = resolveStageError(stage);
  const dataErrors = toDisplayList(stage.data?.errors);
  const dataWarnings = toDisplayList(stage.data?.warnings);

  return (
    <div className="stage-error-block">
      <h4 className="stage-error-title">Execution Error Details</h4>

      {effectiveError && (
        <div className="stage-error-section">
          {effectiveError.code && (
            <p className="stage-error-row">
              <strong>Error Code:</strong> <code>{effectiveError.code}</code>
            </p>
          )}
          {effectiveError.message && (
            <p className="stage-error-row stage-error-message">
              <strong>Message:</strong> {effectiveError.message}
            </p>
          )}
          {effectiveError.details && Object.keys(effectiveError.details).length > 0 && (
            <details className="stage-error-details">
              <summary>Error Details</summary>
              <pre>{JSON.stringify(effectiveError.details, null, 2)}</pre>
            </details>
          )}
        </div>
      )}

      {dataErrors.length > 0 && (
        <details className="stage-error-details">
          <summary>Data Errors ({dataErrors.length})</summary>
          <ul className="stage-error-list stage-error-list-danger">
            {dataErrors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </details>
      )}

      {dataWarnings.length > 0 && (
        <details className="stage-error-details">
          <summary>Data Warnings ({dataWarnings.length})</summary>
          <ul className="stage-error-list stage-error-list-warn">
            {dataWarnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="stage-error-tip">
        <strong>Troubleshooting Suggestions:</strong>
        <ul>
          <li>Check that the repository is cloned and accessible.</li>
          <li>Verify upstream artifacts from previous stages exist.</li>
          <li>For local-only mode, an empty diff can be expected.</li>
          <li>Inspect stage logs for command-level error details.</li>
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
            <p className="artifacts-note artifacts-note-danger">
              Stage failed before artifacts were produced. See error details and logs below.
            </p>
          )}
          {stage.status === "running" && (
            <p className="artifacts-note artifacts-note-info">
              Stage is still running. Artifacts will appear after completion.
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
          <p>Loading stage assets...</p>
        </div>
      );
    }

    if (reviewAssets) {
      if (reviewAssets.diff?.content) return <DiffBlock content={reviewAssets.diff.content} />;
      if (reviewAssets.review_report?.content) return <MarkdownBlock content={reviewAssets.review_report.content} />;
      if (reviewAssets.human_output?.content) return <MarkdownBlock content={reviewAssets.human_output.content} />;
    }

    if (stage.human_output) return <MarkdownBlock content={stage.human_output} />;

    return <ArtifactsList stage={stage} reviewAssets={reviewAssets} />;
  };

  return (
    <section className="detail-panel">
      <div className="detail-header">
        <div>
          <span className="eyebrow">AI Stage Output</span>
          <h2>{displayName}</h2>
        </div>
        <span className={`status-pill ${stage.status}`}>{displayStatus}</span>
      </div>

      <div className="stage-meta">
        <span>
          Agent: <strong>{stage.agent}</strong>
        </span>
        {stage.duration_ms > 0 && <span>Duration: {(stage.duration_ms / 1000).toFixed(1)}s</span>}
      </div>

      <div className="content-box">{renderContent()}</div>

      {stage.status === "failed" && <StageErrorBlock stage={stage} />}

      <AgentLogs logs={stage.logs} model={stage.agent} />
    </section>
  );
}
