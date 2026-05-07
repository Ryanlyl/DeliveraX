const stages = [
  { key: "requirement", label: "需求" },
  { key: "design", label: "方案" },
  { key: "code", label: "代码" },
  { key: "test", label: "测试" },
  { key: "review", label: "评审" },
  { key: "delivery", label: "交付" },
] as const;

type Props = {
  activeIndex?: number;
  completedIndices?: number[];
};

export default function StageStepper({
  activeIndex = -1,
  completedIndices = [],
}: Props) {
  return (
    <div className="flex items-center justify-between gap-0">
      {stages.map((stage, i) => {
        const isCompleted = completedIndices.includes(i) || i < activeIndex;
        const isActive = i === activeIndex;

        return (
          <div key={stage.key} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1.5">
              {/* Dot */}
              <div
                className={`w-3 h-3 rounded-full transition-colors duration-200 ${
                  isActive
                    ? "bg-blue-500 shadow-[0_0_0_4px_rgba(59,130,246,0.15)]"
                    : isCompleted
                      ? "bg-emerald-500"
                      : "bg-slate-200"
                }`}
              />
              {/* Label */}
              <span
                className={`text-[11px] font-semibold whitespace-nowrap ${
                  isActive
                    ? "text-blue-600"
                    : isCompleted
                      ? "text-emerald-600"
                      : "text-slate-400"
                }`}
              >
                {stage.label}
              </span>
            </div>
            {/* Connector line */}
            {i < stages.length - 1 && (
              <div className="flex-1 h-px mx-1 mt-[-14px]">
                <div
                  className={`h-full transition-colors duration-300 ${
                    i < activeIndex || isCompleted ? "bg-emerald-400" : "bg-slate-200"
                  }`}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
