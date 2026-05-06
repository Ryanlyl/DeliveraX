import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import PipelineHeader from "../components/PipelineHeader";
import PipelineTimeline from "../components/PipelineTimeline";
import PipelineCanvas from "../components/PipelineCanvas";
import StageDetailPanel from "../components/StageDetailPanel";
import CheckpointPanel from "../components/CheckpointPanel";
import { Api } from "../api/client";
import type {
  PipelineRecord,
  PipelineRun,
  CurrentCheckpointResponse,
  ReviewAssetsResponse,
  StageRecord,
} from "../api/client";

function getPreferredStageId(stages: StageRecord[]): string {
  const active = stages.find(
    (s) =>
      s.status === "running" ||
      s.status === "pending_approval" ||
      s.status === "failed",
  );
  if (active) return active.id;

  const lastSucceeded = [...stages].reverse().find((s) => s.status === "succeeded");
  if (lastSucceeded) return lastSucceeded.id;

  const firstAvailable = stages.find((s) => s.status !== "queued");
  if (firstAvailable) return firstAvailable.id;

  return stages[0]?.id ?? "";
}

export default function PipelineDetail() {
  const { pipelineId } = useParams<{ pipelineId: string }>();
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run_id");

  const [pipeline, setPipeline] = useState<PipelineRecord | null>(null);
  const [run, setRun] = useState<PipelineRun | null>(null);
  const [checkpoint, setCheckpoint] = useState<CurrentCheckpointResponse | null>(null);
  const [reviewAssets, setReviewAssets] = useState<ReviewAssetsResponse | null>(null);
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [selectedStageId, setSelectedStageId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [totalDuration, setTotalDuration] = useState("0.0s");

  const pollRef = useRef<number | null>(null);
  const durationRef = useRef<number | null>(null);
  const pipelineRef = useRef(pipeline);
  const userSelectedStageRef = useRef(false);

  pipelineRef.current = pipeline;

  // ── fetch helpers ──

  const fetchPipeline = useCallback(async () => {
    if (!pipelineId) return;
    const p = await Api.getPipeline(pipelineId);
    setPipeline(p);
    return p;
  }, [pipelineId]);

  const fetchRun = useCallback(async () => {
    if (!pipelineId || !runId) return;
    const r = await Api.getRun(pipelineId, runId);
    setRun(r);
    return r;
  }, [pipelineId, runId]);

  const fetchCheckpoint = useCallback(async () => {
    if (!pipelineId) return;
    try {
      const c = await Api.getCurrentCheckpoint(pipelineId);
      setCheckpoint(c);
    } catch {
      setCheckpoint(null);
    }
  }, [pipelineId]);

  const fetchReviewAssets = useCallback(
    async (stageId: string) => {
      if (!pipelineId) return;
      setLoadingAssets(true);
      try {
        const assets = await Api.getStageReviewAssets(pipelineId, stageId);
        setReviewAssets(assets);
      } catch {
        setReviewAssets(null);
      } finally {
        setLoadingAssets(false);
      }
    },
    [pipelineId],
  );

  // ── initial load ──

  useEffect(() => {
    if (!pipelineId) {
      setError("No pipeline ID in URL");
      return;
    }

    let cancelled = false;

    async function init() {
      try {
        const p = await Api.getPipeline(pipelineId!);
        if (cancelled) return;
        setPipeline(p);
        if (p.stages.length > 0) {
          setSelectedStageId((prev) => prev || getPreferredStageId(p.stages));
        }
        if (runId) {
          const r = await Api.getRun(pipelineId!, runId);
          if (!cancelled) setRun(r);
        }
      } catch (e) {
        if (!cancelled) setError(`Failed to load pipeline: ${e instanceof Error ? e.message : e}`);
      }
    }

    init();

    return () => {
      cancelled = true;
    };
  }, [pipelineId, runId]);

  // ── polling ──

  useEffect(() => {
    if (!pipelineId) return;

    async function poll() {
      try {
        const p = await Api.getPipeline(pipelineId!);
        setPipeline(p);

        if (p.status === "pending_approval") {
          await fetchCheckpoint();
        }

        if (runId) {
          const r = await Api.getRun(pipelineId!, runId);
          setRun(r);
        }

        if (Api.isTerminal(p.status)) {
          if (pollRef.current) window.clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        // keep polling on transient errors
      }
    }

    pollRef.current = window.setInterval(poll, 1000);

    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [pipelineId, runId, fetchCheckpoint]);

  // ── duration tracking ──

  useEffect(() => {
    if (!run?.started_at) return;
    const startedAt = new Date(run.started_at).getTime();

    if (run.ended_at) {
      const dur = (new Date(run.ended_at).getTime() - startedAt) / 1000;
      setTotalDuration(`${dur.toFixed(1)}s`);
      return;
    }

    if (Api.isTerminal(pipeline?.status ?? "queued")) return;

    durationRef.current = window.setInterval(() => {
      const dur = (Date.now() - startedAt) / 1000;
      setTotalDuration(`${dur.toFixed(1)}s`);
    }, 200);

    return () => {
      if (durationRef.current) window.clearInterval(durationRef.current);
    };
  }, [run?.started_at, run?.ended_at, pipeline?.status]);

  // ── load review assets when stage selection changes ──

  useEffect(() => {
    if (selectedStageId) {
      fetchReviewAssets(selectedStageId);
    }
  }, [selectedStageId, fetchReviewAssets]);

  // ── derived state ──

  const activeStageId =
    run?.current_stage_id ||
    pipeline?.stages.find(
      (s) => s.status === "running" || s.status === "pending_approval",
    )?.id ||
    "";

  const pendingApprovalStageId =
    pipeline?.stages.find((s) => s.status === "pending_approval")?.id ?? "";

  const selectedStage = pipeline?.stages.find((s) => s.id === selectedStageId);

  const handleSelectStage = (stageId: string) => {
    const stage = pipeline?.stages.find((s) => s.id === stageId);
    if (!stage || stage.status === "queued") return;
    userSelectedStageRef.current = true;
    setSelectedStageId(stageId);
  };

  // ── auto-follow active stage (unless user manually selected) ──

  useEffect(() => {
    if (!activeStageId) return;
    if (userSelectedStageRef.current) return;

    setSelectedStageId(activeStageId);
  }, [activeStageId]);

  // ── force-switch to pending approval stage ──

  useEffect(() => {
    if (!pendingApprovalStageId) return;

    setSelectedStageId(pendingApprovalStageId);
    userSelectedStageRef.current = false;
  }, [pendingApprovalStageId]);

  // ── lifecycle actions ──

  const clearError = () => setError(null);

  const handleStart = async () => {
    if (!pipelineId) return;
    clearError();
    try {
      const r = await Api.startPipeline(pipelineId);
      setRun(r);
      // update URL with run_id without full navigation
      const params = new URLSearchParams(searchParams);
      params.set("run_id", r.id);
      window.history.replaceState(null, "", `?${params.toString()}`);
      await fetchPipeline();
    } catch (e) {
      setError(`Start failed: ${e instanceof Error ? e.message : e}`);
    }
  };

  const handlePause = async () => {
    if (!pipelineId) return;
    clearError();
    try {
      await Api.pausePipeline(pipelineId, runId ?? undefined);
      await fetchPipeline();
      await fetchRun();
    } catch (e) {
      setError(`Pause failed: ${e instanceof Error ? e.message : e}`);
    }
  };

  const handleResume = async () => {
    if (!pipelineId) return;
    clearError();
    try {
      await Api.resumePipeline(pipelineId, runId ?? undefined);
      await fetchPipeline();
      await fetchRun();
    } catch (e) {
      setError(`Resume failed: ${e instanceof Error ? e.message : e}`);
    }
  };

  const handleTerminate = async () => {
    if (!pipelineId) return;
    clearError();
    try {
      await Api.terminatePipeline(pipelineId, runId ?? undefined);
      await fetchPipeline();
      await fetchRun();
    } catch (e) {
      setError(`Terminate failed: ${e instanceof Error ? e.message : e}`);
    }
  };

  const handleApprove = async () => {
    if (!checkpoint?.checkpoint?.id) return;
    clearError();
    try {
      await Api.approveCheckpoint(checkpoint.checkpoint.id, { continue_pipeline: true });
      setCheckpoint(null);
      await fetchPipeline();
      await fetchRun();
    } catch (e) {
      setError(`Approval failed: ${e instanceof Error ? e.message : e}`);
    }
  };

  const handleReject = async (reason: string) => {
    if (!checkpoint?.checkpoint?.id) return;
    clearError();
    try {
      await Api.rejectCheckpoint(checkpoint.checkpoint.id, { reason, continue_pipeline: false });
      setCheckpoint(null);
      await fetchPipeline();
      await fetchRun();
    } catch (e) {
      setError(`Rejection failed: ${e instanceof Error ? e.message : e}`);
    }
  };

  // ── loading / error states ──

  if (error) {
    return (
      <main className="pipeline-page">
        <div className="pipeline-error">
          <h2>Pipeline Error</h2>
          <p>{error}</p>
          <button className="button primary" type="button" onClick={() => { setError(null); fetchPipeline(); }}>
            Retry
          </button>
        </div>
      </main>
    );
  }

  if (!pipeline) {
    return (
      <main className="pipeline-page">
        <div className="pipeline-loading">
          <span className="spinner" aria-hidden="true" />
          <p>Loading pipeline…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="pipeline-page">
      <PipelineHeader
        pipelineName={pipeline.name}
        pipelineId={pipeline.id}
        runId={run?.id ?? null}
        status={pipeline.status}
        totalDuration={totalDuration}
        model={pipeline.model}
        provider={pipeline.provider}
        onStart={handleStart}
        onPause={handlePause}
        onResume={handleResume}
        onTerminate={handleTerminate}
      />

      {pipeline.status === "pending_approval" && (
        <div className="checkpoint-alert">
          <strong>等待人工审核</strong>
          <p>当前流程已暂停，请查看当前 stage 输出并选择"通过"或"拒绝"。</p>
        </div>
      )}

      {/* ── visual flow overview ── */}
      <PipelineCanvas
        stages={pipeline.stages}
        activeStageId={activeStageId}
        selectedStageId={selectedStageId}
        onSelectStage={handleSelectStage}
      />

      <div className="pipeline-layout">
        <aside className="pipeline-left-column">
          <PipelineTimeline
            stages={pipeline.stages}
            activeStageId={activeStageId}
            selectedStageId={selectedStageId}
            onSelectStage={handleSelectStage}
          />
        </aside>
        {selectedStage && (
          <div>
            <StageDetailPanel
              stage={selectedStage}
              reviewAssets={reviewAssets}
              isLoadingAssets={loadingAssets}
              onApprove={handleApprove}
              onReject={handleReject}
            />

            {checkpoint?.checkpoint &&
              checkpoint.checkpoint.status === "pending" &&
              checkpoint.checkpoint.stage_id === selectedStage.id && (
                <CheckpointPanel
                  checkpoint={checkpoint}
                  reviewAssets={reviewAssets}
                  pipelineId={pipelineId!}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  isLoadingAssets={loadingAssets}
                  onFetchReviewAssets={fetchReviewAssets}
                />
              )}
          </div>
        )}
      </div>
    </main>
  );
}
