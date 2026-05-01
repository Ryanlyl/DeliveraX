import { Link, useNavigate } from "react-router-dom";

type Props = {
  active?: "home" | "start";
  onFeaturesClick?: () => void;
};

export default function AppNav({ active = "home", onFeaturesClick }: Props) {
  const navigate = useNavigate();
  const startDevFlow = () => navigate("/home");
  const goLanding = () => navigate("/");

  return (
    <nav className="landing-nav">
      <button className="landing-brand" type="button" onClick={goLanding} aria-label="Enter DeliveraX">
        <span className="landing-brand-symbol" aria-hidden="true" />
        <span className="landing-brand-copy">
          <strong>DeliveraX</strong>
          <small>DevFlow Engine</small>
        </span>
      </button>
      <div className="landing-nav-center" aria-label="Primary navigation">
        <Link className={active === "home" ? "active" : ""} to="/">
          首页
        </Link>
        <Link to="/#features" onClick={onFeaturesClick}>
          产品能力
        </Link>
        <Link to="/pipeline/demo-001?model=GPT-4">流程演示</Link>
      </div>
      <div className="landing-nav-links">
        <button className="landing-login" type="button">
          登录
        </button>
        <button className={`landing-nav-cta ${active === "start" ? "active" : ""}`} type="button" onClick={startDevFlow}>
          开始使用
        </button>
      </div>
    </nav>
  );
}
