import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { exampleRequirement } from "../data/mockPipeline";
import type { LLMProvider } from "../types/pipeline";

type ProjectContext = {
  project_id: string;
  repo_path: string;
};

type Props = {
  selectedModel: LLMProvider;
  onModelChange: (model: LLMProvider) => void;
  projectContext?: ProjectContext;
};

const modelOptions: LLMProvider[] = ["GPT-4", "Claude 3"];
const placeholderPrompts = [
  "优化登录页面交互体验",
  "为任务列表增加筛选和排序功能",
  "设计一个数据仪表盘页面",
  "实现一个简单的聊天界面",
];
const flowStages = ["需求", "方案", "代码", "测试", "评审", "交付"];
const exampleChips = ["按钮视觉升级", "列表筛选排序", "仪表盘页面", "聊天交互"];

export default function RequirementInput({ selectedModel, onModelChange, projectContext }: Props) {
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
      const params = new URLSearchParams({ model: selectedModel });
      if (projectContext) {
        params.set("project_id", projectContext.project_id);
        params.set("repo_path", projectContext.repo_path);
      }
      navigate(`/pipeline/demo-001?${params.toString()}`);
    }, 700);
  };

  return (
    <section className="requirement-card" aria-label="需求输入">
      <div className="requirement-header">
        <div className="section-heading">
          <span className="eyebrow">Requirement Intake</span>
          <h2>描述你希望 AI 推进的前端变更</h2>
          <p>建议写清页面、目标、交互状态和验收标准，AI 会把它整理成可审阅的研发链路。</p>
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
      {!hasInput && (
        <div className="requirement-chip-row" aria-label="示例需求">
          {exampleChips.map((chip, index) => (
            <button key={chip} type="button" onClick={() => setValue(placeholderPrompts[index])}>
              {chip}
            </button>
          ))}
        </div>
      )}
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
          {isStarting ? "正在创建流程..." : "启动 AI 开发流程"}
        </button>
      </div>
    </section>
  );
}
