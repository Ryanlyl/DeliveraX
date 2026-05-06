import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import AppNav from "../components/AppNav";
import PipelineList from "../components/PipelineList";
import WorkspaceHeader from "../components/WorkspaceHeader";
import RequirementIntakeCard from "../components/RequirementIntakeCard";
import { Api } from "../api/client";
import type { PipelineRecord } from "../api/client";

export default function Home() {
  const [pipelines, setPipelines] = useState<PipelineRecord[]>([]);
  const [loadingPipelines, setLoadingPipelines] = useState(true);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const projectId = searchParams.get("project_id");

  const fetchPipelines = useCallback(async () => {
    setLoadingPipelines(true);
    setPipelineError(null);
    try {
      const list = await Api.listPipelines(projectId);
      setPipelines(list);
    } catch (e) {
      setPipelineError(e instanceof Error ? e.message : "Failed to load pipelines");
    } finally {
      setLoadingPipelines(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchPipelines();
  }, [fetchPipelines]);

  const projectContext = useMemo(() => {
    const projectId = searchParams.get("project_id");
    const repoPath = searchParams.get("repo_path");
    if (projectId && repoPath) {
      return { project_id: projectId, repo_path: repoPath };
    }
    return undefined;
  }, [searchParams]);

  const handlePipelineClick = (p: PipelineRecord) => {
    navigate(`/pipeline/${p.id}`);
  };

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      {/* Background decoration */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute top-0 right-0 w-[480px] h-[480px] rounded-full blur-[80px] opacity-[0.06] bg-blue-500 -translate-y-1/4 translate-x-1/4" />
        <div className="absolute bottom-0 left-0 w-[360px] h-[360px] rounded-full blur-[80px] opacity-[0.04] bg-cyan-400 translate-y-1/4 -translate-x-1/4" />
      </div>

      <div className="relative z-10">
        {/* Top nav */}
        <div className="max-w-7xl mx-auto px-6 pt-4">
          <AppNav active="dashboard" />
        </div>

        {/* Main two-column layout */}
        <div className="max-w-7xl mx-auto px-6 pt-6 pb-12">
          <div className="flex gap-6 items-start max-lg:flex-col">
            {/* Left: Pipeline list (35%) */}
            <div className="w-[35%] shrink-0 max-lg:w-full">
              <PipelineList
                pipelines={pipelines}
                loading={loadingPipelines}
                error={pipelineError}
                onRetry={fetchPipelines}
                onPipelineClick={handlePipelineClick}
              />
            </div>

            {/* Right: Workspace (65%) */}
            <div className="flex-1 min-w-0 flex flex-col gap-5">
              <WorkspaceHeader />
              <RequirementIntakeCard projectContext={projectContext} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
