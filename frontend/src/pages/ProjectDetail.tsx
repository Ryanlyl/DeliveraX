import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppNav from "../components/AppNav";
import { Api } from "../api/client";
import type { PipelineRecord, ProjectRecord } from "../api/client";

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectRecord | null>(null);
  const [pipelines, setPipelines] = useState<PipelineRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchProject = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await Api.getProject(projectId);
      setProject(data);
      const related = await Api.listPipelines(data.id);
      setPipelines(related);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Project not found");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const refreshProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await Api.getProject(projectId);
      setProject(data);
      const related = await Api.listPipelines(data.id);
      setPipelines(related);
    } catch {
      // polling errors are silent
    }
  }, [projectId]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  useEffect(() => {
    if (!projectId || !project) return;

    const shouldPoll = project.clone_status === "pending" || project.clone_status === "cloning";
    if (!shouldPoll) return;

    const timer = window.setInterval(() => {
      refreshProject();
    }, 1000);

    return () => window.clearInterval(timer);
  }, [projectId, project?.clone_status, refreshProject]);

  const handleDelete = async () => {
    if (deleting || !projectId) return;
    setDeleting(true);
    try {
      await Api.deleteProject(projectId);
      navigate("/projects");
    } catch {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <main className="project-detail-page app-shell">
        <div className="app-grid-overlay" aria-hidden="true" />
        <AppNav active="projects" variant="app" />
        <section className="project-detail-section">
          <p className="project-detail-loading">Loading...</p>
        </section>
      </main>
    );
  }

  if (error || !project) {
    return (
      <main className="project-detail-page app-shell">
        <div className="app-grid-overlay" aria-hidden="true" />
        <AppNav active="projects" variant="app" />
        <section className="project-detail-section">
          <div className="projects-empty">
            <h3>{error ? "Load failed" : "Project not found"}</h3>
            <p>{error ?? "This project may have been deleted."}</p>
            {error ? (
              <button className="app-button app-button-primary" type="button" onClick={fetchProject}>
                Retry
              </button>
            ) : (
              <button className="app-button app-button-primary" type="button" onClick={() => navigate("/projects")}>
                Back to projects
              </button>
            )}
          </div>
        </section>
      </main>
    );
  }

  const statusLabel: Record<string, string> = {
    pending: "Pending",
    cloning: "Cloning",
    ready: "Ready",
    failed: "Failed",
  };

  const canCreatePipeline = project.clone_status === "ready" && Boolean(project.clone_path);

  const createPipelineButtonText =
    project.clone_status === "pending" || project.clone_status === "cloning"
      ? "Repository cloning..."
      : project.clone_status === "failed"
        ? "Clone failed, cannot create pipeline"
        : !project.clone_path
          ? "Missing repository path"
          : "New pipeline";

  const handleCreatePipeline = () => {
    if (!canCreatePipeline || !project.clone_path) return;
    navigate(`/dashboard?project_id=${project.id}&repo_path=${encodeURIComponent(project.clone_path)}`);
  };

  return (
    <main className="project-detail-page app-shell">
      <div className="app-grid-overlay" aria-hidden="true" />
      <div className="app-glow app-glow-right" aria-hidden="true" />
      <div className="app-glow app-glow-left" aria-hidden="true" />

      <AppNav active="projects" variant="app" />

      <section className="project-detail-section">
        <button className="project-detail-back" type="button" onClick={() => navigate("/projects")}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M10.78 12.78a.75.75 0 01-1.06 0L5.97 9.03a.75.75 0 010-1.06l3.75-3.75a.75.75 0 111.06 1.06L7.56 8.5l3.22 3.22a.75.75 0 010 1.06z"
            />
          </svg>
          Back to projects
        </button>

        <div className="project-detail-header">
          <div className="project-detail-info">
            <div className="project-detail-title-row">
              <h1>{project.name}</h1>
              <span className={`project-status-badge status-${project.clone_status}`}>
                {statusLabel[project.clone_status] || project.clone_status}
              </span>
            </div>
            {project.description && <p className="project-detail-desc">{project.description}</p>}
            <div className="project-detail-meta">
              <a className="project-detail-repo" href={project.github_url} target="_blank" rel="noopener noreferrer">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
                </svg>
                {project.github_url}
              </a>
              <span className="project-detail-created">Created at {new Date(project.created_at).toLocaleDateString("zh-CN")}</span>
            </div>
          </div>

          <div className="project-detail-actions">
            <button className="app-button app-button-primary" type="button" disabled={!canCreatePipeline} onClick={handleCreatePipeline}>
              {createPipelineButtonText}
            </button>
            <button className="button secondary danger" type="button" onClick={handleDelete} disabled={deleting}>
              {deleting ? "Deleting..." : "Delete project"}
            </button>
          </div>
        </div>

        {project.clone_status === "failed" && (
          <div
            className="project-clone-warning"
            style={{
              marginTop: "16px",
              padding: "12px 16px",
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: "8px",
              color: "#b91c1c",
              fontSize: "14px",
            }}
          >
            <div>Repository clone failed. Please check the GitHub URL and backend clone logs.</div>
            {project.clone_error && (
              <div style={{ marginTop: "8px", color: "#7f1d1d", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                Error detail: {project.clone_error}
              </div>
            )}
          </div>
        )}

        {project.clone_status === "ready" && !project.clone_path && (
          <div
            className="project-clone-warning"
            style={{
              marginTop: "16px",
              padding: "12px 16px",
              background: "#fffbeb",
              border: "1px solid #fde68a",
              borderRadius: "8px",
              color: "#92400e",
              fontSize: "14px",
            }}
          >
            Project is marked ready, but clone_path is empty. Please check backend project data.
          </div>
        )}

        <div className="project-pipelines">
          <h2>Pipelines</h2>
          {pipelines.length === 0 ? (
            <div className="projects-empty" style={{ margin: "32px 0", padding: "32px" }}>
              <p>No pipelines in this repository.</p>
              <button
                className="app-button app-button-primary"
                type="button"
                disabled={!canCreatePipeline}
                onClick={handleCreatePipeline}
                style={{ marginTop: "12px" }}
              >
                {createPipelineButtonText}
              </button>
            </div>
          ) : (
            <div className="pipeline-list">
              {pipelines.map((p) => (
                <button key={p.id} className="pipeline-item" type="button" onClick={() => navigate(`/pipeline/${p.id}`)}>
                  <div className="pipeline-item-info">
                    <h4>{p.name}</h4>
                    <span className="pipeline-item-status">{p.status}</span>
                  </div>
                  <span className="pipeline-item-provider">{p.provider}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
