import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { ProviderDefinition, Stage } from "../types/pipeline";
import AgentLogs from "./AgentLogs";
import CheckpointPanel from "./CheckpointPanel";
import StageArtifactsPanel from "./StageArtifactsPanel";

type Props = {
  stage: Stage;
  model: string;
  pipelineId: string;
  pipelineRequirement: string;
  viewingHistory?: boolean;
  onApprove: () => void;
  onReject: (reason: string) => void;
};

type DetailTab = "document" | "input";

const tabs: Array<{ id: DetailTab; label: string }> = [
  { id: "document", label: "结构化需求文档" },
  { id: "input", label: "需求输入" },
];

function stringifyDetail(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  return JSON.stringify(value, null, 2);
}

function getStageInputText(stage: Stage, fallback = "") {
  const dataInput = stage.data.input ?? stage.data.input_payload ?? stage.data.request;
  if (dataInput != null) return stringifyDetail(dataInput);
  if (stage.input_artifacts.length > 0) return stringifyDetail(stage.input_artifacts);
  return fallback;
}

function getStageOutputText(stage: Stage) {
  if (stage.human_output?.trim()) return stage.human_output;
  if (stage.error) return `${stage.error.code}: ${stage.error.message}`;
  if (Object.keys(stage.data).length > 0) return stringifyDetail(stage.data);
  if (stage.output_artifacts.length > 0) return stringifyDetail(stage.output_artifacts);
  return "";
}

const statusLabel: Record<Stage["status"], string> = {
  queued: "待执行",
  running: "AI 正在执行",
  succeeded: "已完成",
  failed: "Failed",
  pending_approval: "等待人工审核",
  rejected: "已驳回",
  cancelled: "已取消",
  skipped: "已跳过",
};

function DiffBlock({ content }: { content: string }) {
  return (
    <pre className="code-block diff-block">
      {content.split("\n").map((line, index) => (
        <span key={`${line}-${index}`} className={line.startsWith("+") ? "diff-add" : line.startsWith("-") ? "diff-remove" : ""}>
          {line || " "}
        </span>
      ))}
    </pre>
  );
}

function CodeGenerationResult({ stage }: { stage: Stage }) {
  const changedFiles = [
    { path: "src/components/TaskItem.tsx", added: 10, removed: 2 },
    { path: "src/styles/task-list.css", added: 14, removed: 2 },
  ];

  return (
    <div className="code-result-page">
      <section className="code-summary-grid" aria-label="代码生成结果摘要">
        <article>
          <span>本次生成完成任务</span>
          <strong>任务列表交互优化</strong>
        </article>
        <article>
          <span>修改文件数</span>
          <strong>2</strong>
        </article>
        <article>
          <span>变更代码行</span>
          <strong className="line-delta"><em>+24</em><i>-4</i></strong>
        </article>
      </section>

      <section className="code-files-card">
        <div className="file-change-summary">
          <strong>2 个文件已更改</strong>
          <span className="line-delta"><em>+24</em><i>-4</i></span>
        </div>
        <div className="code-file-list">
          {changedFiles.map((file) => (
            <article key={file.path}>
              <code>{file.path}</code>
              <span className="file-line-delta"><em>+{file.added}</em><i>-{file.removed}</i></span>
              <button type="button" aria-label={`展开 ${file.path} 的变更详情`}>⌄</button>
            </article>
          ))}
        </div>
      </section>

      <section className="code-diff-card">
        <div className="code-diff-toolbar">
          <strong>Code Diff</strong>
          <div>
            <button type="button">复制</button>
            <button type="button">展开</button>
          </div>
        </div>
        <DiffBlock content={getStageOutputText(stage)} />
      </section>
    </div>
  );
}

type EditableTextProps = {
  value: string;
  changed?: boolean;
  multiline?: boolean;
  onSave: (value: string) => void;
};

function EditableText({ value, changed = false, multiline = false, onSave }: EditableTextProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    if (!editing) setDraft(value);
  }, [editing, value]);

  if (editing) {
    return (
      <span className="editable-field editing">
        {multiline ? (
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} autoFocus />
        ) : (
          <input value={draft} onChange={(event) => setDraft(event.target.value)} autoFocus />
        )}
        <span className="editable-actions">
          <button type="button" onClick={() => { onSave(draft.trim() || value); setEditing(false); }}>
            保存
          </button>
          <button type="button" onClick={() => { setDraft(value); setEditing(false); }}>
            取消
          </button>
        </span>
      </span>
    );
  }

  return (
    <span className={`editable-field ${changed ? "changed" : ""}`}>
      <span>{value}</span>
      {changed && <em>已修改</em>}
      <button type="button" onClick={() => setEditing(true)} aria-label="编辑字段">
        ✏️ 编辑
      </button>
    </span>
  );
}

