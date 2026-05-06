import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppNav from "../components/AppNav";
import DevFlowConsole from "../components/DevFlowConsole";
import { Api } from "../api/client";
import type { PipelineRecord, ProjectRecord } from "../api/client";

export default function ProjectDashboard() {
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pipelines, setPipelines] = useState<PipelineRecord[]>([]);
  const [pipelinesLoading, setPipelinesLoading] = useState(false);
  const navigate = useNavigate();

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await Api.listProjects();
      setProjects(data);
      if (data.length > 0) setSelectedId((prev) => prev ?? data[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    if (!selectedId) {
      setPipelines([]);
      return;
    }
    setPipelinesLoading(true);
    Api.listPipelines()
      .then((all) => {
        const project = projects.find((p) => p.id === selectedId);
        setPipelines(project ? all.filter((p) => project.pipeline_ids.includes(p.id)) : []);
        setPipelinesLoading(false);
      })
      .catch(() => setPipelinesLoading(false));
  }, [selectedId, projects]);

  const selectedProject = projects.find((p) => p.id === selectedId) ?? null;

  const statusLabel: Record<string, string> = {
    pending: "待克隆",
    cloning: "克隆中",
    ready: "就绪",
    failed: "失败",
  };

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

  return (
    <main className="project-dashboard">
      <AppNav active="projects" />

      <div className="dashboard-layout">
        <aside className="dashboard-sidebar">
          <div className="sidebar-header">
            <h2>项目列表</h2>
            <button className="landing-primary small" type="button" onClick={() => navigate("/projects/new")}>
              + 新建
            </button>
          </div>

          {loading && (
            <p className="sidebar-loading">加载中...</p>
          )}

          {error && (
            <div className="sidebar-empty">
              <p>加载失败：{error}</p>
              <button className="landing-primary small" type="button" onClick={fetchProjects}>
                重试
              </button>
            </div>
          )}

          {!loading && !error && projects.length === 0 && (
            <div className="sidebar-empty">
              <p>暂无项目</p>
              <button className="landing-primary" type="button" onClick={() => navigate("/projects/new")}>
                新建项目
              </button>
            </div>
          )}

          {!loading && !error &&
            projects.map((project) => (
              <button
                key={project.id}
                className={`project-list-item ${selectedId === project.id ? "selected" : ""}`}
                type="button"
                onClick={() => setSelectedId(project.id)}
              >
                <div className="project-list-item-header">
                  <strong>{project.name}</strong>
                  <span className={`project-status-dot ${project.clone_status}`}>
                    {statusLabel[project.clone_status] || project.clone_status}
                  </span>
                </div>
                <span className="project-list-item-repo">
                  {project.github_url.replace("https://github.com/", "")}
                </span>
                <span className="project-list-item-count">
                  {project.pipeline_ids.length} 个流程
                </span>
              </button>
            ))}
        </aside>

        <div className="dashboard-main">
          <div className="dashboard-pipeline-panel">
            {!selectedProject ? (
              <div className="dashboard-placeholder">
                <h3>选择项目查看 Pipeline</h3>
                <p>从左侧项目列表中选择一个项目，查看其 Pipeline 执行状态与详情。</p>
              </div>
            ) : (
              <>
                <div className="pipeline-panel-header">
                  <div>
                    <h3>{selectedProject.name}</h3>
                    {selectedProject.description && (
                      <p className="pipeline-panel-desc">{selectedProject.description}</p>
                    )}
                    <span className="pipeline-panel-repo">
                      {selectedProject.github_url}
                    </span>
                  </div>
                  <button
                    className="landing-primary small"
                    type="button"
                    onClick={() =>
                      navigate(
                        `/dashboard?project_id=${selectedProject.id}&repo_path=${encodeURIComponent(selectedProject.github_url)}`,
                      )
                    }
                  >
                    新建流程
                  </button>
                </div>

                {pipelinesLoading && (
                  <p className="pipeline-panel-loading">加载流程中...</p>
                )}

                {!pipelinesLoading && pipelines.length === 0 && (
                  <div className="pipeline-panel-empty">
                    <p>该项目暂无 Pipeline</p>
                    <button
                      className="landing-primary small"
                      type="button"
                      onClick={() =>
                        navigate(
                          `/dashboard?project_id=${selectedProject.id}&repo_path=${encodeURIComponent(selectedProject.github_url)}`,
                        )
                      }
                    >
                      启动第一个流程
                    </button>
                  </div>
                )}

                {!pipelinesLoading && pipelines.length > 0 && (
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
                          <span className="pipeline-list-item-requirement">
                            {p.requirement.slice(0, 60)}
                            {p.requirement.length > 60 ? "..." : ""}
                          </span>
                        </div>
                        <div className="pipeline-list-item-right">
                          <span className={`status-pill ${p.status}`}>
                            {pipelineStatusLabel[p.status] || p.status}
                          </span>
                          <span className="pipeline-list-item-provider">{p.provider}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="dashboard-demo-panel">
            <DevFlowConsole />
          </div>
        </div>
      </div>
    </main>
  );
}
