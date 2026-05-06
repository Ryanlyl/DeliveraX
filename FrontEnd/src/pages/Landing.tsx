import { useNavigate } from "react-router-dom";
import type { CSSProperties, MouseEvent, ReactNode } from "react";
import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";

const previewStages = [
  {
    title: "需求分析",
    status: "已完成",
    tone: "completed",
  },
  {
    title: "方案设计",
    status: "已完成",
    tone: "completed",
  },
  {
    title: "代码生成",
    status: "正在执行",
    tone: "progress",
  },
  {
    title: "测试生成",
    status: "待执行",
    tone: "pending",
  },
  {
    title: "代码评审",
    status: "待确认",
    tone: "review",
  },
  {
    title: "交付集成",
    status: "待执行",
    tone: "pending",
  },
];

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

type IconName =
  | "rocket"
  | "play"
  | "zap"
  | "package"
  | "workflow"
  | "check"
  | "document"
  | "code"
  | "test"
  | "refresh"
  | "shield";

const trustSignals: Array<{ icon: IconName; text: string }> = [
  { icon: "zap", text: "3分钟完成一次开发流程" },
  { icon: "package", text: "自动生成代码 + 测试 + 文档" },
  { icon: "workflow", text: "覆盖完整软件交付链路" },
];

const pipelineCapabilities: Array<{
  icon: IconName;
  agent: string;
  number: string;
  from: string;
  to: string;
  stage: string;
  description: string;
  points: string[];
  featured?: boolean;
}> = [
  {
    icon: "document",
    agent: "Req Agent",
    number: "01",
    from: "模糊需求",
    to: "结构需求",
    stage: "需求分析",
    description: "将自然语言转化为可执行描述",
    points: ["消除理解偏差", "输出结构化结果", "沉淀需求上下文"],
  },
  {
    icon: "document",
    agent: "Design Agent",
    number: "02",
    from: "语义理解",
    to: "技术表达",
    stage: "方案设计",
    description: "建立需求与代码映射关系",
    points: ["形成技术方案", "建立代码映射", "明确执行边界"],
  },
  {
    icon: "workflow",
    agent: "Code Agent",
    number: "03",
    from: "方案设计",
    to: "代码变更",
    stage: "代码生成",
    description: "生成可执行代码变更",
    points: ["修改范围可控", "结果可回溯", "严格按方案执行"],
    featured: true,
  },
  {
    icon: "code",
    agent: "Test Agent",
    number: "04",
    from: "代码实现",
    to: "可靠结果",
    stage: "测试生成",
    description: "自动验证代码行为",
    points: ["覆盖变更点", "对齐验收标准", "输出验证结果"],
  },
  {
    icon: "test",
    agent: "Review Agent",
    number: "05",
    from: "实现结果",
    to: "质量评估",
    stage: "代码评审",
    description: "识别风险与质量问题",
    points: ["识别潜在风险", "评估交付质量", "生成审阅意见"],
  },
  {
    icon: "shield",
    agent: "Merge Agent",
    number: "06",
    from: "验证结果",
    to: "交付产物",
    stage: "交付集成",
    description: "输出最终可用结果",
    points: ["汇总交付产物", "保留执行记录", "支持集成发布"],
  },
];