function EditableSelect({
  value,
  options,
  changed = false,
  onSave,
}: {
  value: string;
  options: string[];
  changed?: boolean;
  onSave: (value: string) => void;
}) {
  return (
    <span className={`editable-field select ${changed ? "changed" : ""}`}>
      <select value={value} onChange={(event) => onSave(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      {changed && <em>已修改</em>}
    </span>
  );
}

function EditableList({
  items,
  prefix,
  changedFields,
  onSave,
}: {
  items: string[];
  prefix: string;
  changedFields: string[];
  onSave: (index: number, value: string) => void;
}) {
  return (
    <ul>
      {items.map((item, index) => (
        <li key={`${prefix}-${index}`}>
          <EditableText value={item} changed={changedFields.includes(`${prefix}.${index}`)} multiline onSave={(value) => onSave(index, value)} />
        </li>
      ))}
    </ul>
  );
}

const initialRequirementDocument = {
  basicInfo: {
    requirementName: "任务列表完成按钮视觉强化与状态反馈",
    requirementType: "前端 UI / 交互优化",
    priority: "P1",
    owner: "产品 / 设计 / 前端协作确认",
    relatedPageOrModule: "任务列表页",
    estimatedDeliveryTime: "Demo 阶段当日交付",
    status: "待人工确认",
  },
  background: {
    context: "任务列表页中，“完成”是用户处理任务时的核心动作。当前按钮视觉层级偏弱，用户在扫视任务列表时难以快速定位主要操作。",
    currentProblems: ["完成按钮与普通操作按钮区分不明显。", "用户完成任务后，状态变化反馈不够清晰。", "已完成任务缺少明确的不可重复操作提示。"],
    targetUsers: ["需要快速处理待办任务的普通用户。", "需要批量浏览任务状态的运营或项目成员。"],
  },
  goals: {
    inScope: ["将任务列表页中的“完成”按钮调整为更醒目的主按钮样式。", "用户点击完成后，任务状态立即变化，并展示明确的“已完成”反馈。", "确保按钮 hover、禁用态和完成态具有清晰视觉区分。"],
    outOfScope: ["不新增任务筛选、排序或批量操作能力。", "不改动任务创建、编辑、删除流程。", "不在 PRD 阶段定义具体代码文件、组件拆分或测试文件路径。"],
  },
  impactScope: {
    pagesOrModules: "任务列表页、任务列表项展示区域",
    userRoles: "普通任务处理用户、任务管理用户",
    businessFlows: "查看任务列表 → 点击完成 → 查看完成状态",
    dataOrApiScenarios: "可能涉及任务完成状态字段，例如 completed / status；具体接口确认放入方案设计阶段。",
  },
  uiux: {
    pageStructure: ["任务列表结构保持稳定，不新增额外操作区域。", "完成按钮仍位于任务项的主要操作位置。"],
    visualRequirements: ["完成按钮使用主按钮视觉层级，颜色需与当前设计系统保持一致。", "按钮文字清晰，未完成状态显示“完成”，已完成状态显示“已完成”。"],
    responsiveRequirements: ["桌面端按钮不挤压任务标题和状态信息。", "窄屏下按钮仍可点击，文字不溢出。"],
    interactionRequirements: ["Hover 时有轻微反馈，避免过度动画。", "点击完成后禁止重复触发。", "完成状态变化应在当前任务项内即时可见。"],
  },
  acceptance: {
    checklist: ["未完成任务展示醒目的“完成”主按钮。", "点击“完成”后任务状态变为已完成。", "已完成任务展示“已完成”状态。", "已完成任务不可重复点击完成操作。", "Hover、点击、禁用态均有清晰视觉反馈。"],
    gherkin: `Given 用户打开任务列表页
When 用户看到未完成任务
Then 任务项应展示醒目的“完成”按钮

Given 用户点击某个任务的“完成”按钮
When 完成操作成功
Then 该任务应展示“已完成”状态
And 用户不能重复触发完成操作`,
  },
  performanceRequirements: ["按钮样式和状态变化不应引入明显渲染抖动。", "完成状态更新应在用户操作后即时反馈。"],
  compatibilityRequirements: ["支持主流桌面浏览器的现代版本。", "在常见窄屏宽度下按钮文案不应溢出。"],
  copywriting: {
    normalCopy: "完成、已完成",
    errorCopy: "完成失败，请稍后重试",
  },
  risks: [
    { risk: "主按钮样式与现有设计规范不一致", impact: "视觉割裂", mitigation: "方案设计阶段对齐 Design Tokens" },
    { risk: "完成状态反馈不够明确", impact: "用户重复点击", mitigation: "增加禁用态和“已完成”文案" },
  ],
  definitionOfDone: ["需求范围、验收标准和待确认问题已通过人工审核。", "方案设计阶段可基于本文档继续拆解实现策略。", "相关 UI 状态、交互反馈和文案要求已明确。", "不在需求分析阶段引入代码路径或测试文件决策。"],
};

type RequirementDocumentState = typeof initialRequirementDocument;
type RequirementSectionKey =
  | "basicInfo"
  | "background"
  | "goals"
  | "impactScope"
  | "uiux"
  | "acceptance"
  | "performance"
  | "compatibility"
  | "copywriting"
  | "risks"
  | "done";

function cloneRequirementDocument(document: RequirementDocumentState): RequirementDocumentState {
  return JSON.parse(JSON.stringify(document)) as RequirementDocumentState;
}

function RequirementDocument() {
  const [doc, setDoc] = useState<RequirementDocumentState>(initialRequirementDocument);
  const [draft, setDraft] = useState<RequirementDocumentState>(initialRequirementDocument);
  const [editingSection, setEditingSection] = useState<RequirementSectionKey | null>(null);
  const [changedSections, setChangedSections] = useState<RequirementSectionKey[]>([]);

  const startEdit = (section: RequirementSectionKey) => {
    setDraft(cloneRequirementDocument(doc));
    setEditingSection(section);
  };

  const saveSection = (section: RequirementSectionKey) => {
    setDoc(cloneRequirementDocument(draft));
    setChangedSections((current) => (current.includes(section) ? current : [...current, section]));
    setEditingSection(null);
  };

  const cancelEdit = () => {
    setDraft(cloneRequirementDocument(doc));
    setEditingSection(null);
  };

  const isEditing = (section: RequirementSectionKey) => editingSection === section;
  const view = (section: RequirementSectionKey) => (isEditing(section) ? draft : doc);

  const setBasicInfo = (key: keyof RequirementDocumentState["basicInfo"], value: string) => {
    setDraft((current) => ({ ...current, basicInfo: { ...current.basicInfo, [key]: value } }));
  };

  const setNestedField = <Group extends "background" | "impactScope" | "copywriting" | "acceptance">(
    group: Group,
    key: keyof RequirementDocumentState[Group],
    value: string,
  ) => {
    setDraft((current) => ({ ...current, [group]: { ...current[group], [key]: value } }));
  };

  const setNestedListItem = <Group extends "background" | "goals" | "uiux" | "acceptance">(
    group: Group,
    key: keyof RequirementDocumentState[Group],
    index: number,
    value: string,
  ) => {
    setDraft((current) => ({
      ...current,
      [group]: {
        ...current[group],
        [key]: (current[group][key] as string[]).map((item, itemIndex) => (itemIndex === index ? value : item)),
      },
    }));
  };

  const setTopListItem = (
    key: "performanceRequirements" | "compatibilityRequirements" | "definitionOfDone",
    index: number,
    value: string,
  ) => {
    setDraft((current) => ({
      ...current,
      [key]: current[key].map((item, itemIndex) => (itemIndex === index ? value : item)),
    }));
  };

  const setRisk = (index: number, key: keyof RequirementDocumentState["risks"][number], value: string) => {
    setDraft((current) => ({
      ...current,
      risks: current.risks.map((risk, riskIndex) => (riskIndex === index ? { ...risk, [key]: value } : risk)),
    }));
  };

  const SectionHeader = ({ id, title }: { id: RequirementSectionKey; title: string }) => (
    <div className="prd-section-header">
      <h4>{title}</h4>
      {changedSections.includes(id) && <span className="section-changed">已修改</span>}
      {isEditing(id) ? (
        <span className="section-actions">
          <button type="button" onClick={() => saveSection(id)}>保存</button>
          <button type="button" onClick={cancelEdit}>取消</button>
        </span>
      ) : (
        <button className="section-edit-button" type="button" onClick={() => startEdit(id)}>✏️ 编辑</button>
      )}
    </div>
  );

  const textField = (value: string, onChange: (value: string) => void, editing: boolean, multiline = false) =>
    editing ? (
      multiline ? (
        <textarea className="section-control" value={value} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <input className="section-control" value={value} onChange={(event) => onChange(event.target.value)} />
      )
    ) : (
      value
    );

  const renderList = (items: string[], editing: boolean, onChange: (index: number, value: string) => void, className?: string) => (
    <ul className={className}>
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>
          {editing ? (
            <textarea className="section-control" value={item} onChange={(event) => onChange(index, event.target.value)} />
          ) : (
            item
          )}
        </li>
      ))}
    </ul>
  );

  return (
    <article className="prd-document">
      <header>
        <h3>任务列表完成按钮视觉强化与状态反馈</h3>
        <p>PRD 阶段仅确认需求本身，不读取代码库上下文；代码路径、组件拆分与测试文件将在方案设计阶段处理。</p>
      </header>

      <section>
        <SectionHeader id="basicInfo" title="1. 基本信息" />
        <table>
          <tbody>
            <tr><th>需求名称</th><td>{textField(view("basicInfo").basicInfo.requirementName, (value) => setBasicInfo("requirementName", value), isEditing("basicInfo"))}</td></tr>
            <tr><th>需求类型</th><td>{textField(view("basicInfo").basicInfo.requirementType, (value) => setBasicInfo("requirementType", value), isEditing("basicInfo"))}</td></tr>
            <tr>
              <th>优先级</th>
              <td>
                {isEditing("basicInfo") ? (
                  <select className="section-control" value={draft.basicInfo.priority} onChange={(event) => setBasicInfo("priority", event.target.value)}>
                    {["P0", "P1", "P2", "P3"].map((priority) => <option key={priority}>{priority}</option>)}
                  </select>
                ) : doc.basicInfo.priority}
              </td>
            </tr>
            <tr><th>负责人</th><td>{doc.basicInfo.owner}</td></tr>
            <tr><th>相关页面 / 模块</th><td>{textField(view("basicInfo").basicInfo.relatedPageOrModule, (value) => setBasicInfo("relatedPageOrModule", value), isEditing("basicInfo"))}</td></tr>
            <tr><th>预计交付时间</th><td>{textField(view("basicInfo").basicInfo.estimatedDeliveryTime, (value) => setBasicInfo("estimatedDeliveryTime", value), isEditing("basicInfo"))}</td></tr>
            <tr><th>当前状态</th><td><span className="locked-field" title="该字段由系统自动维护，无法手动修改">{doc.basicInfo.status} 🔒</span></td></tr>
          </tbody>
        </table>
      </section>

      <section>
        <SectionHeader id="background" title="2. 背景与问题说明" />
        <h5>背景</h5>
        <p>{textField(view("background").background.context, (value) => setNestedField("background", "context", value), isEditing("background"), true)}</p>
        <h5>当前问题</h5>
        {renderList(view("background").background.currentProblems, isEditing("background"), (index, value) => setNestedListItem("background", "currentProblems", index, value))}
        <h5>目标用户</h5>
        {renderList(view("background").background.targetUsers, isEditing("background"), (index, value) => setNestedListItem("background", "targetUsers", index, value))}
      </section>

      <section>
        <SectionHeader id="goals" title="3. 需求目标" />
        <h5>本次要实现什么</h5>
        {renderList(view("goals").goals.inScope, isEditing("goals"), (index, value) => setNestedListItem("goals", "inScope", index, value))}
        <h5>本次不做什么</h5>
        {renderList(view("goals").goals.outOfScope, isEditing("goals"), (index, value) => setNestedListItem("goals", "outOfScope", index, value))}
      </section>

      <section>
        <SectionHeader id="impactScope" title="4. 需求影响范围说明" />
        <table>
          <tbody>
            <tr><th>涉及页面 / 模块</th><td>{textField(view("impactScope").impactScope.pagesOrModules, (value) => setNestedField("impactScope", "pagesOrModules", value), isEditing("impactScope"))}</td></tr>
            <tr><th>涉及用户角色</th><td>{textField(view("impactScope").impactScope.userRoles, (value) => setNestedField("impactScope", "userRoles", value), isEditing("impactScope"))}</td></tr>
            <tr><th>涉及业务流程</th><td>{textField(view("impactScope").impactScope.businessFlows, (value) => setNestedField("impactScope", "businessFlows", value), isEditing("impactScope"))}</td></tr>
            <tr><th>涉及接口 / 数据</th><td>{textField(view("impactScope").impactScope.dataOrApiScenarios, (value) => setNestedField("impactScope", "dataOrApiScenarios", value), isEditing("impactScope"), true)}</td></tr>
          </tbody>
        </table>
      </section>

      <section>
        <SectionHeader id="uiux" title="5. UI / UX 要求" />
        <h5>页面结构</h5>
        {renderList(view("uiux").uiux.pageStructure, isEditing("uiux"), (index, value) => setNestedListItem("uiux", "pageStructure", index, value))}
        <h5>视觉要求</h5>
        {renderList(view("uiux").uiux.visualRequirements, isEditing("uiux"), (index, value) => setNestedListItem("uiux", "visualRequirements", index, value))}
        <h5>响应式要求</h5>
        {renderList(view("uiux").uiux.responsiveRequirements, isEditing("uiux"), (index, value) => setNestedListItem("uiux", "responsiveRequirements", index, value))}
        <h5>交互要求</h5>
        {renderList(view("uiux").uiux.interactionRequirements, isEditing("uiux"), (index, value) => setNestedListItem("uiux", "interactionRequirements", index, value))}
      </section>

      <section>
        <SectionHeader id="acceptance" title="6. 验收标准" />
        <h5>功能验收 Checklist</h5>
        {renderList(view("acceptance").acceptance.checklist, isEditing("acceptance"), (index, value) => setNestedListItem("acceptance", "checklist", index, value), "prd-checklist")}
        <h5>Gherkin 验收场景</h5>
        <div className="gherkin-editable">{textField(view("acceptance").acceptance.gherkin, (value) => setNestedField("acceptance", "gherkin", value), isEditing("acceptance"), true)}</div>
      </section>

      <section>
        <SectionHeader id="performance" title="7. 性能要求" />
        {renderList(view("performance").performanceRequirements, isEditing("performance"), (index, value) => setTopListItem("performanceRequirements", index, value))}
      </section>

      <section>
        <SectionHeader id="compatibility" title="8. 兼容性要求" />
        {renderList(view("compatibility").compatibilityRequirements, isEditing("compatibility"), (index, value) => setTopListItem("compatibilityRequirements", index, value))}
      </section>

      <section>
        <SectionHeader id="copywriting" title="9. 文案要求" />
        <table>
          <tbody>
            <tr><th>正常文案</th><td>{textField(view("copywriting").copywriting.normalCopy, (value) => setNestedField("copywriting", "normalCopy", value), isEditing("copywriting"))}</td></tr>
            <tr><th>错误文案</th><td>{textField(view("copywriting").copywriting.errorCopy, (value) => setNestedField("copywriting", "errorCopy", value), isEditing("copywriting"))}</td></tr>
          </tbody>
        </table>
      </section>

      <section>
        <SectionHeader id="risks" title="10. 风险与注意事项" />
        <table>
          <thead>
            <tr><th>风险</th><th>影响</th><th>缓解方式</th></tr>
          </thead>
          <tbody>
            {view("risks").risks.map((risk, index) => (
              <tr key={`risk-${index}`}>
                <td>{textField(risk.risk, (value) => setRisk(index, "risk", value), isEditing("risks"), true)}</td>
                <td>{textField(risk.impact, (value) => setRisk(index, "impact", value), isEditing("risks"))}</td>
                <td>{textField(risk.mitigation, (value) => setRisk(index, "mitigation", value), isEditing("risks"), true)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <SectionHeader id="done" title="11. Definition of Done" />
        {renderList(view("done").definitionOfDone, isEditing("done"), (index, value) => setTopListItem("definitionOfDone", index, value))}
      </section>
    </article>
  );
}

const changedFiles = [
  { path: "src/components/TaskItem.tsx", action: "修改", content: "完成按钮 className 与完成态文案", note: "保持组件结构，仅增强主操作视觉和禁用态" },
  { path: "src/styles/task-list.css", action: "新增", content: "主按钮渐变、hover、阴影、禁用态样式", note: "复用 Design Tokens，避免内联样式" },
  { path: "src/components/__tests__/TaskItem.test.tsx", action: "新增", content: "完成按钮渲染、点击状态变化、异常状态测试", note: "覆盖核心交互和边界状态" },
];

export const DESIGN_NAV_GROUPS = [
  { group: "📌 基础信息", items: [{ id: "meta", label: "元信息" }] },
  { group: "🧠 设计理解", items: [{ id: "requirement-understanding", label: "需求理解" }, { id: "architecture-analysis", label: "现有架构分析" }] },
  {
    group: "🛠 技术方案",
    items: [
      { id: "tech-solution", label: "推荐技术方案" },
      { id: "impact-scope", label: "影响范围" },
      { id: "file-changes", label: "文件变更" },
      { id: "api-design", label: "API设计" },
      { id: "data-structure", label: "数据结构" },
    ],
  },
  { group: "🚀 实施与验证", items: [{ id: "implementation-steps", label: "实施步骤" }, { id: "test-plan", label: "测试计划" }] },
  { group: "⚠️ 风险与决策", items: [{ id: "risks", label: "风险与待确认问题" }] },
  { group: "🤖 Agent执行", items: [{ id: "agent-instructions", label: "执行指令" }, { id: "consistency-check", label: "一致性检查" }] },
];

const implementationContractYaml = `implementation_contract:
  objective: "强化任务列表完成按钮视觉层级，并补充完成态反馈"
  must_do:
    - "先读取仓库，确认任务列表页与任务项组件真实路径"
    - "复用现有状态字段与样式体系"
    - "补充完成按钮 hover、disabled、completed 状态"
    - "补充自动化测试"
  must_not_do:
    - "不要编造不存在的文件路径"
    - "不要新增筛选、排序或批量操作"
    - "不要改动无关页面"
  unresolved_questions:
    - "失败反馈使用 Toast 还是行内提示"
    - "任务完成接口与状态字段名称"`;

function ReviewSection({
  id,
  title,
  children,
  variant = "default",
  flagged = false,
  defaultOpen = false,
}: {
  id: string;
  title: string;
  children: ReactNode;
  variant?: "default" | "data" | "risk";
  flagged?: boolean;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section id={id} className={`design-review-section ${variant} ${flagged ? "flagged" : ""}`}>
      <button className="design-section-title" type="button" onClick={() => setOpen((current) => !current)} aria-expanded={open}>
        <h4>{title}</h4>
        <span>{open ? "收起" : "展开"}</span>
      </button>
      {open && <div className="design-section-body open">{children}</div>}
    </section>
  );
}

function TechnicalDesignReview() {
  const renderYamlLine = (line: string, index: number) => {
    const commentIndex = line.indexOf("#");
    const codePart = commentIndex >= 0 ? line.slice(0, commentIndex) : line;
    const commentPart = commentIndex >= 0 ? line.slice(commentIndex) : "";
    const match = codePart.match(/^(\s*(?:-\s*)?)([\w_]+)(:)(.*)$/);

    if (!match) {
      return (
        <span key={`${line}-${index}`} className="yaml-line">
          {codePart}
          {commentPart && <span className="yaml-comment">{commentPart}</span>}
        </span>
      );
    }

    const [, prefix, key, colon, rest] = match;
    const quoted = rest.match(/^(\s*)(".*")(\s*)$/);

    return (
      <span key={`${line}-${index}`} className="yaml-line">
        {prefix}
        <span className="yaml-key">{key}</span>
        {colon}
        {quoted ? (
          <>
            {quoted[1]}
            <span className="yaml-string">{quoted[2]}</span>
            {quoted[3]}
          </>
        ) : (
          rest
        )}
        {commentPart && <span className="yaml-comment">{commentPart}</span>}
      </span>
    );
  };

  return (
    <article className="design-review-workbench">
      <header className="technical-document-header">
        <h3>任务列表完成按钮视觉强化</h3>
        <p>基于需求分析自动生成的技术实现方案</p>
      </header>

      <section className="solution-summary-card">
        <div className="summary-card-header">
          <div>
            <span className="eyebrow">方案名称</span>
            <h4>任务列表完成按钮视觉强化</h4>
          </div>
          <span className="summary-status">Ready for Code</span>
        </div>
        <div className="summary-grid">
          <article>
            <strong>🧠 核心改动</strong>
            <ul>
              <li>按钮升级为主操作视觉</li>
              <li>完成后状态不可重复触发</li>
              <li>增加 hover / disabled 状态</li>
            </ul>
          </article>
          <article>
            <strong>📦 影响范围</strong>
            <ul>
              <li>TaskItem.tsx</li>
              <li>TaskList.tsx</li>
              <li>styles</li>
            </ul>
          </article>
          <article className="warning">
            <strong>⚠️ 风险提示</strong>
            <ul>
              <li>设计 Token 可能不一致</li>
              <li>状态字段命名待确认</li>
            </ul>
          </article>
        </div>
      </section>

      <div className="design-review-content document-mode">
          <ReviewSection id="meta" title="0. 元信息" variant="data" defaultOpen>
            <table className="review-table">
              <tbody>
                <tr><th>需求名称</th><td>任务列表完成按钮视觉强化与状态反馈</td></tr>
                <tr><th>目标仓库</th><td>DeliveraX Frontend Demo</td></tr>
                <tr><th>请求 ref</th><td>main</td></tr>
                <tr><th>实际 ref</th><td>main</td></tr>
                <tr><th>实际 commit SHA</th><td>demo-local-context</td></tr>
                <tr><th>拉取方式</th><td>本地 Demo 上下文</td></tr>
                <tr><th>package.json</th><td>React + TypeScript + Vite</td></tr>
                <tr><th>生成时间</th><td>Demo 运行时生成</td></tr>
                <tr><th>方案状态</th><td>Draft</td></tr>
                <tr><th>方案作者</th><td>SolDesign</td></tr>
              </tbody>
            </table>
          </ReviewSection>

          <ReviewSection id="requirement-understanding" title="1. 需求理解" defaultOpen>
            <h5>1.1 需求目标</h5>
            <p>本次变更聚焦任务列表页的核心操作「完成」。方案需要提升按钮视觉优先级，并在任务完成后给出明确状态反馈，避免用户重复点击或误判任务状态。</p>
            <ul className="bullet-ui">
              <li>完成按钮从普通操作升级为主操作视觉。</li>
              <li>完成后文案切换为「已完成」，并进入不可重复触发状态。</li>
            </ul>
            <h5>1.2 核心用户流程</h5>
            <ol className="step-list">
              <li>用户进入任务列表页并定位未完成任务。</li>
              <li>用户点击醒目的「完成」主按钮。</li>
              <li>当前任务项立即展示「已完成」状态。</li>
            </ol>
            <h5>1.3 本次不做</h5>
            <ul className="bullet-ui">
              <li>保留现有任务列表结构，不引入筛选、排序或批量操作。</li>
              <li>不改动任务创建、编辑、删除流程。</li>
            </ul>
            <h5>1.4 验收标准映射</h5>
            <table className="review-table">
              <thead><tr><th>验收项</th><th>技术响应</th></tr></thead>
              <tbody>
                <tr><td>完成按钮更醒目</td><td>新增主按钮样式类，并提高视觉层级。</td></tr>
                <tr><td>完成后展示状态变化</td><td>基于 completed 状态切换文案和 disabled 状态。</td></tr>
                <tr><td>Hover 与禁用态清晰</td><td>补充 hover、disabled、completed 样式。</td></tr>
              </tbody>
            </table>
          </ReviewSection>

          <ReviewSection id="architecture-analysis" title="2. 现有架构分析">
            <h5>2.1 技术栈与项目结构</h5>
            <ul className="bullet-ui">
              <li>前端技术栈：React + TypeScript + Vite。</li>
              <li>样式策略：Demo 中以普通 CSS / Design Tokens 为主。</li>
              <li>任务列表相关路径在当前 Demo 中未进行真实仓库扫描，具体路径需要实现 Agent 二次确认。</li>
            </ul>
            <h5>2.2 关键入口</h5>
            <table className="review-table">
              <thead><tr><th>入口类型</th><th>说明</th><th>确定性</th></tr></thead>
              <tbody>
                <tr><td>任务列表页面</td><td>承载任务项渲染与完成操作。</td><td>待实现 Agent 确认实际路径</td></tr>
                <tr><td>任务项组件</td><td>承载完成按钮和完成态文案。</td><td>待实现 Agent 确认实际路径</td></tr>
              </tbody>
            </table>
            <h5>2.3 可复用的已有实现</h5>
            <table className="review-table">
              <thead><tr><th>能力</th><th>复用方式</th></tr></thead>
              <tbody>
                <tr><td>Design Tokens</td><td>复用品牌蓝、圆角、阴影和状态色。</td></tr>
                <tr><td>任务完成状态</td><td>优先复用已有 completed / status 字段。</td></tr>
              </tbody>
            </table>
          </ReviewSection>

          <ReviewSection id="impact-scope" title="3. 影响范围" variant="data">
            <h5>3.1 页面与组件影响</h5>
            <table className="review-table">
              <tbody>
                <tr><th>页面 / 模块</th><td>任务列表页、任务列表项展示区域</td></tr>
                <tr><th>用户角色</th><td>普通任务处理用户、任务管理用户</td></tr>
                <tr><th>业务流程</th><td>查看任务列表 → 点击完成 → 查看完成状态</td></tr>
              </tbody>
            </table>
            <h5>3.2 状态与数据流影响</h5>
            <ul className="bullet-ui"><li>优先复用现有完成状态字段，不新增全局状态。</li><li>点击完成后更新当前任务项展示状态。</li></ul>
            <h5>3.3 API 与请求影响</h5>
            <ul className="bullet-ui"><li>当前方案不强制新增 API。</li><li>如果已有完成接口，沿用现有请求封装。</li></ul>
            <h5>3.4 样式与交互影响</h5>
            <ul className="bullet-ui"><li>新增主按钮视觉层级。</li><li>补充 hover、completed、disabled 状态。</li></ul>
            <h5>3.5 测试影响</h5>
            <ul className="bullet-ui"><li>补充按钮渲染、点击完成、不可重复点击和样式类断言。</li></ul>
          </ReviewSection>

          <ReviewSection id="tech-solution" title="4. 推荐技术方案">
            <h5>4.1 总体思路</h5>
            <ol className="step-list">
              <li>在 TaskItem 中为完成按钮增加主按钮 class，并基于 completed 状态切换文案与 disabled 属性。</li>
              <li>在样式层新增主按钮视觉，包括蓝色渐变、白色文字、轻微阴影和 hover 上浮。</li>
              <li>为完成态补充禁用态样式，降低重复操作风险。</li>
              <li>保留组件结构和数据流，避免扩大改动范围。</li>
            </ol>
            <h5>4.2 前端实现方案</h5>
            <ul className="bullet-ui"><li>按钮 className 增加主按钮样式类。</li><li>按钮文案由 completed 状态驱动。</li><li>完成态禁用按钮，避免重复触发。</li></ul>
            <h5>4.3 后端 / API 协作方案</h5>
            <ul className="bullet-ui"><li>优先复用已有任务完成接口。</li><li>接口字段不确定时写入待确认问题，不在方案中硬编码。</li></ul>
            <h5>4.4 错误、Loading、空状态处理</h5>
            <table className="review-table">
              <tbody>
                <tr><th>Loading</th><td>点击后按钮可进入处理中状态，避免重复提交。</td></tr>
                <tr><th>Success</th><td>任务项文案变为「已完成」。</td></tr>
                <tr><th>Error</th><td>保留原状态并提示「完成失败，请稍后重试」。</td></tr>
                <tr><th>Empty</th><td>无任务时不展示完成按钮。</td></tr>
                <tr><th>Retry</th><td>失败后允许用户再次点击完成。</td></tr>
              </tbody>
            </table>
            <h5>4.5 响应式与可访问性方案</h5>
            <ul className="bullet-ui"><li>窄屏下按钮文案不溢出。</li><li>disabled 状态需要具备视觉和语义表达。</li><li>按钮可保留原生 button 语义。</li></ul>
          </ReviewSection>

          <ReviewSection id="file-changes" title="5. 文件变更清单" variant="data">
            <table className="review-table">
              <thead>
                <tr><th>文件路径</th><th>操作</th><th>变更内容</th><th>执行说明</th></tr>
              </thead>
              <tbody>
                {changedFiles.map((file) => (
                  <tr key={file.path}>
                    <td><code>{file.path}</code></td>
                    <td><span className="review-tag neutral">{file.action}</span></td>
                    <td>{file.content}</td>
                    <td>{file.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ReviewSection>

          <ReviewSection id="api-design" title="6. API设计" variant="data">
            <h5>6.1 API 变更总览</h5>
            <table className="review-table">
              <thead><tr><th>接口</th><th>变更类型</th><th>说明</th></tr></thead>
              <tbody>
                <tr><td>任务完成接口</td><td>复用 / 待确认</td><td>Demo 不编造实际 API 路径，由实现 Agent 读取仓库后确认。</td></tr>
              </tbody>
            </table>
            <h5>6.2 请求与响应草案</h5>
            <div className="api-design-grid">
              <article>
                <strong>Request</strong>
                <pre>{`PATCH /api/tasks/:taskId
{
  "completed": true
}`}</pre>
              </article>
              <article>
                <strong>Response</strong>
                <pre>{`{
  "id": "task-001",
  "completed": true,
  "status": "completed"
}`}</pre>
              </article>
            </div>
            <h5>6.3 异常处理</h5>
            <table className="review-table compact">
              <thead><tr><th>错误场景</th><th>处理方式</th></tr></thead>
              <tbody>
                <tr><td>网络失败</td><td>保持原状态，提示「完成失败，请稍后重试」。</td></tr>
                <tr><td>重复提交</td><td>按钮进入 disabled 状态，避免二次触发。</td></tr>
              </tbody>
            </table>
          </ReviewSection>

          <ReviewSection id="data-structure" title="7. 数据结构与状态设计" variant="data">
            <h5>7.1 类型定义草案</h5>
            <pre className="schema-block">{`type Task = {
  id: string;
  title: string;
  completed: boolean;
  status?: "todo" | "completed";
};`}</pre>
            <h5>7.2 状态来源与更新方式</h5>
            <ul className="bullet-ui"><li>状态来源优先使用任务数据中的 completed 字段。</li><li>完成成功后更新当前任务项状态。</li><li>失败时回滚到原状态。</li></ul>
            <h5>7.3 边界条件</h5>
            <ul className="bullet-ui"><li>任务已完成时不允许重复提交。</li><li>接口失败时不展示错误的已完成状态。</li><li>任务标题过长时按钮区域不应被挤压。</li></ul>
          </ReviewSection>

          <ReviewSection id="implementation-steps" title="8. 实施步骤">
            <ol className="step-list">
              <li>实现 Agent 读取仓库并确认任务列表相关真实文件路径。</li>
              <li>定位任务项组件和完成状态字段。</li>
              <li>新增或调整完成按钮 className、文案和 disabled 状态。</li>
              <li>补充主按钮样式、hover 与完成态样式。</li>
              <li>补充自动化测试和必要的手工验收记录。</li>
            </ol>
          </ReviewSection>

          <ReviewSection id="test-plan" title="9. 测试计划" variant="data">
            <h5>9.1 自动化检查</h5>
            <table className="review-table">
              <thead><tr><th>测试项</th><th>预期结果</th></tr></thead>
              <tbody>
                <tr><td>完成按钮渲染</td><td>未完成任务展示主按钮样式。</td></tr>
                <tr><td>点击完成</td><td>任务状态变为已完成。</td></tr>
                <tr><td>重复点击</td><td>已完成任务不可重复触发。</td></tr>
              </tbody>
            </table>
            <h5>9.2 手工验收</h5>
            <div className="design-info-grid">
              <article>
                <ul className="checklist-ui">
                  <li>按钮视觉层级明显高于普通操作。</li>
                  <li>Hover、禁用态和完成态可区分。</li>
                  <li>窄屏下文案不溢出。</li>
                </ul>
              </article>
            </div>
            <h5>9.3 回归范围</h5>
            <ul className="bullet-ui"><li>任务列表渲染。</li><li>任务完成操作。</li><li>任务项布局和响应式表现。</li></ul>
          </ReviewSection>

          <ReviewSection id="risks" title="需要决策 / 风险点" variant="risk" flagged defaultOpen>
            <h5>10.1 风险</h5>
            <table className="review-table">
              <thead><tr><th>风险</th><th>影响</th><th>缓解方式</th></tr></thead>
              <tbody>
                <tr><td>主按钮样式与现有规范不一致</td><td>视觉割裂</td><td>复用 Design Tokens，并由实现 Agent 对齐现有样式。</td></tr>
                <tr><td>实际任务项路径不确定</td><td>代码生成可能落错文件</td><td>实现前必须读取仓库确认真实路径。</td></tr>
              </tbody>
            </table>
            <h5>10.2 待确认问题</h5>
            <div className="risk-panel">
              <ul>
                <li>任务列表页和任务项组件的真实文件路径需要实现 Agent 确认。</li>
                <li>完成失败时使用 Toast 还是行内错误提示需要确认。</li>
                <li>后端返回字段是 completed 还是 status 需要确认。</li>
              </ul>
            </div>
          </ReviewSection>

          <ReviewSection id="agent-instructions" title="11. 给下一个实现 Agent 的执行指令">
            <p className="code-caption">执行指令（供实现 Agent 使用）</p>
            <pre className="yaml-code-block">{implementationContractYaml.split("\n").map(renderYamlLine)}</pre>
          </ReviewSection>

          <ReviewSection id="consistency-check" title="12. 一致性自检">
            <table className="review-table">
              <thead><tr><th>检查项</th><th>结果</th><th>说明</th></tr></thead>
              <tbody>
                <tr><td>是否覆盖结构化需求目标</td><td>通过</td><td>覆盖按钮视觉强化与完成态反馈。</td></tr>
                <tr><td>是否编造代码路径</td><td>通过</td><td>路径不确定项已进入待确认问题。</td></tr>
                <tr><td>是否可交给实现 Agent</td><td>通过</td><td>包含实施步骤、文件变更方向、测试计划和执行指令。</td></tr>
              </tbody>
            </table>
          </ReviewSection>
      </div>
    </article>
  );
}

export default function StageDetailPanel({ stage, model, pipelineId, pipelineRequirement, viewingHistory = false, onApprove, onReject }: Props) {
  const [activeTab, setActiveTab] = useState<DetailTab>("document");
  const stageInput = getStageInputText(stage, pipelineRequirement);
  const stageOutput = getStageOutputText(stage);
  const hasStageOutput = stageOutput.trim().length > 0;
  const [editableRequirement, setEditableRequirement] = useState(stageInput);
  const [requirementDraft, setRequirementDraft] = useState(stageInput);
  const [supplementText, setSupplementText] = useState("");
  const [supplementDraft, setSupplementDraft] = useState("");
  const [editingRequirement, setEditingRequirement] = useState(false);
  const [businessContext, setBusinessContext] = useState(
    "AI 将基于确认后的自然语言需求推进需求分析、方案设计、代码生成、测试生成、代码评审与交付集成。\n人类只在关键检查点确认范围、风险和交付质量。",
  );
  const [businessContextDraft, setBusinessContextDraft] = useState(
    "AI 将基于确认后的自然语言需求推进需求分析、方案设计、代码生成、测试生成、代码评审与交付集成。\n人类只在关键检查点确认范围、风险和交付质量。",
  );
  const [editingContext, setEditingContext] = useState(false);
  const [analysisState, setAnalysisState] = useState<"idle" | "running" | "done">("idle");
  const isDesignStage = stage.id === "solution";
  const isCodeStage = stage.id === "code";
  const hasRequirementChanges =
    editableRequirement !== stageInput || supplementText.trim().length > 0 || businessContext !== businessContextDraft || analysisState === "done";
  const isCodeOutput = stage.id === "code" && activeTab === "document";
  const isRequirementOutput = stage.id === "requirements" && activeTab === "document";
  const isRequirementInput = stage.id === "requirements" && activeTab === "input";
  const displayStatus =
    stage.status === "pending_approval"
      ? stage.id === "requirements"
        ? "AI 已完成需求结构化，请确认是否进入下一阶段"
        : "AI 已完成当前阶段产物，请确认是否继续推进"
      : statusLabel[stage.status];

  useEffect(() => {
    if (stage.id === "solution") {
      setActiveTab("document");
    }
    setEditableRequirement(stageInput);
    setRequirementDraft(stageInput);
    setSupplementText("");
    setSupplementDraft("");
    setBusinessContext(
      "AI 将基于确认后的自然语言需求推进需求分析、方案设计、代码生成、测试生成、代码评审与交付集成。\n人类只在关键检查点确认范围、风险和交付质量。",
    );
    setBusinessContextDraft(
      "AI 将基于确认后的自然语言需求推进需求分析、方案设计、代码生成、测试生成、代码评审与交付集成。\n人类只在关键检查点确认范围、风险和交付质量。",
    );
    setEditingRequirement(false);
    setEditingContext(false);
    setAnalysisState("idle");
  }, [stage.id, stageInput]);

  const confirmRequirementEdit = () => {
    setAnalysisState("running");
    window.setTimeout(() => setAnalysisState("done"), 650);
  };

  const addAiSuggestion = () => {
    const suggestion = "- 需要完成 Toast 提示。\n- 需要 hover 动效。\n- 需要明确异常失败时的反馈方式。";
    if (!supplementText.includes("需要完成 Toast 提示")) {
      const nextSupplement = supplementText.trim() ? `${supplementText.trim()}\n${suggestion}` : suggestion;
      setSupplementText(nextSupplement);
      setSupplementDraft(nextSupplement);
      setAnalysisState("idle");
    }
  };

  return (
    <section className="detail-panel">
      <div className="detail-header">
        <div>
          <span className="eyebrow">AI 执行结果</span>
          <h2>{stage.id === "solution" ? "技术方案设计" : stage.name}</h2>
        </div>
        <span className={`status-pill ${stage.status}`}>{displayStatus}</span>
      </div>

      {viewingHistory && (
        <div className="history-view-note">
          正在查看历史阶段，不影响当前 Pipeline 执行。
        </div>
      )}

      {!isDesignStage && !isCodeStage && (
        <div className="tabs" role="tablist" aria-label="阶段详情">
          {tabs.map((tab) => (
            <button key={tab.id} className={activeTab === tab.id ? "active" : ""} type="button" onClick={() => setActiveTab(tab.id)}>
              {tab.label}
            </button>
          ))}
        </div>
      )}

      <div className="content-box">
        {stage.status !== "queued" && (
          <StageArtifactsPanel pipelineId={pipelineId} stage={stage} />
        )}
        {isCodeStage ? (
          <CodeGenerationResult stage={stage} />
        ) : isDesignStage ? (
          hasStageOutput ? <pre>{stageOutput}</pre> : <TechnicalDesignReview />
        ) : activeTab === "document" && (
          isRequirementOutput ? (hasStageOutput ? <pre>{stageOutput}</pre> : <RequirementDocument />) : isCodeOutput ? <DiffBlock content={stageOutput} /> : <pre>{stageOutput}</pre>
        )}
        {!isDesignStage && !isCodeStage && activeTab === "input" && (
          isRequirementInput ? (
            <div className="requirement-review-panel">
              <section className={`requirement-edit-card main ${editingRequirement ? "editing" : ""}`}>
                <div className="requirement-card-title">
                  <span aria-hidden="true">01</span>
                  <div>
                    <h3>核心需求</h3>
                    <p>确认你希望 AI 推进的核心目标。</p>
                  </div>
                  {editingRequirement ? (
                    <span className="inline-actions">
                      <button type="button" onClick={() => { setEditableRequirement(requirementDraft); setSupplementText(supplementDraft); setEditingRequirement(false); setAnalysisState("idle"); }}>
                        保存
                      </button>
                      <button type="button" onClick={() => { setRequirementDraft(editableRequirement); setSupplementDraft(supplementText); setEditingRequirement(false); }}>
                        取消
                      </button>
                    </span>
                  ) : (
                    <button className="inline-reset" type="button" onClick={() => { setRequirementDraft(editableRequirement); setSupplementDraft(supplementText); setEditingRequirement(true); }}>
                      ✏️ 编辑
                    </button>
                  )}
                </div>
                {editingRequirement ? (
                  <div className="document-edit-fields">
                    <label>
                      用户需求
                      <textarea
                        value={requirementDraft}
                        onChange={(event) => setRequirementDraft(event.target.value)}
                        placeholder="描述你希望AI推进的需求（越具体越好）"
                        aria-label="编辑用户需求"
                      />
                    </label>
                    <label>
                      补充描述
                      <textarea
                        className="compact"
                        value={supplementDraft}
                        onChange={(event) => setSupplementDraft(event.target.value)}
                        placeholder="补充约束、反馈方式或异常场景，可留空"
                        aria-label="编辑补充描述"
                      />
                    </label>
                  </div>
                ) : (
                  <div className="document-readonly-fields">
                    <article>
                      <strong>用户需求</strong>
                      <p className="requirement-readonly-text">{editableRequirement}</p>
                    </article>
                    <article className="muted">
                      <strong>补充描述</strong>
                      <p className="requirement-readonly-text">{supplementText || "暂无补充描述"}</p>
                    </article>
                  </div>
                )}
                <div className="requirement-card-footnote">
                  <p className="requirement-edit-tip">💡 描述越具体，后续方案与代码生成越准确</p>
                  <button className="inline-reset ghost" type="button" onClick={() => { setEditableRequirement(stageInput); setRequirementDraft(stageInput); setSupplementText(""); setSupplementDraft(""); setAnalysisState("idle"); }}>
                    恢复原始
                  </button>
                </div>
              </section>

              <section className="ai-understanding-card linear">
                <div className="requirement-card-title">
                  <span aria-hidden="true">02</span>
                  <div>
                    <h3>AI如何理解你的需求</h3>
                    <p>AI 将先把自然语言拆解为可执行信息，并提示可补充的关键细节。</p>
                  </div>
                </div>
                <div className="ai-recognition-grid">
                  <article>
                    <strong>当前识别</strong>
                    <ul>
                      <li>UI改动：强化按钮视觉层级</li>
                      <li>交互逻辑：点击后状态变化</li>
                      <li>验收标准：完成态、禁用态、hover 反馈</li>
                    </ul>
                  </article>
                  <article className="ai-suggestion-box">
                    <strong>建议补充项</strong>
                    <ul>
                      <li>是否需要 Toast 提示</li>
                      <li>是否需要动效</li>
                      <li>失败后是否需要错误反馈</li>
                    </ul>
                    <button className="button secondary" type="button" onClick={addAiSuggestion}>
                      一键补充到需求
                    </button>
                  </article>
                </div>
              </section>

              <section className={`requirement-edit-card context ${editingContext ? "editing" : ""}`}>
                <div className="requirement-card-title">
                  <span aria-hidden="true">03</span>
                  <div>
                    <h3>业务上下文（可选补充）</h3>
                    <p>补充场景、角色或限制条件，帮助 AI 更准确地理解需求边界。</p>
                  </div>
                  {editingContext ? (
                    <span className="inline-actions">
                      <button type="button" onClick={() => { setBusinessContext(businessContextDraft); setEditingContext(false); setAnalysisState("idle"); }}>
                        保存
                      </button>
                      <button type="button" onClick={() => { setBusinessContextDraft(businessContext); setEditingContext(false); }}>
                        取消
                      </button>
                    </span>
                  ) : (
                    <button className="inline-reset" type="button" onClick={() => { setBusinessContextDraft(businessContext); setEditingContext(true); }}>
                      ✏️ 编辑
                    </button>
                  )}
                </div>
                {editingContext ? (
                  <textarea
                    value={businessContextDraft}
                    onChange={(event) => setBusinessContextDraft(event.target.value)}
                    aria-label="编辑业务上下文"
                  />
                ) : (
                  <p className="requirement-readonly-text">{businessContext}</p>
                )}
              </section>

              <div className="requirement-review-actions">
                <span className={`analysis-state ${analysisState}`}>
                  {analysisState === "running"
                    ? "正在重新分析需求…"
                    : analysisState === "done"
                      ? "已基于当前需求更新分析视图"
                      : hasRequirementChanges
                        ? "你已修改需求，建议重新生成分析"
                        : "编辑完成后，可重新生成需求分析结果"}
                </span>
                <div>
                  <button className="button secondary" type="button" onClick={() => setAnalysisState("done")}>
                    仅保存修改
                  </button>
                  <button className="button primary" type="button" onClick={confirmRequirementEdit}>
                    重新生成需求分析 →
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <pre>{stageInput}</pre>
          )
        )}
      </div>

      {stage.status === "pending_approval" && (
        <CheckpointPanel
          title={stage.checkpoint_label ?? "Awaiting Human Approval"}
          description={stage.checkpoint_description ?? "AI Agent 已完成当前阶段产物，请人工确认是否继续推进 Pipeline。"}
          onApprove={onApprove}
          onReject={onReject}
        />
      )}

      <AgentLogs logs={stage.logs} model={model} />
    </section>
  );
}
