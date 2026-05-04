import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createPipeline } from "../api/pipelines";
import { exampleRequirement } from "../data/mockPipeline";
import type { ProviderDefinition } from "../types/pipeline";

type Props = {
  providers: ProviderDefinition[];
  selectedProvider: ProviderDefinition | null;
  selectedModel: string;
  onProviderChange: (providerId: string) => void;
  onModelChange: (model: string) => void;
};
const placeholderPrompts = [
  "优化登录页面交互体验",
  "为任务列表增加筛选和排序功能",
  "设计一个数据仪表盘页面",
  "实现一个简单的聊天界面",
];
const flowStages = ["需求", "方案", "代码", "测试", "评审", "交付"];

export default function RequirementInput({ providers, selectedProvider, selectedModel, onProviderChange, onModelChange }: Props) {
  const [value, setValue] = useState("");
  const [promptIndex, setPromptIndex] = useState(0);
  const [promptVisible, setPromptVisible] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
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

  const startPipeline = async () => {
    if (isStarting) return;

    const requirement = hasInput ? value.trim() : exampleRequirement;
    if (!hasInput) setValue(requirement);

    setIsStarting(true);
    setStartError(null);

    try {
      const pipeline = await createPipeline({
        name: "AI DevFlow Pipeline",
        requirement,
        provider: selectedProvider?.id ?? selectedModel,
        model: selectedModel || selectedProvider?.default_model || undefined,
        repo_path: import.meta.env.VITE_DELIVERAX_REPO_PATH || undefined,
      });
      loadingTimerRef.current = window.setTimeout(() => {
        navigate(`/pipeline/${encodeURIComponent(pipeline.id)}`);
      }, 320);
    } catch (error) {
      setStartError(error instanceof Error ? error.message : "Failed to create pipeline");
      setIsStarting(false);
    }
  };

  return (
    <section className="requirement-card" aria-label="需求输入">
      <div className="requirement-header">
        <div className="section-heading">
          <h2>描述你希望 AI 推进的前端变更</h2>
        </div>
        <div className="model-picker" aria-label="Provider 与模型选择">
          <label>
            <span className="model-label">Provider：</span>
            <select
              value={selectedProvider?.id ?? ""}
              onChange={(event) => onProviderChange(event.target.value)}
              aria-label="选择 Provider"
            >
              {providers.length === 0 && <option value="">加载中…</option>}
              {providers.map((p) => (
                <option key={p.id} value={p.id} disabled={!p.available}>
                  {p.name}{!p.available ? " (不可用)" : ""}{p.configured ? "" : " (未配置)"}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="model-label">模型：</span>
            <select
              value={selectedModel}
              onChange={(event) => onModelChange(event.target.value)}
              aria-label="选择模型"
            >
              {(selectedProvider?.models ?? []).map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
              {(!selectedProvider || selectedProvider.models.length === 0) && (
                <option value="">无可用模型</option>
              )}
            </select>
          </label>
          {selectedProvider && !selectedProvider.configured && (
            <small>⚠️ 未配置 API Key ({selectedProvider.api_key_env})</small>
          )}
          {selectedProvider?.notes && <small>{selectedProvider.notes}</small>}
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
      {startError && <p className="ai-input-hint error">{startError}</p>}
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
