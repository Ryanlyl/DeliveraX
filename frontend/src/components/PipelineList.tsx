import type { PipelineRecord } from "../api/client";
import PipelineCard from "./PipelineCard";

type Props = {
  pipelines: PipelineRecord[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  activePipelineId?: string;
  onPipelineClick: (pipeline: PipelineRecord) => void;
};

export default function PipelineList({
  pipelines,
  loading,
  error,
  onRetry,
  activePipelineId,
  onPipelineClick,
}: Props) {
  return (
    <div className="pipeline-list-panel bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">Pipelines</h2>
          {!loading && !error && (
            <span className="text-xs font-semibold text-slate-400 bg-slate-100 rounded-full px-2.5 py-0.5">
              {pipelines.length}
            </span>
          )}
        </div>
      </div>

      <div className="px-4 py-3">
        {loading && (
          <div className="flex flex-col items-center gap-3 py-10 text-slate-400">
            <div className="w-5 h-5 border-2 border-slate-200 border-t-blue-500 rounded-full animate-spin" />
            <p className="text-xs">Loading pipelines...</p>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center gap-3 py-10">
            <p className="text-xs text-red-500">Failed to load: {error}</p>
            <button
              type="button"
              onClick={onRetry}
              className="rounded-lg bg-blue-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-600 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && pipelines.length === 0 && (
          <div className="py-10 text-center">
            <p className="text-xs text-slate-400">No pipeline yet.</p>
            <p className="text-xs text-slate-300 mt-1">Create a new DevFlow from the workspace panel.</p>
          </div>
        )}

        {!loading && !error && pipelines.length > 0 && (
          <div className="flex flex-col gap-2">
            {pipelines.map((p) => (
              <PipelineCard
                key={p.id}
                pipeline={p}
                isActive={p.id === activePipelineId}
                onClick={() => onPipelineClick(p)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
