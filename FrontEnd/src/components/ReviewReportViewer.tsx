import type { ReviewAssetItem } from "../types/pipeline";

type Props = {
  asset: ReviewAssetItem;
};

export default function ReviewReportViewer({ asset }: Props) {
  const content = asset.content ?? "";

  return (
    <article className="review-report-viewer">
      <div className="artifact-section-header">
        <strong>Review Report</strong>
        {asset.path && <code className="artifact-path">{asset.path}</code>}
      </div>
      <pre className="artifact-markdown-content">{content}</pre>
    </article>
  );
}
