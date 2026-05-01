import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { exampleRequirement } from "../data/mockPipeline";
import type { LLMProvider } from "../types/pipeline";

type Props = {
  selectedModel: LLMProvider;
  onModelChange: (model: LLMProvider) => void;
};

const modelOptions: LLMProvider[] = ["GPT-4", "Claude 3"];
const placeholderPrompts = [
  "优化登录页面交互体验",
  "为任务列表增加筛选和排序功能",
  "设计一个数据仪表盘页面",
  "实现一个简单的聊天界面",
];
const flowStages = ["需求", "方案", "代码", "测试", "评审", "交付"];

export default function RequirementInput({ selectedModel, onModelChange }: Props) {
  const [value, setValue] = useState("");
  const [promptIndex, setPromptIndex] = useState(0);
  const [promptVisible, setPromptVisible] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const loadingTimerRef = useRef<number | null>(null);
  const navigate = useNavigate();
  const hasInput = value.trim().length > 0;

  useEffect(() => {
    if (hasInput) return undefined;

    const interval = window.setInterval(() => {
      setPromptVisible(false);
      window.setTimeout(() => {
        setPromptIndex((current) => (current + 1) % placeholderPrompts.length);
        setPromptVisible(true);
      }, 220);
    }, 2600);

    return () => window.clearInterval(interval);
  }, [hasInput]);

  useEffect(
    () => () => {
      if (loadingTimerRef.current) window.clearTimeout(loadingTimerRef.current);
    },
    [],
  );

  const startPipeline = () => {
    if (isStarting) return;

    if (!hasInput) {
      setValue(exampleRequirement);
    }

    setIsStarting(true);
    loadingTimerRef.current = window.setTimeout(() => {
      navigate(`/pipeline/demo-001?model=${encodeURIComponent(selectedModel)}`);
    }, 700);
  };

  return (
    <section className="requirement-card" aria-label="需求输入">
      <div className="requirement-header">
        <div className="section-heading">
          <h2>描述你希望 AI 推进的前端变更</h2>
        </div>
        <div className="model-picker" aria-label="模型选择">
          <label>
            <span className="model-label">模型：</span>
            <select
              value={selectedModel}
              onChange={(event) => onModelChange(event.target.value as LLMProvider)}
              aria-label="选择模型"
            >
              {modelOptions.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>
          <small>支持 OpenAI / Anthropic</small>
        </div>
      </div>
      <div className="textarea-shell">
        <textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          aria-label="描述开发需求"
        />
        {!hasInput && (
          <div className={`dynamic-placeholder ${promptVisible ? "visible" : ""}`} aria-hidden="true">
            <span>描述你希望 AI 帮你完成的开发需求，例如：</span>
            <strong>{placeholderPrompts[promptIndex]}</strong>
          </div>
        )}
      </div>
      {hasInput && <p className="ai-input-hint">AI 将为你生成：页面结构 + 交互逻辑 + API 定义</p>}
      <div className="flow-hint" aria-label="DevFlow Pipeline stages">
        {flowStages.map((stage, index) => (
          <span className={`flow-step ${hasInput && index === 0 ? "active" : ""}`} key={stage}>
            <span className="flow-dot" aria-hidden="true" />
            <span className="flow-label">{stage}</span>
          </span>
        ))}
      </div>
      <div className="requirement-actions">
        <button className="button secondary example-button" type="button" onClick={() => setValue(exampleRequirement)}>
          使用示例需求
        </button>
        <button
          className={`button primary start-button ${hasInput ? "ready" : ""}`}
          type="button"
          onClick={startPipeline}
          disabled={isStarting}
        >
          {isStarting && <span className="button-spinner" aria-hidden="true" />}
          {isStarting ? "正在生成方案…" : "启动 AI 开发流程"}
        </button>
      </div>
    </section>
  );
}
