import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createPipeline } from "../api/pipelines";
import AppNav from "../components/AppNav";
import { exampleRequirement } from "../data/mockPipeline";

const previewStages = [
  {
    title: "需求分析",
    status: "已完成",
    tone: "completed",
    checkpoint: "已审核通过",
  },
  {
    title: "方案设计",
    status: "已完成",
    tone: "completed",
  },
  {
    title: "代码生成",
    status: "生成中...",
    tone: "progress",
  },
  {
    title: "测试生成",
    status: "待执行",
    tone: "pending",
  },
  {
    title: "代码评审",
    status: "待执行",
    tone: "pending",
    checkpoint: "待人工确认",
  },
  {
    title: "交付集成",
    status: "待执行",
    tone: "pending",
  },
];

const capabilityTags = [
  {
    icon: "A",
    title: "结构化流程",
    description: "标准化 AI 执行链路",
  },
  {
    icon: "H",
    title: "人工参与决策",
    description: "关键节点人工把控",
  },
  {
    icon: "D",
    title: "可交付级产出",
    description: "支持真实项目交付",
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const [isCreatingDemo, setIsCreatingDemo] = useState(false);

  const startDevFlow = () => navigate("/home");
  const viewPipelineDemo = async () => {
    if (isCreatingDemo) return;
    setIsCreatingDemo(true);
    try {
      const pipeline = await createPipeline({
        name: "AI DevFlow Pipeline",
        requirement: exampleRequirement,
        provider: "GPT-4",
        repo_path: import.meta.env.VITE_DELIVERAX_REPO_PATH || undefined,
      });
      navigate(`/pipeline/${encodeURIComponent(pipeline.id)}`);
    } finally {
      setIsCreatingDemo(false);
    }
  };
  const focusFeatures = () => {
    document.getElementById("landing-preview")?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <main className="landing-page">
      <div className="landing-grid-overlay" aria-hidden="true" />
      <div className="landing-glow landing-glow-left" aria-hidden="true" />
      <div className="landing-glow landing-glow-right" aria-hidden="true" />

      <AppNav active="home" onFeaturesClick={focusFeatures} />

      <section className="landing-hero">
        <div className="landing-copy">
          <span className="landing-kicker">AI 研发流程引擎</span>
          <h1>
            从需求到代码，
            <br />
            让 AI 推进<span>完整交付</span>
          </h1>
          <p className="landing-description">
            输入一个需求，AI 自动完成分析、设计、编码、测试与评审，
            <br />
            并在关键节点由人工确认，确保交付质量。
          </p>
          <p className="landing-cta-label">一键体验完整 DevFlow</p>
          <div className="landing-actions">
            <button className="landing-primary" type="button" onClick={startDevFlow}>
              启动 AI 开发流程 →
            </button>
            <button className="landing-secondary" type="button" onClick={viewPipelineDemo} disabled={isCreatingDemo}>
              {isCreatingDemo ? "Creating..." : "查看流程演示"}
            </button>
          </div>
          <p className="landing-cta-note">无需配置 · 即刻体验</p>
        </div>

        <div className="landing-preview-stack" id="landing-preview">
          <section className="landing-preview-card" aria-label="AI DevFlow Pipeline preview">
            <div className="preview-header">
              <div>
                <span className="landing-kicker">实时流程</span>
                <h2>AI 研发流程</h2>
              </div>
              <span className="preview-live-pill">运行中</span>
            </div>

            <div className="preview-timeline">
              {previewStages.map((stage, index) => (
                <article className="preview-stage" key={stage.title}>
                  <div className={`preview-node ${stage.tone}`} aria-hidden="true">
                    {stage.tone === "completed" ? "✓" : ""}
                  </div>
                  {index < previewStages.length - 1 && <span className="preview-line" aria-hidden="true" />}
                  <div className="preview-stage-copy">
                    <h3>{stage.title}</h3>
                    {stage.checkpoint && (
                      <p className={`preview-checkpoint ${stage.tone}`}>
                        <span aria-hidden="true">✓</span>
                        {stage.checkpoint}
                      </p>
                    )}
                  </div>
                  <span className={`preview-status ${stage.tone}`}>{stage.status}</span>
                </article>
              ))}
            </div>

            <div className="preview-capabilities">
              {capabilityTags.map((item) => (
                <div className="capability-tag" key={item.title}>
                  <span aria-hidden="true">{item.icon}</span>
                  <div>
                    <strong>{item.title}</strong>
                    <small>{item.description}</small>
                  </div>
                </div>
              ))}
            </div>
          </section>
          <div className="landing-preview-shadow-card" aria-hidden="true" />
        </div>
      </section>

      <section className="landing-features" id="features" aria-labelledby="features-title">
        <div className="landing-features-heading">
          <span className="landing-kicker">PRODUCT CAPABILITIES</span>
          <h2 id="features-title">产品能力</h2>
        </div>
        <div className="landing-feature-grid">
          {capabilityTags.map((item) => (
            <article className="landing-feature-card" key={item.title}>
              <span aria-hidden="true">{item.icon}</span>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
