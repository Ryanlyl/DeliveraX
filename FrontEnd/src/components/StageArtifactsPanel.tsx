import { useCallback, useEffect, useState } from "react";
import { getStageReviewAssets } from "../api/artifacts";
import type { ReviewAssetsResponse, Stage } from "../types/pipeline";
import ArtifactMarkdownViewer from "./ArtifactMarkdownViewer";
import DiffViewer from "./DiffViewer";
import ReviewReportViewer from "./ReviewReportViewer";

type Props = {
  pipelineId: string;
  stage: Stage;
};

type LoadState = "idle" | "loading" | "loaded" | "error";

export default function StageArtifactsPanel({ pipelineId, stage }: Props) {
  const [assets, setAssets] = useState<ReviewAssetsResponse | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadState("loading");
    setError(null);
    try {
      const result = await getStageReviewAssets(pipelineId, stage.id);
      setAssets(result);
      setLoadState("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load artifacts");
      setLoadState("error");
    }
  }, [pipelineId, stage.id]);

  useEffect(() => {
    load();
  }, [load]);

  const hasRealArtifacts =
    assets && (assets.human_output?.content || assets.diff?.content || assets.review_report?.content || assets.artifacts.length > 0);

  // If we have real artifacts, render them
  if (loadState === "loaded" && hasRealArtifacts) {
    return (
      <div className="stage-artifacts-panel">
        {assets!.human_output && (
          <ArtifactMarkdownViewer asset={assets!.human_output} title="Human Output" />
        )}
        {assets!.diff && <DiffViewer asset={assets!.diff} />}
        {assets!.review_report && <ReviewReportViewer asset={assets!.review_report} />}
        {assets!.artifacts.length > 0 && !assets!.human_output && !assets!.diff && !assets!.review_report && (
          <div className="artifact-list-fallback">
            <strong>Output Artifacts</strong>
            <ul>
              {assets!.artifacts.map((a) => (
                <li key={a.path}>
                  <code>{a.path}</code>
                  {a.role && <span className="review-tag neutral">{a.role}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  // Loading state
  if (loadState === "loading") {
    return <div className="artifact-loading">Loading artifacts...</div>;
  }

  // Error or no real artifacts — signal caller to fall back
  if (loadState === "error") {
    return <div className="artifact-loading error">{error}</div>;
  }

  // idle / no artifacts — return null to signal fallback
  return null;
}
