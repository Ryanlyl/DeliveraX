import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AppNav from "../components/AppNav";

export default function ProjectNew() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const isValid = name.trim().length > 0 && githubUrl.trim().length > 0 && githubUrl.includes("github.com");

  const handleSubmit = async () => {
    if (!isValid || submitting) return;
    setSubmitting(true);
    setError("");

    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          github_url: githubUrl.trim(),
        }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || "创建失败");
      }
      const project = await res.json();
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败，请重试");
      setSubmitting(false);
    }
  };

  return (
    <main className="project-new-page">
      <div className="landing-grid-overlay" aria-hidden="true" />
      <div className="landing-glow landing-glow-right" aria-hidden="true" />
      <div className="landing-glow landing-glow-left" aria-hidden="true" />

      <AppNav active="projects" />

      <section className="project-new-section">
        <div className="project-new-card">
          <div className="project-new-header">
            <span className="eyebrow">New Project</span>
            <h1>新建项目</h1>
            <p>创建一个项目并关联 GitHub 仓库，后续 AI DevFlow 将基于该仓库工作。</p>
          </div>

          {error && <div className="project-new-error">{error}</div>}

          <div className="project-new-field">
            <label htmlFor="project-name">项目名称 *</label>
            <input
              id="project-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：DeliveraX Frontend"
              autoFocus
            />
          </div>

          <div className="project-new-field">
            <label htmlFor="project-desc">项目描述</label>
            <textarea
              id="project-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="简要描述项目用途..."
              rows={3}
            />
          </div>

          <div className="project-new-field">
            <label htmlFor="project-repo">GitHub 仓库地址 *</label>
            <input
              id="project-repo"
              type="text"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/user/repo"
            />
            {githubUrl && !githubUrl.includes("github.com") && (
              <span className="project-new-hint error">请输入有效的 GitHub 仓库地址</span>
            )}
          </div>

          <div className="project-new-actions">
            <button className="button secondary" type="button" onClick={() => navigate("/projects")}>
              取消
            </button>
            <button
              className="button primary"
              type="button"
              onClick={handleSubmit}
              disabled={!isValid || submitting}
            >
              {submitting ? "创建中..." : "创建项目"}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
