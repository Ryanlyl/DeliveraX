import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppNav from "../components/AppNav";
import type { Project } from "../types/pipeline";

export default function ProjectsList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetch("/api/projects")
      .then((res) => res.json())
      .then((data) => {
        setProjects(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <main className="projects-page">
      <div className="landing-grid-overlay" aria-hidden="true" />
      <div className="landing-glow landing-glow-right" aria-hidden="true" />
      <div className="landing-glow landing-glow-left" aria-hidden="true" />

      <AppNav active="projects" />

      <section className="projects-section">
        <div className="projects-header">
          <div>
            <span className="eyebrow">Project Repository</span>
            <h1>项目仓库</h1>
            <p>管理你的项目并关联 GitHub 仓库，为每个项目启动 AI DevFlow。</p>
          </div>
          <button className="landing-primary" type="button" onClick={() => navigate("/projects/new")}>
            新建项目
          </button>
        </div>

        {loading && (
          <div className="projects-empty">
            <p>加载中...</p>
          </div>
        )}

        {!loading && projects.length === 0 && (
          <div className="projects-empty">
            <div className="projects-empty-icon" aria-hidden="true">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <h3>暂无项目</h3>
            <p>创建你的第一个项目，关联 GitHub 仓库后即可启动 AI DevFlow。</p>
            <button className="landing-primary" type="button" onClick={() => navigate("/projects/new")}>
              新建项目
            </button>
          </div>
        )}

        {!loading && projects.length > 0 && (
          <div className="project-grid">
            {projects.map((project) => (
              <button
                key={project.id}
                className="project-card"
                type="button"
                onClick={() => navigate(`/projects/${project.id}`)}
              >
                <div className="project-card-header">
                  <h3>{project.name}</h3>
                  <span className={`project-status-badge status-${project.clone_status}`}>
                    {project.clone_status === "ready" ? "就绪" : project.clone_status === "failed" ? "失败" : "待克隆"}
                  </span>
                </div>
                {project.description && (
                  <p className="project-card-desc">{project.description}</p>
                )}
                <div className="project-card-meta">
                  <span className="project-card-repo" title={project.github_url}>
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
                    </svg>
                    {project.github_url.replace("https://github.com/", "")}
                  </span>
                  <span className="project-card-count">{project.pipeline_ids.length} 个流程</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
