import { useState } from "react";
import type { CurrentCheckpointResponse, ReviewAssetsResponse } from "../api/client";

type Props = {
  checkpoint: CurrentCheckpointResponse;
  reviewAssets: ReviewAssetsResponse | null;
  pipelineId: string;
  onApprove: () => void;
  onReject: (reason: string) => void;
  isLoadingAssets: boolean;
  onFetchReviewAssets: (stageId: string) => void;
};

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

export default function CheckpointPanel({
  checkpoint,
  reviewAssets,
  pipelineId: _pipelineId,
  onApprove,
  onReject,
  isLoadingAssets,
  onFetchReviewAssets: _onFetchReviewAssets,
}: Props) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const cp = checkpoint.checkpoint;
  const stage = checkpoint.stage;

  if (!cp) {
    return (
      <section className="checkpoint-panel">
        <div className="checkpoint-empty">
          <p>No pending checkpoint.</p>
        </div>
      </section>
    );
  }

  const title = cp.title || stage?.checkpoint_label || stage?.name || "Checkpoint";
  const description =
    cp.description || stage?.checkpoint_description || "AI Agent 已完成当前阶段，请人工确认。";

  const handleApproveClick = async () => {
    setSubmitting(true);
    try {
      await onApprove();
    } finally {
      setSubmitting(false);
    }
  };

  const handleRejectClick = async () => {
    if (!reason.trim()) return;
    setSubmitting(true);
    try {
      await onReject(reason.trim());
      setReason("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="checkpoint-panel">
      <div className="checkpoint-header">
        <span className="checkpoint-kicker">CHECKPOINT</span>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>

      {/* ── human output ── */}
      {checkpoint.human_output && (
        <div className="checkpoint-section">
          <strong>Human Output</strong>
          <MarkdownBlock content={checkpoint.human_output} />
        </div>
      )}

      {/* ── review assets ── */}
      {isLoadingAssets && (
        <div className="checkpoint-section">
          <span className="spinner" aria-hidden="true" />
          <p>Loading review assets…</p>
        </div>
      )}

      {reviewAssets && !isLoadingAssets && (
        <div className="checkpoint-section">
          {reviewAssets.human_output?.content && (
            <div>
              <strong>AI Output</strong>
              <MarkdownBlock content={reviewAssets.human_output.content} />
            </div>
          )}
          {reviewAssets.diff?.content && (
            <div>
              <strong>Diff</strong>
              <DiffBlock content={reviewAssets.diff.content} />
            </div>
          )}
          {reviewAssets.review_report?.content && (
            <div>
              <strong>Review Report</strong>
              <MarkdownBlock content={reviewAssets.review_report.content} />
            </div>
          )}
          {reviewAssets.artifacts && reviewAssets.artifacts.length > 0 && (
            <div>
              <strong>Artifacts</strong>
              <ul>
                {reviewAssets.artifacts.map((a) => (
                  <li key={`${a.name}-${a.path}`}>
                    <strong>{a.name}</strong> <code>{a.path}</code> ({a.type})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ── artifacts from checkpoint ── */}
      {cp.artifact_refs && cp.artifact_refs.length > 0 && (
        <div className="checkpoint-section">
          <strong>Checkpoint Artifacts</strong>
          <ul>
            {cp.artifact_refs.map((a) => (
              <li key={`${a.name}-${a.path}`}>
                <strong>{a.name}</strong> <code>{a.path}</code> ({a.type})
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── decision area ── */}
      <div className="checkpoint-decision">
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="请输入拒绝原因（通过则无需填写）"
          rows={3}
        />
        <div className="checkpoint-actions">
          <button
            className="button secondary warning"
            type="button"
            onClick={handleRejectClick}
            disabled={submitting || !reason.trim()}
          >
            {submitting ? "处理中..." : "拒绝"}
          </button>
          <button
            className="button primary"
            type="button"
            onClick={handleApproveClick}
            disabled={submitting}
          >
            {submitting ? "处理中..." : "通过"}
          </button>
        </div>
      </div>
    </section>
  );
}
