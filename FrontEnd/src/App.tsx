import { Navigate, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import Landing from "./pages/Landing";
import PipelineDetail from "./pages/PipelineDetail";
import PipelineList from "./pages/PipelineList";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/home" element={<Home />} />
      <Route path="/pipelines" element={<PipelineList />} />
      <Route path="/pipeline/:pipelineId" element={<PipelineDetail />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
