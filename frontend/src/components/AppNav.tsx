import type { MouseEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

type Props = {
  active?: "home" | "start" | "projects" | "demo";
  onFeaturesClick?: (e: MouseEvent) => void;
};

export default function AppNav({ active = "home", onFeaturesClick }: Props) {
  const navigate = useNavigate();
  const startDevFlow = () => navigate("/home");
  const goLanding = () => navigate("/");
  const goProjects = () => navigate("/projects");
  const goNewProject = () => navigate("/projects/new");

  return (
    <nav className="landing-nav">
      <button className="landing-brand" type="button" onClick={goLanding} aria-label="进入 DeliveraX">
        <span className="landing-brand-symbol" aria-hidden="true">D</span>
        <span className="landing-brand-copy">
          <strong>DeliveraX</strong>
          <small>DevFlow Engine</small>
        </span>
      </button>
      <div className="landing-nav-center" aria-label="Primary navigation">
        <Link className={active === "home" ? "active" : ""} to="/">
          工作台
        </Link>
        <Link to="/#features" onClick={(e) => onFeaturesClick?.(e)}>
          产品能力
        </Link>
        <Link className={active === "projects" ? "active" : ""} to="/projects">
          项目仓库
        </Link>
        <Link className={active === "demo" ? "active" : ""} to="/pipeline/demo-001?model=GPT-4">
          流程演示
        </Link>
      </div>
      <div className="landing-nav-links">
        <button className="landing-login" type="button" onClick={goNewProject}>
          导入项目
        </button>
        <button className={`landing-nav-cta ${active === "start" ? "active" : ""}`} type="button" onClick={startDevFlow}>
          新建流程
        </button>
      </div>
    </nav>
  );
}
