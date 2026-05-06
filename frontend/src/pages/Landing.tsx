import { useNavigate } from "react-router-dom";
import type { CSSProperties, MouseEvent } from "react";
import { useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import DevFlowConsole from "../components/DevFlowConsole";
import SvgIcon from "../components/SvgIcon";
import type { IconName } from "../components/SvgIcon";

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

export default function Landing() {
  const navigate = useNavigate();
  const [activeCapabilityIndex, setActiveCapabilityIndex] = useState(0);
  const [isCapabilityPaused, setIsCapabilityPaused] = useState(false);

  const startDevFlow = () => navigate("/dashboard");
  const viewProjects = () => navigate("/projects");
  const focusFeatures = (e: MouseEvent) => {
    const target = document.getElementById("features");
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

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

      <AppNav onFeaturesClick={focusFeatures} />

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
          <DevFlowConsole />
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
