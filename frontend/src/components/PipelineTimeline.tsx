import type { StageRecord } from "../api/client";
import StageCard from "./StageCard";

type Props = {
  stages: StageRecord[];
  activeStageId: string;
  selectedStageId: string;
  onSelectStage: (stageId: string) => void;
};

export default function PipelineTimeline({ stages, activeStageId, selectedStageId, onSelectStage }: Props) {
  return (
    <aside className="timeline-panel">
      <div className="panel-title">
        <span className="eyebrow">Pipeline Timeline</span>
        <h2>Execution Stages</h2>
      </div>
      <div className="timeline-list">
        {stages.map((stage, index) => (
          <StageCard
            key={stage.id}
            stage={stage}
            active={stage.id === activeStageId}
            selected={stage.id === selectedStageId}
            disabled={stage.status === "queued"}
            isLast={index === stages.length - 1}
            onSelect={() => onSelectStage(stage.id)}
          />
        ))}
      </div>
    </aside>
  );
}
