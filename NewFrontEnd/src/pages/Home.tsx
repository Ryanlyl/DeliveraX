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
          <h1>
            从需求到代码的
            <span>自动化交付</span>
          </h1>
          <p className="hero-description">
            输入一个需求，AI 自动完成分析、设计、编码、测试与评审，并交付可运行代码。
          </p>
        </div>
      </section>

      <RequirementInput selectedModel={selectedModel} onModelChange={setSelectedModel} />
    </main>
  );
}
