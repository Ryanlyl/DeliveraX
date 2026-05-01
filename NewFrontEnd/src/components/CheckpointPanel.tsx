import { useState } from "react";

type Props = {
  title: string;
  description: string;
  onApprove: () => void;
  onReject: (reason: string) => void;
};

export default function CheckpointPanel({ title, description, onApprove, onReject }: Props) {
  const [reason, setReason] = useState("");
  const isRequirementReview = title.includes("需求");

  return (
    <section className="checkpoint-panel">
      <div>
        <span className="checkpoint-kicker">CHECKPOINT</span>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <div className="checkpoint-decision-grid">
        <article>
          <strong>AI 总结</strong>
          <p>已完成需求结构化，包含：</p>
          <ul>
            <li>UI 改动</li>
            <li>交互逻辑</li>
            <li>验收标准</li>
          </ul>
        </article>
        <article>
          <strong>风险提示</strong>
          <p>{isRequirementReview ? "该需求可能影响现有交互逻辑，建议确认完成状态与重复点击规则。" : "该变更需要确认是否符合现有设计规范与交付标准。"}</p>
        </article>
      </div>
      <textarea
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="如需返回修改，可补充调整意见..."
      />
      <div className="checkpoint-actions">
        <button className="button secondary warning" type="button" onClick={() => onReject(reason || "需要重新生成并补充说明")}>
          返回修改
        </button>
        <button className="button primary" type="button" onClick={onApprove}>
          {isRequirementReview ? "确认进入方案设计" : "确认进入交付集成"}
        </button>
      </div>
    </section>
  );
}
