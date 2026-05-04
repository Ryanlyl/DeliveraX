import type { ReviewAssetItem } from "../types/pipeline";

type Props = {
  asset: ReviewAssetItem;
  title?: string;
};

export default function ArtifactMarkdownViewer({ asset, title }: Props) {
  const content = asset.content ?? "";

  return (
    <article className="artifact-markdown-viewer">
      {title && (
        <div className="artifact-section-header">
          <strong>{title}</strong>
          {asset.path && <code className="artifact-path">{asset.path}</code>}
        </div>
      )}
      <pre className="artifact-markdown-content">{content}</pre>
    </article>
  );
}
