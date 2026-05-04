import { useCallback, useEffect, useState } from "react";
import AppNav from "../components/AppNav";
import RequirementInput from "../components/RequirementInput";
import { listProviders } from "../api/providers";
import type { ProviderDefinition } from "../types/pipeline";

export default function Home() {
  const [providers, setProviders] = useState<ProviderDefinition[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState<string>("");
  const [selectedModel, setSelectedModel] = useState<string>("");

  const selectedProvider = providers.find((p) => p.id === selectedProviderId) ?? null;

  useEffect(() => {
    let cancelled = false;
    listProviders()
      .then((list) => {
        if (cancelled) return;
        setProviders(list);
        const def = list.find((p) => p.available && p.configured) ?? list.find((p) => p.available) ?? list[0];
        if (def) {
          setSelectedProviderId(def.id);
          setSelectedModel(def.default_model ?? def.models[0] ?? "");
        }
      })
      .catch(() => {
        // keep defaults
      });
    return () => { cancelled = true; };
  }, []);

  const handleProviderChange = useCallback((providerId: string) => {
    setSelectedProviderId(providerId);
    const provider = providers.find((p) => p.id === providerId);
    if (provider) {
      setSelectedModel(provider.default_model ?? provider.models[0] ?? "");
    }
  }, [providers]);

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

      <RequirementInput
        providers={providers}
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        onProviderChange={handleProviderChange}
        onModelChange={setSelectedModel}
      />
    </main>
  );
}
