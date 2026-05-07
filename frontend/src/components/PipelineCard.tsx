import type { PipelineRecord } from "../api/client";

const statusConfig: Record<string, { label: string; className: string }> = {
  queued: { label: "Queued", className: "bg-slate-100 text-slate-600" },
  running: { label: "Running", className: "bg-blue-50 text-blue-600" },
  paused: { label: "Paused", className: "bg-amber-50 text-amber-600" },
  pending_approval: { label: "Pending approval", className: "bg-amber-50 text-amber-600" },
  succeeded: { label: "Succeeded", className: "bg-emerald-50 text-emerald-600" },
  failed: { label: "Failed", className: "bg-red-50 text-red-600" },
  rejected: { label: "Rejected", className: "bg-red-50 text-red-600" },
  cancelled: { label: "Cancelled", className: "bg-slate-100 text-slate-500" },
  terminated: { label: "Terminated", className: "bg-slate-100 text-slate-500" },
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function currentStageLabel(p: PipelineRecord): string {
  const active = p.stages.find((s) => s.status === "running" || s.status === "pending_approval");
  if (active) return active.name;

  if (p.stages.length > 0) {
    const lastDone = [...p.stages].reverse().find((s) => s.status === "succeeded");
    if (lastDone) return lastDone.name;
  }

  return "Not started";
}

type Props = {
  pipeline: PipelineRecord;
  isActive: boolean;
  onClick: () => void;
};

export default function PipelineCard({ pipeline, isActive, onClick }: Props) {
  const status = statusConfig[pipeline.status] ?? {
    label: pipeline.status,
    className: "bg-slate-100 text-slate-600",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={`pipeline-card w-full text-left rounded-xl border px-4 py-3.5 transition-all duration-150 cursor-pointer font-sans ${
        isActive
          ? "pipeline-card-active border-blue-300 bg-blue-50/70 shadow-sm"
          : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-semibold text-slate-900 truncate">{pipeline.name}</h4>
          <p className="text-xs text-slate-400 mt-0.5 truncate">
            {pipeline.requirement.slice(0, 60)}
            {pipeline.requirement.length > 60 ? "..." : ""}
          </p>
        </div>
        <span className={`shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold ${status.className}`}>
          {status.label}
        </span>
      </div>

      <div className="pipeline-card-meta flex items-center gap-3 mt-2.5 text-[11px] text-slate-400">
        <span>{currentStageLabel(pipeline)}</span>
        <span className="text-slate-300">·</span>
        <span>
          {pipeline.provider}
          {pipeline.model ? ` / ${pipeline.model}` : ""}
        </span>
        <span className="text-slate-300">·</span>
        <span>{formatDate(pipeline.updated_at)}</span>
      </div>
    </button>
  );
}
