import { useState } from "react";

type Props = {
  title: string;
  description: string;
  onApprove: () => void;
  onReject: (reason: string) => void;
};

export default function CheckpointPanel({ title, description, onApprove, onReject }: Props) {
  const [reason, setReason] = useState("");
  const [checkedItems, setCheckedItems] = useState<string[]>([]);
  const isRequirementReview = title.includes("需求");
  const checklistItems = ["需求范围是否完整", "UI/交互是否符合预期", "验收标准是否清晰", "待确认问题是否明确"];
  const isChecklistComplete = checkedItems.length === checklistItems.length;
  const approveDisabled = isRequirementReview && !isChecklistComplete;

  const toggleChecklistItem = (item: string) => {
    setCheckedItems((current) =>
      current.includes(item) ? current.filter((checked) => checked !== item) : [...current, item],
    );
  };

  return (
    <section className="checkpoint-panel">
      <div>
        <span className="checkpoint-kicker">CHECKPOINT</span>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {isRequirementReview && (
        <div className="checkpoint-checklist">
          <strong>审核 Checklist</strong>
          <div>
            {checklistItems.map((item) => (
              <label key={item} className={checkedItems.includes(item) ? "checked" : ""}>
                <input
                  type="checkbox"
                  checked={checkedItems.includes(item)}
                  onChange={() => toggleChecklistItem(item)}
                />
                <span>{item}</span>
              </label>
            ))}
          </div>
        </div>
      )}
      <div className="checkpoint-decision-grid">
        <article>
          <strong>AI 总结</strong>
          <p>已完成需求结构化，包含：</p>
          <ul>
            <li>{isRequirementReview ? "任务完成按钮视觉升级" : "代码实现符合需求目标"}</li>
            <li>{isRequirementReview ? "状态与禁用逻辑" : "测试结果与风险项已整理"}</li>
            <li>验收标准</li>
          </ul>
        </article>
        <article>
          <strong>风险提示</strong>
          <ul className="checkpoint-risk-list">
            {isRequirementReview ? (
              <>
                <li>需要重点确认完成状态是否允许重复触发。</li>
                <li>需要重点确认按钮视觉是否符合现有设计规范。</li>
              </>
            ) : (
              <>
                <li>需要重点确认评审报告中的设计规范风险。</li>
                <li>需要重点确认是否允许进入交付集成。</li>
              </>
            )}
          </ul>
        </article>
      </div>
      <textarea
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="请输入修改意见（将反馈给 AI 重新生成需求）"
      />
      <div className="checkpoint-actions">
        <button className="button secondary warning" type="button" onClick={() => onReject(reason || "需要重新生成并补充说明")}>
          {isRequirementReview ? "返回修改需求" : "返回修改"}
        </button>
        <button className="button primary" type="button" onClick={onApprove} disabled={approveDisabled}>
          {isRequirementReview ? "确认需求无误，进入方案设计" : "确认进入交付集成"}
        </button>
      </div>
    </section>
  );
}
