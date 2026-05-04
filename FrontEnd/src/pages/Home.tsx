import { useState } from "react";
import AppNav from "../components/AppNav";
import RequirementInput from "../components/RequirementInput";
import type { LLMProvider } from "../types/pipeline";

export default function Home() {
  const [selectedModel, setSelectedModel] = useState<LLMProvider>("GPT-4");

  return (
    <main className="home-page">
      <div className="home-grid-overlay" aria-hidden="true" />
      <div className="home-glow home-glow-right" aria-hidden="true" />
      <div className="home-glow home-glow-left" aria-hidden="true" />

      <AppNav active="start" />

      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">AI DevFlow Workbench</span>
          <h1>
            从需求到代码的
            <span>自动化研发工作台</span>
          </h1>
          <p className="hero-description">
            输入一个前端变更需求，系统会拆解 PRD、方案、代码、测试和评审节点，并在关键检查点交给你确认。
          </p>
          <div className="hero-metrics" aria-label="DevFlow 摘要">
            <span><strong>6</strong> 个自动化节点</span>
            <span><strong>2</strong> 个人工检查点</span>
            <span><strong>18s</strong> 演示交付链路</span>
          </div>
        </div>
      </section>

      <RequirementInput selectedModel={selectedModel} onModelChange={setSelectedModel} />
    </main>
  );
}
