import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppNav from "../components/AppNav";
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
    pending: "Pending",
    cloning: "Cloning",
    ready: "Ready",
    failed: "Failed",
  };

  const pipelineStatusLabel: Record<string, string> = {
    queued: "Queued",
    running: "Running",
    paused: "Paused",
    pending_approval: "Pending approval",
    succeeded: "Succeeded",
    failed: "Failed",
    rejected: "Rejected",
    cancelled: "Cancelled",
    terminated: "Terminated",
  };

  return (
    <main className="project-dashboard app-shell">
      <AppNav active="projects" variant="app" />

      <div className="dashboard-layout">
        <aside className="dashboard-sidebar">
          <div className="sidebar-header">
            <h2>Projects</h2>
            <button
              className="app-button app-button-primary app-button-small"
              type="button"
              onClick={() => navigate("/projects/new")}
            >
              + New
            </button>
          </div>

          {loading && <p className="sidebar-loading">Loading...</p>}

          {error && (
            <div className="sidebar-empty">
              <p>Load failed: {error}</p>
              <button className="app-button app-button-primary app-button-small" type="button" onClick={fetchProjects}>
                Retry
              </button>
            </div>
          )}

          {!loading && !error && projects.length === 0 && (
            <div className="sidebar-empty">
              <p>No projects yet.</p>
              <button className="app-button app-button-primary" type="button" onClick={() => navigate("/projects/new")}>
                Create project
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
                <span className="project-list-item-repo">{project.github_url.replace("https://github.com/", "")}</span>
                <span className="project-list-item-count">{project.pipeline_ids.length} pipelines</span>
              </button>
            ))}
        </aside>

        <div className="dashboard-main">
          <div className="dashboard-pipeline-panel">
            {!selectedProject ? (
              <div className="dashboard-placeholder">
                <h3>Select a project</h3>
                <p>Pick a project from the left to inspect its pipeline list and status.</p>
              </div>
            ) : (
              <>
                <div className="pipeline-panel-header">
                  <div>
                    <h3>{selectedProject.name}</h3>
                    {selectedProject.description && <p className="pipeline-panel-desc">{selectedProject.description}</p>}
                    <span className="pipeline-panel-repo">{selectedProject.github_url}</span>
                  </div>
                  <button
                    className="app-button app-button-primary app-button-small"
                    type="button"
                    disabled={!selectedProject.clone_path}
                    onClick={() =>
                      navigate(
                        `/dashboard?project_id=${selectedProject.id}&repo_path=${encodeURIComponent(
                          selectedProject.clone_path || "",
                        )}`,
                      )
                    }
                  >
                    {selectedProject.clone_path ? "New pipeline" : "Cloning..."}
                  </button>
                </div>

                {pipelinesLoading && <p className="pipeline-panel-loading">Loading pipelines...</p>}

                {!pipelinesLoading && pipelines.length === 0 && (
                  <div className="pipeline-panel-empty">
                    <p>No pipelines yet for this project.</p>
                    <button
                      className="app-button app-button-primary app-button-small"
                      type="button"
                      disabled={!selectedProject.clone_path}
                      onClick={() =>
                        navigate(
                          `/dashboard?project_id=${selectedProject.id}&repo_path=${encodeURIComponent(
                            selectedProject.clone_path || "",
                          )}`,
                        )
                      }
                    >
                      {selectedProject.clone_path ? "Start first pipeline" : "Cloning..."}
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
                          <span className={`status-pill ${p.status}`}>{pipelineStatusLabel[p.status] || p.status}</span>
                          <span className="pipeline-list-item-provider">{p.provider}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
