import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listPipelines, startPipeline, pausePipeline, resumePipeline, terminatePipeline } from "../api/pipelines";
import type { PipelineRecord, Stage } from "../types/pipeline";

const statusLabel: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  paused: "Paused",
  pending_approval: "Waiting Review",
  succeeded: "Completed",
  failed: "Failed",
  rejected: "Rejected",
  cancelled: "Cancelled",
  terminated: "Terminated",
};

function currentStageName(stages: Stage[]): string {
  const active = stages.find((s) => s.status === "running" || s.status === "pending_approval");
  if (active) return active.name;
  for (let i = stages.length - 1; i >= 0; i--) {
    if (stages[i].status === "succeeded") return stages[i].name;
  }
  return stages[0]?.name ?? "—";
}

function progressText(stages: Stage[]): string {
  const succeeded = stages.filter((s) => s.status === "succeeded").length;
  return `${succeeded}/${stages.length}`;
}

export default function PipelineList() {
  const [pipelines, setPipelines] = useState<PipelineRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actingIds, setActingIds] = useState<Set<string>>(new Set());
  const navigate = useNavigate();

  const refresh = useCallback(async () => {
    try {
      const list = await listPipelines();
      setPipelines(list);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load pipelines");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll for active pipelines
  useEffect(() => {
    const hasActive = pipelines.some((p) =>
      ["queued", "running", "pending_approval"].includes(p.status)
    );
    if (!hasActive) return;

    const timer = window.setInterval(refresh, 2000);
    return () => window.clearInterval(timer);
  }, [pipelines, refresh]);

  const action = async (pipelineId: string, fn: (id: string) => Promise<unknown>) => {
    setActingIds((prev) => new Set(prev).add(pipelineId));
    try {
      await fn(pipelineId);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActingIds((prev) => {
        const next = new Set(prev);
        next.delete(pipelineId);
        return next;
      });
    }
  };

  if (loading) {
    return (
      <main className="pipeline-page">
        <div className="pipeline-header">
          <div>
            <span className="eyebrow">DeliveraX / Pipelines</span>
            <h1>Loading pipelines...</h1>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="pipeline-page">
      <header className="pipeline-header">
        <div>
          <span className="eyebrow">DeliveraX / DevFlow Engine</span>
          <h1>Pipelines</h1>
        </div>
        <Link to="/home" className="button primary">创建新 Pipeline</Link>
      </header>

      {error && <div className="floating-log-strip" aria-live="polite"><span>{error}</span></div>}

      {pipelines.length === 0 ? (
        <section className="detail-panel" style={{ textAlign: "center", marginTop: 24 }}>
          <p>暂无 Pipeline，前往 <Link to="/home">首页</Link> 创建。</p>
        </section>
      ) : (
        <section className="pipeline-list-grid">
          {pipelines.map((p) => (
            <article key={p.id} className="pipeline-list-card">
              <div className="pipeline-list-header">
                <strong>{p.name}</strong>
                <span className={`status-pill ${p.status}`}>
                  {statusLabel[p.status] ?? p.status}
                </span>
              </div>
              <div className="pipeline-list-meta">
                <span>Provider: {p.provider}</span>
                {p.model && <span>Model: {p.model}</span>}
                <span>Stage: {currentStageName(p.stages)}</span>
                <span>进度: {progressText(p.stages)}</span>
                <span>更新: {new Date(p.updated_at).toLocaleString("zh-CN")}</span>
              </div>
              <div className="pipeline-list-actions">
                <button
                  className="button ghost"
                  type="button"
                  onClick={() => navigate(`/pipeline/${encodeURIComponent(p.id)}`)}
                >
                  查看
                </button>
                {p.status === "queued" && (
                  <button className="button primary" type="button" disabled={actingIds.has(p.id)}
                    onClick={() => action(p.id, (id) => startPipeline(id))}>
                    启动
                  </button>
                )}
                {p.status === "running" && (
                  <>
                    <button className="button secondary" type="button" disabled={actingIds.has(p.id)}
                      onClick={() => action(p.id, (id) => pausePipeline(id))}>
                      暂停
                    </button>
                    <button className="button danger" type="button" disabled={actingIds.has(p.id)}
                      onClick={() => action(p.id, (id) => terminatePipeline(id))}>
                      终止
                    </button>
                  </>
                )}
                {p.status === "paused" && (
                  <>
                    <button className="button primary" type="button" disabled={actingIds.has(p.id)}
                      onClick={() => action(p.id, (id) => resumePipeline(id))}>
                      恢复
                    </button>
                    <button className="button danger" type="button" disabled={actingIds.has(p.id)}
                      onClick={() => action(p.id, (id) => terminatePipeline(id))}>
                      终止
                    </button>
                  </>
                )}
                {p.status === "pending_approval" && (
                  <button className="button danger" type="button" disabled={actingIds.has(p.id)}
                    onClick={() => action(p.id, (id) => terminatePipeline(id))}>
                    终止
                  </button>
                )}
              </div>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
