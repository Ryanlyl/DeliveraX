import { useEffect, useState } from "react";
import { Api } from "../api/client";
import type { ProviderInfo } from "../api/client";

export type ProviderSelection = {
  providerId: string;
  modelId: string;
};

type Props = {
  value: ProviderSelection;
  onChange: (selection: ProviderSelection) => void;
  disabled?: boolean;
};

export default function ModelConfigPanel({ value, onChange, disabled }: Props) {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Api.listProviders()
      .then((list) => {
        setProviders(list);
        setLoading(false);
      })
      .catch(() => {
        setProviders([
          {
            id: "deepseek",
            name: "DeepSeek",
            kind: "openai-compatible",
            available: true,
            configured: true,
            default_model: "deepseek-chat",
            default_base_url: "https://api.deepseek.com",
            api_key_env: "DEEPSEEK_API_KEY",
            models: ["deepseek-chat"],
          },
        ]);
        setLoading(false);
      });
  }, []);

  const selectedProvider = providers.find((p) => p.id === value.providerId);
  const models = selectedProvider?.models ?? [];

  const handleProviderChange = (providerId: string) => {
    const provider = providers.find((p) => p.id === providerId);
    const modelId = provider?.default_model ?? provider?.models[0] ?? "deepseek-chat";
    onChange({ providerId, modelId });
  };

  const handleModelChange = (modelId: string) => {
    onChange({ ...value, modelId });
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <div className="w-3 h-3 border-2 border-slate-200 border-t-blue-500 rounded-full animate-spin" />
        加载模型列表…
      </div>
    );
  }

  if (providers.length === 0) {
    return <p className="text-xs text-slate-400">暂无可用的 Provider</p>;
  }

  const selectClass =
    "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-colors appearance-none bg-[length:8px_8px] bg-[position:right_12px_center] bg-no-repeat";
  // inline SVG arrow encoded as data URI for the select dropdown arrow
  const selectStyle = {
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 8 8'%3E%3Cpath d='M0 2l4 4 4-4' fill='none' stroke='%2394a3b8' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
  } as React.CSSProperties;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <label className="flex-1">
          <span className="block text-[11px] font-bold uppercase tracking-wide text-slate-400 mb-1">
            Provider
          </span>
          <select
            value={value.providerId}
            onChange={(e) => handleProviderChange(e.target.value)}
            disabled={disabled}
            className={selectClass}
            style={selectStyle}
            aria-label="选择 Provider"
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex-1">
          <span className="block text-[11px] font-bold uppercase tracking-wide text-slate-400 mb-1">
            Model
          </span>
          <select
            value={value.modelId}
            onChange={(e) => handleModelChange(e.target.value)}
            disabled={disabled || models.length === 0}
            className={selectClass}
            style={selectStyle}
            aria-label="选择模型"
          >
            {models.length === 0 ? (
              <option value="">请选择模型</option>
            ) : (
              models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))
            )}
          </select>
        </label>
      </div>
      <p className="text-[10px] text-slate-400">
        支持 OpenAI / Anthropic / Local
      </p>
    </div>
  );
}
