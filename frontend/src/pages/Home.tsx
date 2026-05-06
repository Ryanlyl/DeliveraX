import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import AppNav from "../components/AppNav";
import RequirementInput from "../components/RequirementInput";
import { Api } from "../api/client";
import type { PipelineRecord } from "../api/client";

const pipelineStatusLabel: Record<string, string> = {
  queued: "排队中",
  running: "运行中",
  paused: "已暂停",
  pending_approval: "待审核",
  succeeded: "已完成",
  failed: "失败",
  rejected: "已拒绝",
  cancelled: "已取消",
  terminated: "已终止",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("zh-CN");
}

export default function Home() {
  const [pipelines, setPipelines] = useState<PipelineRecord[]>([]);
  const [loadingPipelines, setLoadingPipelines] = useState(true);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // ── pipelines ──

  const fetchPipelines = useCallback(async () => {
    setLoadingPipelines(true);
    setPipelineError(null);
    try {
      const list = await Api.listPipelines();
      setPipelines(list);
    } catch (e) {
      setPipelineError(e instanceof Error ? e.message : "Failed to load pipelines");
    } finally {
      setLoadingPipelines(false);
    }
  }, []);

  useEffect(() => {
    fetchPipelines();
  }, [fetchPipelines]);

  // ── project context (from URL params via project page) ──

  const projectContext = useMemo(() => {
    const projectId = searchParams.get("project_id");
    const repoPath = searchParams.get("repo_path");
    if (projectId && repoPath) {
      return { project_id: projectId, repo_path: repoPath };
    }
    return undefined;
  }, [searchParams]);

  const currentStageLabel = (p: PipelineRecord): string => {
    const active = p.stages.find(
      (s) => s.status === "running" || s.status === "pending_approval",
    );
    if (active) return active.name;
    if (p.stages.length > 0) {
      const lastDone = [...p.stages].reverse().find((s) => s.status === "succeeded");
      if (lastDone) return lastDone.name;
    }
    return "—";
  };

  return (
    <main className="home-page">
      <div className="home-grid-overlay" aria-hidden="true" />
      <div className="home-glow home-glow-right" aria-hidden="true" />
      <div className="home-glow home-glow-left" aria-hidden="true" />

      <AppNav active="dashboard" />

      {/* ── Pipeline list ── */}
      <section className="dashboard-pipeline-section">
        <div className="dashboard-header">
          <div>
            <span className="eyebrow">Pipeline Dashboard</span>
            <h1>AI DevFlow 流程列表</h1>
            <p>管理和追踪所有 AI 驱动的开发流程。</p>
          </div>
          {!loadingPipelines && !pipelineError && (
            <span className="pipeline-count">{pipelines.length} 个流程</span>
          )}
        </div>

        {loadingPipelines && (
          <div className="dashboard-status">
            <span className="spinner" aria-hidden="true" />
            <p>加载流程列表...</p>
          </div>
        )}

        {pipelineError && (
          <div className="dashboard-status dashboard-error">
            <p>加载失败：{pipelineError}</p>
            <button className="button primary small" type="button" onClick={fetchPipelines}>
              重试
            </button>
          </div>
        )}

        {!loadingPipelines && !pipelineError && pipelines.length === 0 && (
          <div className="dashboard-status">
            <p>暂无流程，请在下方创建第一个 DevFlow。</p>
          </div>
        )}

        {!loadingPipelines && !pipelineError && pipelines.length > 0 && (
          <div className="pipeline-list">
            {pipelines.map((p) => (
              <button
                key={p.id}
                className="pipeline-list-item"
                type="button"
                onClick={() => navigate(`/pipeline/${p.id}`)}
              >
                <div className="pipeline-list-item-left">
                  <strong className="pipeline-list-item-name">{p.name}</strong>
                  <span className="pipeline-list-item-id">ID: {p.id}</span>
                  <span className="pipeline-list-item-requirement">
                    {p.requirement.slice(0, 80)}
                    {p.requirement.length > 80 ? "..." : ""}
                  </span>
                </div>
                <div className="pipeline-list-item-center">
                  <span className="pipeline-list-item-stage">
                    当前阶段：{currentStageLabel(p)}
                  </span>
                  <span className="pipeline-list-item-provider">
                    {p.provider}{p.model ? ` / ${p.model}` : ""}
                  </span>
                </div>
                <div className="pipeline-list-item-right">
                  <span className={`status-pill ${p.status}`}>
                    {pipelineStatusLabel[p.status] || p.status}
                  </span>
                  <span className="pipeline-list-item-date">
                    {formatDate(p.created_at)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* ── Create pipeline ── */}
      <RequirementInput projectContext={projectContext} />
    </main>
  );
}
