import type { ReviewAssetItem } from "../types/pipeline";

type Props = {
  asset: ReviewAssetItem;
};

export default function DiffViewer({ asset }: Props) {
  const content = asset.content ?? "";

  return (
    <section className="code-diff-card">
      <div className="code-diff-toolbar">
        <strong>Code Diff</strong>
        <div>
          <button type="button">复制</button>
          <button type="button">展开</button>
        </div>
      </div>
      {asset.path && <code className="artifact-path">{asset.path}</code>}
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
    </section>
  );
}
