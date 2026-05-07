import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AppNav from "../components/AppNav";
import { Api } from "../api/client";

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
      const project = await Api.createProject({
        name: name.trim(),
        description: description.trim() || null,
        github_url: githubUrl.trim(),
      });
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed, please retry");
      setSubmitting(false);
    }
  };

  return (
    <main className="project-new-page app-shell">
      <div className="app-grid-overlay" aria-hidden="true" />
      <div className="app-glow app-glow-right" aria-hidden="true" />
      <div className="app-glow app-glow-left" aria-hidden="true" />

      <AppNav active="projects" variant="app" />

      <section className="project-new-section">
        <div className="project-new-card">
          <div className="project-new-header">
            <span className="eyebrow">New Project</span>
            <h1>Create project</h1>
            <p>Create a project and connect a GitHub repository for subsequent DevFlow runs.</p>
          </div>

          {error && <div className="project-new-error">{error}</div>}

          <div className="project-new-field">
            <label htmlFor="project-name">Project name *</label>
            <input
              id="project-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="For example: DeliveraX Frontend"
              autoFocus
            />
          </div>

          <div className="project-new-field">
            <label htmlFor="project-desc">Project description</label>
            <textarea
              id="project-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the project purpose"
              rows={3}
            />
          </div>

          <div className="project-new-field">
            <label htmlFor="project-repo">GitHub repository URL *</label>
            <input
              id="project-repo"
              type="text"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/user/repo"
            />
            {githubUrl && !githubUrl.includes("github.com") && (
              <span className="project-new-hint error">Please enter a valid GitHub repository URL</span>
            )}
          </div>

          <div className="project-new-actions">
            <button className="button secondary" type="button" onClick={() => navigate("/projects")}>
              Cancel
            </button>
            <button className="button primary" type="button" onClick={handleSubmit} disabled={!isValid || submitting}>
              {submitting ? "Creating..." : "Create project"}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
