import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { approveStage, getPipeline, rejectStage, runPipeline } from "../api/pipelines";
import PipelineHeader from "../components/PipelineHeader";
import PipelineTimeline from "../components/PipelineTimeline";
import StageDetailPanel, { DESIGN_NAV_GROUPS } from "../components/StageDetailPanel";
import type { PipelineRecord, Stage } from "../types/pipeline";

const createBaseLogs = (provider: string) => [
  `Using model: ${provider}`,
  "Pipeline loaded from API server",
  "Waiting for stage updates",
];

function formatDuration(ms: number) {
  return `${(ms / 1000).toFixed(1)}s`;
}

function totalDuration(pipeline: PipelineRecord) {
  return formatDuration(pipeline.stages.reduce((total, stage) => total + stage.duration_ms, 0));
}

function currentStageId(stages: Stage[]) {
  const active = stages.find((stage) => stage.status === "pending_approval" || stage.status === "running");
  if (active) return active.id;

  const firstAvailable = stages.find((stage) => stage.status !== "queued");
  if (firstAvailable) return firstAvailable.id;

  return stages[0]?.id ?? "";
}

export default function PipelineDetail() {
  const { pipelineId = "" } = useParams();
  const [pipeline, setPipeline] = useState<PipelineRecord | null>(null);
  const [selectedStageId, setSelectedStageId] = useState("");
  const [activeDesignSection, setActiveDesignSection] = useState("meta");
  const [isLoading, setIsLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoRunIdsRef = useRef<Set<string>>(new Set());

  const activeStageId = useMemo(() => currentStageId(pipeline?.stages ?? []), [pipeline]);
  const selectedStage = useMemo(
    () => pipeline?.stages.find((stage) => stage.id === selectedStageId) ?? pipeline?.stages.find((stage) => stage.id === activeStageId) ?? pipeline?.stages[0],
    [activeStageId, pipeline, selectedStageId],
  );
  const isViewingDesign = selectedStage?.id === "solution";

  const refreshPipeline = useCallback(async () => {
    if (!pipelineId) return;
    const nextPipeline = await getPipeline(pipelineId);
    setPipeline(nextPipeline);
    setSelectedStageId((current) => {
      const currentStage = nextPipeline.stages.find((stage) => stage.id === current);
      if (currentStage && currentStage.status !== "queued") return current;
      return currentStageId(nextPipeline.stages);
    });
  }, [pipelineId]);

  useEffect(() => {
    let active = true;

    setIsLoading(true);
    setError(null);
    getPipeline(pipelineId)
      .then((nextPipeline) => {
        if (!active) return;
        setPipeline(nextPipeline);
        setSelectedStageId(currentStageId(nextPipeline.stages));
      })
      .catch((loadError) => {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : "Failed to load pipeline");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [pipelineId]);

  useEffect(() => {
    if (!pipeline || pipeline.status !== "queued" || autoRunIdsRef.current.has(pipeline.id)) return;

    autoRunIdsRef.current.add(pipeline.id);
    setIsActing(true);
    runPipeline(pipeline.id, {})
      .then(setPipeline)
      .catch((runError) => setError(runError instanceof Error ? runError.message : "Failed to run pipeline"))
      .finally(() => setIsActing(false));
  }, [pipeline]);

  useEffect(() => {
    if (!pipeline || pipeline.status !== "running") return undefined;

    const timer = window.setInterval(() => {
      refreshPipeline().catch((refreshError) => {
        setError(refreshError instanceof Error ? refreshError.message : "Failed to refresh pipeline");
      });
    }, 1200);

    return () => window.clearInterval(timer);
  }, [pipeline, refreshPipeline]);

  useEffect(() => {
    if (!isViewingDesign) return;

    const sectionIds = DESIGN_NAV_GROUPS.flatMap((group) => group.items.map((item) => item.id));
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target.id) setActiveDesignSection(visible.target.id);
      },
      { rootMargin: "-18% 0px -68% 0px", threshold: [0.12, 0.3, 0.6] },
    );

    sectionIds.forEach((id) => {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    });

    return () => observer.disconnect();
  }, [isViewingDesign]);

  const selectStage = (stageId: string) => {
    const stage = pipeline?.stages.find((item) => item.id === stageId);
    if (!stage || stage.status === "queued") return;
    setSelectedStageId(stageId);
  };

  const scrollToDesignSection = (sectionId: string) => {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const approveCheckpoint = async () => {
    if (!pipeline || !selectedStage || isActing) return;

    setIsActing(true);
    setError(null);
    try {
      const nextPipeline = await approveStage(pipeline.id, selectedStage.id, {
        reviewer: "human",
        continue_pipeline: true,
      });
      setPipeline(nextPipeline);
      setSelectedStageId(currentStageId(nextPipeline.stages));
    } catch (approvalError) {
      setError(approvalError instanceof Error ? approvalError.message : "Failed to approve stage");
    } finally {
      setIsActing(false);
    }
  };

  const rejectCheckpoint = async (reason: string) => {
    if (!pipeline || !selectedStage || isActing) return;

    setIsActing(true);
    setError(null);
    try {
      const nextPipeline = await rejectStage(pipeline.id, selectedStage.id, {
        reviewer: "human",
        comment: reason,
        continue_pipeline: false,
      });
      setPipeline(nextPipeline);
      setSelectedStageId(selectedStage.id);
    } catch (rejectError) {
      setError(rejectError instanceof Error ? rejectError.message : "Failed to reject stage");
    } finally {
      setIsActing(false);
    }
  };

  if (isLoading) {
    return (
      <main className="pipeline-page">
        <section className="detail-panel">
          <div className="detail-header">
            <div>
              <span className="eyebrow">DeliveraX / DevFlow Engine</span>
              <h2>Loading pipeline</h2>
            </div>
          </div>
        </section>
      </main>
    );
  }

  if (!pipeline || !selectedStage) {
    return (
      <main className="pipeline-page">
        <section className="detail-panel">
          <div className="detail-header">
            <div>
              <span className="eyebrow">DeliveraX / DevFlow Engine</span>
              <h2>Pipeline unavailable</h2>
            </div>
          </div>
          {error && <p className="ai-input-hint error">{error}</p>}
        </section>
      </main>
    );
  }

  return (
    <main className="pipeline-page">
      <PipelineHeader status={pipeline.status} totalDuration={totalDuration(pipeline)} model={pipeline.provider} />
      {error && (
        <div className="floating-log-strip" aria-live="polite">
          <span>{error}</span>
        </div>
      )}
      {isActing && (
        <div className="floating-log-strip" aria-live="polite">
          <span>Syncing with API server...</span>
        </div>
      )}
      <div className="pipeline-layout">
        <aside className="pipeline-left-column">
          <PipelineTimeline stages={pipeline.stages} activeStageId={activeStageId} selectedStageId={selectedStage.id} onSelectStage={selectStage} />
          {isViewingDesign && (
            <nav className="design-review-nav enhanced pipeline-structure-nav" aria-label="Technical design structure">
              <div className="panel-title compact">
                <span className="eyebrow">Content Index</span>
                <h2>缁撴瀯瀵艰埅</h2>
              </div>
              {DESIGN_NAV_GROUPS.map((group) => (
                <div className="nav-group" key={group.group}>
                  <strong>{group.group}</strong>
                  {group.items.map((item) => (
                    <button
                      key={item.id}
                      className={activeDesignSection === item.id ? "active" : ""}
                      type="button"
                      onClick={() => scrollToDesignSection(item.id)}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              ))}
            </nav>
          )}
        </aside>
        <StageDetailPanel
          stage={selectedStage}
          model={pipeline.provider}
          pipelineRequirement={pipeline.requirement}
          viewingHistory={selectedStage.id !== activeStageId}
          onApprove={approveCheckpoint}
          onReject={rejectCheckpoint}
        />
      </div>
      <div className="floating-log-strip" aria-hidden="true">
        {createBaseLogs(pipeline.provider).map((log) => (
          <span key={log}>{log}</span>
        ))}
      </div>
    </main>
  );
}
