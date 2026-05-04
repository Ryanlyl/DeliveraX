import { useState } from "react";
import type { ArtifactRef } from "../types/pipeline";

type Props = {
  title: string;
  description: string;
  artifacts?: ArtifactRef[];
  humanOutput?: string | null;
  onApprove: () => void;
  onReject: (reason: string) => void;
};

export default function CheckpointPanel({
  title,
  description,
  artifacts,
  humanOutput,
  onApprove,
  onReject,
}: Props) {
  const [reason, setReason] = useState("");

  return (
    <section className="checkpoint-panel">
      <div>
        <span className="checkpoint-kicker">CHECKPOINT</span>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>

      {humanOutput && (
        <div className="checkpoint-summary">
          <strong>AI Output Summary</strong>
          <pre>{humanOutput}</pre>
        </div>
      )}

      {artifacts && artifacts.length > 0 && (
        <div className="checkpoint-artifacts">
          <strong>Output Artifacts</strong>
          <ul>
            {artifacts.map((a) => (
              <li key={a.path}>
                <code>{a.path}</code>
                {a.role && <span className="review-tag neutral">{a.role}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <textarea
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="如需返回修改，可补充调整意见..."
      />
      <div className="checkpoint-actions">
        <button
          className="button secondary warning"
          type="button"
          onClick={() => onReject(reason || "需要重新生成并补充说明")}
        >
          返回修改
        </button>
        <button className="button primary" type="button" onClick={onApprove}>
          确认通过
        </button>
      </div>
    </section>
  );
}
