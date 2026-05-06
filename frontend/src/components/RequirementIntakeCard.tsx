import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Api } from "../api/client";
import ModelConfigPanel from "./ModelConfigPanel";
import StageStepper from "./StageStepper";
import type { ProviderSelection } from "./ModelConfigPanel";

type ProjectContext = {
  project_id: string;
  repo_path: string;
};

type Props = {
  projectContext?: ProjectContext;
};

const placeholderPrompts = [
  "优化登录页面交互体验",
  "为任务列表增加筛选和排序功能",
  "设计一个数据仪表盘页面",
  "实现一个简单的聊天界面",
];

const exampleChips = ["按钮视觉升级", "列表筛选排序", "仪表盘页面", "聊天交互"];

export default function RequirementIntakeCard({ projectContext }: Props) {
  const [value, setValue] = useState("");
  const [promptIndex, setPromptIndex] = useState(0);
  const [promptVisible, setPromptVisible] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<ProviderSelection>({
    providerId: "local",
    modelId: "local",
  });
  const navigate = useNavigate();
  const hasInput = value.trim().length > 0;

  const handleSelectionChange = useCallback((sel: ProviderSelection) => {
    setSelection(sel);
  }, []);

  // Rotating placeholder effect
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

  const startPipelineFlow = async () => {
    if (isStarting) return;

    if (!hasInput) {
      setError("请输入开发需求描述");
      return;
    }

    setError(null);
    setIsStarting(true);

    try {
      const pipeline = await Api.createPipeline({
        requirement: value.trim(),
        provider: selection.providerId || undefined,
        model: selection.modelId || undefined,
        repo_path: projectContext?.repo_path || undefined,
      });

      const run = await Api.startPipeline(pipeline.id, {
        repo_path: projectContext?.repo_path || undefined,
      });

      const params = new URLSearchParams({ run_id: run.id });
      if (projectContext) {
        params.set("project_id", projectContext.project_id);
        params.set("repo_path", projectContext.repo_path);
      }
      navigate(`/pipeline/${pipeline.id}?${params.toString()}`);
    } catch (e) {
      const message =
        e instanceof Error ? e.message : "创建流程失败，请检查后端服务是否可用";
      setError(message);
      setIsStarting(false);
    }
  };

  return (
    <form
      id="requirement-intake-form"
      onSubmit={(e) => {
        e.preventDefault();
        startPipelineFlow();
      }}
      className="bg-white rounded-xl border border-slate-200 shadow-sm"
    >
      {/* Card header */}
      <div className="px-6 pt-6 pb-0">
        <div className="flex items-start justify-between gap-6">
          <div className="flex-1 min-w-0">
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-500">
              Requirement Intake
            </span>
            <h3 className="mt-2 text-lg font-bold text-slate-900">
              描述你希望 AI 推进的前端变更
            </h3>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              建议写清页面、目标、交互状态和验收标准，AI 会把它整理成可审阅的研发链路。
            </p>
          </div>

          {/* Model config inside card top-right */}
          <div className="shrink-0 w-64">
            <div className="rounded-lg border border-slate-100 bg-slate-50/70 px-4 py-3">
              <span className="text-[11px] font-bold uppercase tracking-wide text-slate-500">
                模型配置
              </span>
              <div className="mt-2">
                <ModelConfigPanel value={selection} onChange={handleSelectionChange} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Textarea */}
      <div className="px-6 pt-4">
        <div className="relative">
          <textarea
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
              setError(null);
            }}
            aria-label="描述开发需求"
            placeholder=" "
            className="w-full min-h-[180px] resize-y rounded-xl border border-slate-200 bg-slate-50/50 px-5 py-4 text-sm text-slate-900 outline-none transition-all placeholder:text-transparent focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100 leading-relaxed"
          />
          {!hasInput && (
            <div
              className={`absolute top-4 left-5 right-5 grid gap-2 pointer-events-none transition-all duration-200 ${
                promptVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-0.5"
              }`}
              aria-hidden="true"
            >
              <span className="text-sm text-slate-400 font-medium">
                描述你希望 AI 帮你完成的开发需求，例如：
              </span>
              <strong className="text-sm text-slate-500 font-bold">
                {placeholderPrompts[promptIndex]}
              </strong>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <p className="mt-3 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        {/* Hint */}
        {hasInput && !error && (
          <p className="mt-3 text-xs text-slate-400">
            AI 将为你生成：页面结构 + 交互逻辑 + API 定义
          </p>
        )}

        {/* Quick chips */}
        {!hasInput && (
          <div className="flex flex-wrap gap-2 mt-3">
            {exampleChips.map((chip, index) => (
              <button
                key={chip}
                type="button"
                onClick={() => setValue(placeholderPrompts[index])}
                className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-500 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
              >
                {chip}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Stage stepper */}
      <div className="px-6 py-4 mx-6 mt-4 bg-slate-50/70 rounded-xl border border-slate-100">
        <StageStepper activeIndex={hasInput ? 0 : -1} />
      </div>

      {/* Actions */}
      <div className="px-6 py-4 flex items-center justify-end gap-3 border-t border-slate-100 mt-5">
        <button
          type="submit"
          disabled={isStarting}
          className={`inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold text-white shadow-md transition-all
            ${isStarting
              ? "bg-slate-400 cursor-not-allowed shadow-none"
              : "bg-gradient-to-r from-blue-500 to-blue-600 shadow-blue-500/25 hover:from-blue-600 hover:to-blue-700 hover:shadow-lg hover:shadow-blue-500/30 hover:-translate-y-px"
            }`}
        >
          {isStarting && (
            <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          )}
          {isStarting ? "正在创建流程…" : "启动 AI 开发流程"}
        </button>
      </div>
    </form>
  );
}
