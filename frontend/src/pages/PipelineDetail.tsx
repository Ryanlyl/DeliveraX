import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import PipelineHeader from "../components/PipelineHeader";
import PipelineTimeline from "../components/PipelineTimeline";
import StageDetailPanel, { DESIGN_NAV_GROUPS } from "../components/StageDetailPanel";
import { initialStages } from "../data/mockPipeline";
import type { LLMProvider, PipelineStatus, Stage, StageStatus } from "../types/pipeline";

const stageDurations = ["1.5s", "3.0s", "4.2s", "6.8s", "9.6s", "11.1s"];
const createBaseLogs = (model: LLMProvider) => [
  `Using model: ${model}`,
  "Requirement Agent started",
  "Parsing natural language requirement",
  "Generated RequirementSpec JSON",
  "Waiting for human approval",
  "Token usage: 1280",
  "Duration: 3.2s",
];

function parseModel(model: string | null): LLMProvider {
  return model === "Claude 3" ? "Claude 3" : "GPT-4";
}

function cloneStages() {
  return initialStages.map((stage) => ({
    ...stage,
    logs: [...stage.logs],
  }));
}

function nextExecutableIndex(stages: Stage[], currentIndex: number) {
  for (let index = currentIndex + 1; index < stages.length; index += 1) {
    if (stages[index].status === "queued") return index;
  }
  return -1;
}

function enforceCheckpointBoundary(stages: Stage[]) {
  const pendingReviewIndex = stages.findIndex((stage) => stage.status === "pending_approval");
  if (pendingReviewIndex < 0) return stages;

  return stages.map((stage, index) =>
    index > pendingReviewIndex && stage.status !== "queued"
      ? { ...stage, status: "queued" as const, duration: "0.0s" }
      : stage,
  );
}