function SvgIcon({ name, className }: { name: IconName; className?: string }) {
  const commonProps = {
    className,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  const paths: Record<IconName, ReactNode> = {
    rocket: (
      <>
        <path d="M4.5 16.5c-1.2 1-1.8 2.5-1.5 4 1.5.3 3-.3 4-1.5" />
        <path d="M9 15 6 18" />
        <path d="M15 9l-6 6" />
        <path d="M14.5 4.5c2.1-.9 4.1-1 5.5-.5.5 1.4.4 3.4-.5 5.5-1 2.3-3 4.6-5.5 6.5L8 10c1.9-2.5 4.2-4.5 6.5-5.5Z" />
        <path d="M14 5v5h5" />
      </>
    ),
    play: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m10 8 6 4-6 4V8Z" />
      </>
    ),
    zap: <path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" />,
    package: (
      <>
        <path d="m21 8-9-5-9 5 9 5 9-5Z" />
        <path d="M3 8v8l9 5 9-5V8" />
        <path d="M12 13v8" />
        <path d="m7.5 5.5 9 5" />
      </>
    ),
    workflow: (
      <>
        <rect x="3" y="4" width="6" height="5" rx="1.5" />
        <rect x="15" y="4" width="6" height="5" rx="1.5" />
        <rect x="9" y="15" width="6" height="5" rx="1.5" />
        <path d="M9 6.5h6" />
        <path d="M6 9v2.5A3.5 3.5 0 0 0 9.5 15H12" />
        <path d="M18 9v2.5A3.5 3.5 0 0 1 14.5 15H12" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    document: (
      <>
        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
        <path d="M14 3v5h5" />
        <path d="M8 13h8" />
        <path d="M8 17h5" />
      </>
    ),
    code: (
      <>
        <path d="m8 9-4 3 4 3" />
        <path d="m16 9 4 3-4 3" />
        <path d="m14 5-4 14" />
      </>
    ),
    test: (
      <>
        <path d="M9 11 12 14 22 4" />
        <path d="M20 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h11" />
      </>
    ),
    refresh: (
      <>
        <path d="M21 12a9 9 0 0 1-15.2 6.5" />
        <path d="M3 12A9 9 0 0 1 18.2 5.5" />
        <path d="M18 2v4h-4" />
        <path d="M6 22v-4h4" />
      </>
    ),
    shield: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="m9.5 12 1.8 1.8 3.7-4" />
      </>
    ),
  };

  return <svg {...commonProps}>{paths[name]}</svg>;
}

