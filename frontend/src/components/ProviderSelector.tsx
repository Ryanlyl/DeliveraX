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

export default function ProviderSelector({ value, onChange, disabled }: Props) {
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
            id: "local",
            name: "Local",
            kind: "local",
            available: true,
            configured: true,
            models: ["local"],
          },
        ]);
        setLoading(false);
      });
  }, []);

  const selectedProvider = providers.find((p) => p.id === value.providerId);
  const models = selectedProvider?.models ?? [];

  const handleProviderChange = (providerId: string) => {
    const provider = providers.find((p) => p.id === providerId);
    const modelId = provider?.default_model ?? provider?.models[0] ?? "local";
    onChange({ providerId, modelId });
  };

  const handleModelChange = (modelId: string) => {
    onChange({ ...value, modelId });
  };

  if (loading) {
    return (
      <div className="model-picker" aria-label="模型选择">
        <small>加载 provider 列表...</small>
      </div>
    );
  }

  if (providers.length === 0) {
    return (
      <div className="model-picker" aria-label="模型选择">
        <small>暂无可用的 provider</small>
      </div>
    );
  }

  return (
    <div className="model-picker" aria-label="模型选择">
      <label>
        <span className="model-label">Provider：</span>
        <select
          value={value.providerId}
          onChange={(e) => handleProviderChange(e.target.value)}
          disabled={disabled}
          aria-label="选择 Provider"
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="model-label">模型：</span>
        <select
          value={value.modelId}
          onChange={(e) => handleModelChange(e.target.value)}
          disabled={disabled}
          aria-label="选择模型"
        >
          {models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>
      <small>支持 OpenAI / Anthropic / Local</small>
    </div>
  );
}