export default function PipelineDetail() {
  const [searchParams] = useSearchParams();
  const model = parseModel(searchParams.get("model"));
  const [stages, setStages] = useState<Stage[]>(cloneStages);
  const [activeStageId, setActiveStageId] = useState("requirements");
  const [selectedStageId, setSelectedStageId] = useState("requirements");
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>("running");
  const [totalDuration, setTotalDuration] = useState("0.0s");
  const [activeDesignSection, setActiveDesignSection] = useState("meta");
  const timerRef = useRef<number | null>(null);

  const selectedStage = useMemo(
    () => stages.find((stage) => stage.id === selectedStageId) ?? stages[0],
    [selectedStageId, stages],
  );
  const isViewingDesign = selectedStage.id === "solution";

  const focusCurrentStage = (nextStages: Stage[]) => {
    const focused = nextStages.find((stage) => stage.status === "pending_approval" || stage.status === "running");
    if (focused) setActiveStageId(focused.id);
  };

  const selectStage = (stageId: string) => {
    const stage = stages.find((item) => item.id === stageId);
    if (!stage || stage.status === "queued") return;
    setSelectedStageId(stageId);
  };

  const updateStage = (stageId: string, patch: Partial<Stage>) => {
    setStages((current) => {
      const next = current.map((stage) => (stage.id === stageId ? { ...stage, ...patch } : stage));
      focusCurrentStage(next);
      return next;
    });
  };

  const appendLog = (stageId: string, log: string) => {
    setStages((current) =>
      current.map((stage) =>
        stage.id === stageId && !stage.logs.includes(log) ? { ...stage, logs: [...stage.logs, log] } : stage,
      ),
    );
  };

  const completeRunningStage = (stageId: string, targetStatus: StageStatus = "succeeded") => {
    setStages((current) => {
      const index = current.findIndex((stage) => stage.id === stageId);
      if (index < 0) return current;

      const next = enforceCheckpointBoundary(current.map((stage, stageIndex) => {
        if (stage.id !== stageId) return stage;
        const logMessage =
          targetStatus === "pending_approval" ? "Waiting for human approval" : `${stage.agent} completed successfully`;
        const logs = [
          ...stage.logs,
          ...(stage.logs.includes(logMessage) ? [] : [logMessage]),
        ];
        return { ...stage, status: targetStatus, duration: stageDurations[index], logs };
      }));

      if (targetStatus === "pending_approval") {
        setPipelineStatus("pending_approval");
      }

      focusCurrentStage(next);
      return next;
    });
  };

  const runStage = (stageId: string) => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    updateStage(stageId, { status: "running" });
    appendLog(stageId, `${stages.find((stage) => stage.id === stageId)?.agent ?? "Agent"} started`);

    timerRef.current = window.setTimeout(() => {
      const currentStage = initialStages.find((item) => item.id === stageId);
      const shouldPauseForReview = currentStage?.checkpoint === true;
      completeRunningStage(stageId, shouldPauseForReview ? "pending_approval" : "succeeded");

      if (!shouldPauseForReview) {
        setStages((current) => {
          const index = current.findIndex((item) => item.id === stageId);
          const nextIndex = nextExecutableIndex(current, index);
          if (nextIndex < 0) {
            setPipelineStatus("succeeded");
            setTotalDuration("18.6s");
            return current;
          }
          const next = current.map((item, itemIndex) =>
            itemIndex === nextIndex
              ? { ...item, status: "running" as const, logs: [...item.logs, `${item.agent} started`] }
              : item,
          );
          focusCurrentStage(next);
          window.setTimeout(() => runStage(next[nextIndex].id), 80);
          return next;
        });
      }
    }, 1500);
  };

  useEffect(() => {
    const timer = window.setTimeout(() => runStage("requirements"), 250);
    return () => {
      window.clearTimeout(timer);
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, []);

  useEffect(() => {
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      if (pipelineStatus !== "succeeded") {
        setTotalDuration(`${((Date.now() - startedAt) / 1000).toFixed(1)}s`);
      }
    }, 200);
    return () => window.clearInterval(timer);
  }, [pipelineStatus]);

  useEffect(() => {
    const pendingReviewIndex = stages.findIndex((stage) => stage.status === "pending_approval");
    if (pendingReviewIndex < 0) return;

    const normalized = enforceCheckpointBoundary(stages);
    const needsNormalization = normalized.some(
      (stage, index) => stage.status !== stages[index].status || stage.duration !== stages[index].duration,
    );

    if (pipelineStatus !== "pending_approval") {
      setPipelineStatus("pending_approval");
    }
    if (activeStageId !== stages[pendingReviewIndex].id) {
      setActiveStageId(stages[pendingReviewIndex].id);
    }
    const selectedStageInNext = normalized.find((stage) => stage.id === selectedStageId);
    if (!selectedStageInNext || selectedStageInNext.status === "queued") {
      setSelectedStageId(stages[pendingReviewIndex].id);
    }
    if (needsNormalization) {
      setStages(normalized);
    }
  }, [activeStageId, pipelineStatus, selectedStageId, stages]);

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

  const scrollToDesignSection = (sectionId: string) => {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const approveCheckpoint = () => {
    const currentIndex = stages.findIndex((stage) => stage.id === selectedStage.id);
    const nextIndex = nextExecutableIndex(stages, currentIndex);
    const approvedStages = stages.map((stage, index) => {
      if (stage.id === selectedStage.id) {
        return {
          ...stage,
          status: "succeeded" as const,
          logs: stage.logs.includes("Human approval received") ? stage.logs : [...stage.logs, "Human approval received"],
        };
      }
      if (index === nextIndex) {
        return { ...stage, status: "running" as const, logs: [...stage.logs, `${stage.agent} started`] };
      }
      return stage;
    });

    setPipelineStatus("running");
    setStages(approvedStages);

    if (nextIndex >= 0) {
      setActiveStageId(approvedStages[nextIndex].id);
      setSelectedStageId(approvedStages[nextIndex].id);
      window.setTimeout(() => runStage(approvedStages[nextIndex].id), 120);
    } else {
      setPipelineStatus("succeeded");
      setTotalDuration("18.6s");
    }
  };

  const rejectCheckpoint = (reason: string) => {
    appendLog(selectedStage.id, `Reject reason received: ${reason}`);
    appendLog(selectedStage.id, `Regenerating stage output with model: ${model}`);
    setPipelineStatus("running");
    updateStage(selectedStage.id, { status: "running" });

    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      completeRunningStage(selectedStage.id, "pending_approval");
    }, 1500);
  };

  return (
    <main className="pipeline-page">
      <PipelineHeader status={pipelineStatus} totalDuration={totalDuration} model={model} />
      <div className="pipeline-layout">
        <aside className="pipeline-left-column">
          <PipelineTimeline stages={stages} activeStageId={activeStageId} selectedStageId={selectedStageId} onSelectStage={selectStage} />
          {isViewingDesign && (
            <nav className="design-review-nav enhanced pipeline-structure-nav" aria-label="技术方案结构导航">
              <div className="panel-title compact">
                <span className="eyebrow">Content Index</span>
                <h2>结构导航</h2>
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
          model={model}
          viewingHistory={selectedStageId !== activeStageId}
          onApprove={approveCheckpoint}
          onReject={rejectCheckpoint}
        />
      </div>
      <div className="floating-log-strip" aria-hidden="true">
        {createBaseLogs(model).map((log) => (
          <span key={log}>{log}</span>
        ))}
      </div>
    </main>
  );
}
