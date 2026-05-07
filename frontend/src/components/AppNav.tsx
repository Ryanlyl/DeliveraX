import type { MouseEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

type Props = {
  active?: "dashboard" | "start" | "projects";
  onFeaturesClick?: (e: MouseEvent) => void;
  variant?: "landing" | "app";
};

const labels = {
  enterDeliveraX: "\u8fdb\u5165 DeliveraX",
  dashboard: "\u5de5\u4f5c\u53f0",
  capabilities: "\u4ea7\u54c1\u80fd\u529b",
  projects: "\u9879\u76ee\u4ed3\u5e93",
  importProject: "\u5bfc\u5165\u9879\u76ee",
  newPipeline: "\u65b0\u5efa\u6d41\u7a0b",
} as const;

export default function AppNav({ active, onFeaturesClick, variant = "landing" }: Props) {
  const navigate = useNavigate();
  const startDevFlow = () => navigate("/dashboard");
  const goLanding = () => navigate("/");
  const goNewProject = () => navigate("/projects/new");
  const isAppVariant = variant === "app";

  const navClass = isAppVariant ? "app-nav" : "landing-nav";
  const brandClass = isAppVariant ? "app-brand" : "landing-brand";
  const brandSymbolClass = isAppVariant ? "app-brand-symbol" : "landing-brand-symbol";
  const brandCopyClass = isAppVariant ? "app-brand-copy" : "landing-brand-copy";
  const centerClass = isAppVariant ? "app-nav-center" : "landing-nav-center";
  const linksClass = isAppVariant ? "app-nav-links" : "landing-nav-links";
  const loginClass = isAppVariant ? "app-login" : "landing-login";
  const ctaClass = isAppVariant ? "app-nav-cta" : "landing-nav-cta";

  return (
    <nav className={navClass}>
      <button className={brandClass} type="button" onClick={goLanding} aria-label={labels.enterDeliveraX}>
        <span className={brandSymbolClass} aria-hidden="true">
          D
        </span>
        <span className={brandCopyClass}>
          <strong>DeliveraX</strong>
          <small>DevFlow Engine</small>
        </span>
      </button>

      <div className={centerClass} aria-label="Primary navigation">
        <Link className={active === "dashboard" ? "active" : ""} to="/dashboard">
          {labels.dashboard}
        </Link>
        <Link to="/#features" onClick={(e) => onFeaturesClick?.(e)}>
          {labels.capabilities}
        </Link>
        <Link className={active === "projects" ? "active" : ""} to="/projects">
          {labels.projects}
        </Link>
      </div>

      <div className={linksClass}>
        <button className={loginClass} type="button" onClick={goNewProject}>
          {labels.importProject}
        </button>
        <button className={`${ctaClass} ${active === "start" ? "active" : ""}`} type="button" onClick={startDevFlow}>
          {labels.newPipeline}
        </button>
      </div>
    </nav>
  );
}
