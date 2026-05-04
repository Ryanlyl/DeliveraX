import type { Stage } from "../types/pipeline";
import StageCard from "./StageCard";

type Props = {
  stages: Stage[];
  activeStageId: string;
  selectedStageId: string;
  onSelectStage: (stageId: string) => void;
};

export default function PipelineTimeline({ stages, activeStageId, selectedStageId, onSelectStage }: Props) {
  return (
    <aside className="timeline-panel">
      <div className="panel-title">
        <span className="eyebrow">Pipeline Timeline</span>
        <h2>执行链路</h2>
      </div>
      <div className="timeline-list">
        {stages.map((stage, index) => (
          <StageCard
            key={stage.id}
            stage={stage}
            active={stage.id === activeStageId}
            selected={stage.id === selectedStageId}
            disabled={stage.status === "waiting"}
            isLast={index === stages.length - 1}
            onSelect={() => onSelectStage(stage.id)}
          />
        ))}
      </div>
    </aside>
  );
}
