import { Navigate, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import Landing from "./pages/Landing";
import PipelineDetail from "./pages/PipelineDetail";
import ProjectDashboard from "./pages/ProjectDashboard";
import ProjectNew from "./pages/ProjectNew";
import ProjectDetail from "./pages/ProjectDetail";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Home />} />
      <Route path="/pipeline/:pipelineId" element={<PipelineDetail />} />
      <Route path="/projects" element={<ProjectDashboard />} />
      <Route path="/projects/new" element={<ProjectNew />} />
      <Route path="/projects/:projectId" element={<ProjectDetail />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
