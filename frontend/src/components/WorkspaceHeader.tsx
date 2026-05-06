type Props = {
  title?: string;
  subtitle?: string;
};

export default function WorkspaceHeader({ title = "AI DevFlow Pipeline", subtitle }: Props) {
  return (
    <div className="flex items-center justify-between gap-4 bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-4">
      <div className="min-w-0">
        <h2 className="text-lg font-bold text-slate-900">{title}</h2>
        {subtitle ? (
          <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>
        ) : (
          <p className="text-xs text-slate-400 mt-0.5">
            ID · 当前阶段 · Provider / Model · 状态
          </p>
        )}
      </div>
    </div>
  );
}
