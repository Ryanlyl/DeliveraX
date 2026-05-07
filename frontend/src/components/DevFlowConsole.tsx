import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import SvgIcon from "./SvgIcon";

const previewStages = [
  { title: "需求分析", status: "已完成", tone: "completed" },
  { title: "方案设计", status: "已完成", tone: "completed" },
  { title: "代码生成", status: "正在执行", tone: "progress" },
  { title: "测试生成", status: "待执行", tone: "pending" },
  { title: "代码评审", status: "待确认", tone: "review" },
  { title: "交付集成", status: "待执行", tone: "pending" },
] as const;

const codeDiffLines = [
  "+ add completed state guard",
  "+ update primary action style",
  "+ add hover / disabled feedback",
];

const liveLogs = [
  "Parsing requirement...",
  "Generating solution design...",
  "Creating task workspace...",
  "Applying code changes...",
  "Writing git diff...",
];

type Props = {
  compact?: boolean;
};

export default function DevFlowConsole({ compact = false }: Props) {
  const [visibleDiffCount, setVisibleDiffCount] = useState(1);
  const [activeLogIndex, setActiveLogIndex] = useState(0);

  useEffect(() => {
    const diffTimer = window.setInterval(() => {
      setVisibleDiffCount((current) =>
        current >= codeDiffLines.length ? 0 : current + 1,
      );
    }, visibleDiffCount >= codeDiffLines.length ? 1900 : 720);

    return () => window.clearInterval(diffTimer);
  }, [visibleDiffCount]);

  useEffect(() => {
    const logTimer = window.setInterval(() => {
      setActiveLogIndex((current) => (current + 1) % 3);
    }, 1000);

    return () => window.clearInterval(logTimer);
  }, []);

  return (
    <section
      className={`devflow-console${compact ? " compact" : ""}`}
      aria-label="AI DevFlow Console 正在运行"
    >
      <div className="console-window-bar">
        <div className="console-window-left">
          <span className="window-dots" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <div>
            <strong>AI DevFlow Console</strong>
            <small>Task #DX-042</small>
          </div>
        </div>
        <span className="console-running-badge">Running</span>
      </div>

      <div className="console-body">
        <div className="console-section-head">
          <span>Pipeline Studio</span>
          <strong>代码生成中</strong>
        </div>

        <div className="console-pipeline">
          {previewStages.map((stage) => (
            <article className={`console-step ${stage.tone}`} key={stage.title}>
              <span className={`console-step-node ${stage.tone}`} aria-hidden="true">
                {stage.tone === "completed" ? (
                  <SvgIcon name="check" className="console-check-icon" />
                ) : (
                  ""
                )}
              </span>
              <div>
                <h3>{stage.title}</h3>
                <p>{stage.status}</p>
              </div>
              {stage.tone === "progress" && (
                <span className="active-runner">执行中 · · ·</span>
              )}
            </article>
          ))}
        </div>

        <section className="console-output-panel" aria-label="生成结果预览">
          <div className="console-section-head compact">
            <span>Code Diff Preview</span>
            <strong>+3 / -0</strong>
          </div>
          <pre className="console-code-diff">
            {codeDiffLines.map((line, index) => (
              <span
                className={index < visibleDiffCount ? "visible" : ""}
                style={{ "--line-index": index } as CSSProperties}
                key={line}
              >
                {line}
              </span>
            ))}
          </pre>
        </section>

        <section className="console-log-panel" aria-label="实时执行日志">
          <div className="console-section-head compact">
            <span>实时执行日志</span>
            <strong>live</strong>
          </div>
          <div className="console-log-list">
            {liveLogs.map((log, index) => (
              <p
                className={
                  index === activeLogIndex
                    ? "active"
                    : index < activeLogIndex
                      ? "history"
                      : "pending"
                }
                style={{ "--log-index": index } as CSSProperties}
                key={log}
              >
                <span aria-hidden="true">→</span>
                {log}
              </p>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