export default function Landing() {
  const navigate = useNavigate();
  const [visibleDiffCount, setVisibleDiffCount] = useState(1);
  const [activeLogIndex, setActiveLogIndex] = useState(0);
  const [activeCapabilityIndex, setActiveCapabilityIndex] = useState(0);
  const [isCapabilityPaused, setIsCapabilityPaused] = useState(false);

  const startDevFlow = () => navigate("/home");
  const viewProjects = () => navigate("/projects");
  const focusFeatures = (e: MouseEvent) => {
    const target = document.getElementById("features");
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  useEffect(() => {
    const diffTimer = window.setInterval(() => {
      setVisibleDiffCount((current) => (current >= codeDiffLines.length ? 0 : current + 1));
    }, visibleDiffCount >= codeDiffLines.length ? 1900 : 720);

    return () => window.clearInterval(diffTimer);
  }, [visibleDiffCount]);

  useEffect(() => {
    const logTimer = window.setInterval(() => {
      setActiveLogIndex((current) => (current + 1) % 3);
    }, 1000);

    return () => window.clearInterval(logTimer);
  }, []);

  useEffect(() => {
    if (isCapabilityPaused) return;

    const capabilityTimer = window.setInterval(() => {
      setActiveCapabilityIndex((current) => (current + 1) % pipelineCapabilities.length);
    }, 3500);

    return () => window.clearInterval(capabilityTimer);
  }, [isCapabilityPaused]);

  const pipelineProgress = activeCapabilityIndex / (pipelineCapabilities.length - 1);

  return (
    <main className="landing-page">
      <div className="landing-grid-overlay" aria-hidden="true" />
      <div className="landing-glow landing-glow-left" aria-hidden="true" />
      <div className="landing-glow landing-glow-right" aria-hidden="true" />

      <AppNav active="home" onFeaturesClick={focusFeatures} />

      <section className="landing-hero">
        <div className="landing-copy">
          <span className="landing-kicker">
            <SvgIcon name="workflow" className="landing-kicker-icon" />
            AI DevFlow 工作台
          </span>
          <h1>
            DeliveraX
            <br />
            让 AI 推进<span>完整交付</span>
          </h1>
          <div className="landing-description">
            <p>面向前端场景的 AI DevFlow 工作台</p>
            <p>输入一个需求，AI 自动推进完整开发流程：</p>
            <p className="landing-flow-line">分析 → 设计 → 编码 → 测试 → 评审</p>
            <p>关键节点支持人工确认，确保交付质量。</p>
          </div>
          <p className="landing-cta-label">一键体验完整 DevFlow</p>
          <div className="landing-actions">
            <button className="landing-primary" type="button" onClick={startDevFlow}>
              <SvgIcon name="rocket" className="landing-button-icon" />
              免费体验 AI 自动开发
            </button>
            <button className="landing-secondary" type="button" onClick={viewProjects}>
              <SvgIcon name="play" className="landing-button-icon" />
              进入项目仓库
            </button>
          </div>
          <div className="landing-trust-signals" aria-label="DeliveraX 能力数据">
            {trustSignals.map((item) => (
              <span key={item.text}>
                <span className="trust-icon" aria-hidden="true">
                  <SvgIcon name={item.icon} />
                </span>
                {item.text}
              </span>
            ))}
          </div>
          <p className="landing-cta-note">无需配置 · 即刻体验</p>
        </div>

        <div className="landing-preview-stack" id="landing-preview">
          <section className="devflow-console" aria-label="AI DevFlow Console 正在运行">
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
                      {stage.tone === "completed" ? <SvgIcon name="check" className="console-check-icon" /> : ""}
                    </span>
                    <div>
                      <h3>{stage.title}</h3>
                      <p>{stage.status}</p>
                    </div>
                    {stage.tone === "progress" && <span className="active-runner">执行中 · · ·</span>}
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
                      className={index === activeLogIndex ? "active" : index < activeLogIndex ? "history" : "pending"}
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
        </div>
      </section>

      <section className="landing-features" id="features" aria-labelledby="features-title">
        <div className="landing-features-heading">
          <span className="landing-kicker">PRODUCT CAPABILITIES</span>
          <h2 id="features-title">
            一个 DevFlow
            <br />
            一条自动交付流水线
          </h2>
          <p>不是写代码，而是完成交付</p>
          <small>每个阶段都基于上下文与历史结果持续优化</small>
        </div>
        <div
          className="capability-pipeline"
          style={
            {
              "--pipeline-progress": `${pipelineProgress * 100}%`,
              "--pipeline-progress-ratio": pipelineProgress,
              "--pipeline-progress-x": `${4 + pipelineProgress * 92}%`,
            } as CSSProperties
          }
          aria-label="DeliveraX 自动交付流水线"
        >
          {pipelineCapabilities.map((item, index) => {
            const isActiveCapability = index === activeCapabilityIndex;

            return (
            <div
              className="capability-pipeline-item"
              key={item.stage}
              onMouseEnter={() => {
                setIsCapabilityPaused(true);
                setActiveCapabilityIndex(index);
              }}
              onMouseLeave={() => setIsCapabilityPaused(false)}
            >
              <article className={`landing-feature-card pipeline-node ${isActiveCapability ? "active" : ""}`}>
                <div className="pipeline-node-meta">
                  <span className="pipeline-agent">
                    {item.number} · {item.agent}
                  </span>
                  {isActiveCapability && (
                    <span className="pipeline-running">
                      <span aria-hidden="true" />
                      Running
                    </span>
                  )}
                </div>
                <div className="pipeline-icon-row">
                  <span className="capability-icon" aria-hidden="true">
                    <SvgIcon name={item.icon} />
                  </span>
                </div>
                <div className="pipeline-state-shift">
                  <span>{item.from}</span>
                  <strong>→</strong>
                  <span>{item.to}</span>
                </div>
                <h3>{item.stage}</h3>
                <p>{item.description}</p>
                <ul className="pipeline-points">
                  {item.points.map((point) => (
                    <li key={point}>
                      <SvgIcon name="check" />
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </article>
              {index < pipelineCapabilities.length - 1 && <span className="pipeline-connector" aria-hidden="true">→</span>}
            </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
