import type { RequirementSpec } from "./types";

const EMPTY_VALUE = "待确认";

function text(value: unknown): string {
  if (typeof value !== "string") {
    return EMPTY_VALUE;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : EMPTY_VALUE;
}

function list(values: string[] | undefined): string {
  if (!Array.isArray(values) || values.length === 0) {
    return `- ${EMPTY_VALUE}`;
  }

  return values.map((value) => `- ${text(value)}`).join("\n");
}

function checklist(values: string[] | undefined): string {
  if (!Array.isArray(values) || values.length === 0) {
    return `- [ ] ${EMPTY_VALUE}`;
  }

  return values.map((value) => `- [ ] ${text(value)}`).join("\n");
}

function definitionOfDoneChecklist(values: string[] | undefined): string {
  if (!Array.isArray(values) || values.length === 0) {
    return ["- [ ] 需求目标已确认", "- [ ] 验收标准已确认", "- [ ] 无未解决的阻塞问题"].join("\n");
  }

  return checklist(values);
}

function openQuestionsList(values: string[] | undefined): string {
  if (!Array.isArray(values) || values.length === 0) {
    return "- 暂无";
  }

  return list(values);
}

function gherkin(values: string[] | undefined): string {
  if (!Array.isArray(values) || values.length === 0) {
    return `\`\`\`gherkin\n${EMPTY_VALUE}\n\`\`\``;
  }

  return `\`\`\`gherkin\n${values.map(text).join("\n\n")}\n\`\`\``;
}

function table(rows: Array<[string, unknown]>): string {
  return ["| 字段 | 内容 |", "| --- | --- |", ...rows.map(([key, value]) => `| ${key} | ${text(value)} |`)].join("\n");
}

function risksTable(spec: RequirementSpec): string {
  if (!Array.isArray(spec.risks) || spec.risks.length === 0) {
    return ["| 风险 | 影响 | 缓解方式 |", "| --- | --- | --- |", `| ${EMPTY_VALUE} | ${EMPTY_VALUE} | ${EMPTY_VALUE} |`].join("\n");
  }

  return [
    "| 风险 | 影响 | 缓解方式 |",
    "| --- | --- | --- |",
    ...spec.risks.map((item) => `| ${text(item.risk)} | ${text(item.impact)} | ${text(item.mitigation)} |`),
  ].join("\n");
}

export function renderRequirementMarkdown(spec: RequirementSpec): string {
  return `# Frontend Feature PRD

## 1. 基本信息
${table([
  ["需求名称", spec.basicInfo?.requirementName],
  ["需求类型", spec.basicInfo?.requirementType],
  ["优先级", spec.basicInfo?.priority],
  ["负责人", spec.basicInfo?.owner],
  ["相关页面 / 模块", spec.basicInfo?.relatedPageOrModule],
  ["预计交付时间", spec.basicInfo?.estimatedDeliveryTime],
  ["状态", spec.basicInfo?.status],
])}

## 2. 背景与问题说明
### 2.1 背景
${text(spec.background?.context)}

### 2.2 当前问题
${list(spec.background?.currentProblems)}

### 2.3 目标用户
${list(spec.background?.targetUsers)}

## 3. 需求目标
### 3.1 本次要实现什么
${list(spec.goals?.inScope)}

### 3.2 本次不做什么
${list(spec.goals?.outOfScope)}

## 4. 需求影响范围说明
### 4.1 涉及页面 / 模块
${list(spec.impactScope?.pagesOrModules)}

### 4.2 涉及用户角色
${list(spec.impactScope?.userRoles)}

### 4.3 涉及业务流程
${list(spec.impactScope?.businessFlows)}

### 4.4 涉及接口 / 数据
${list(spec.impactScope?.dataOrApiScenarios)}

## 5. UI / UX 要求
### 5.1 页面结构
${list(spec.uiux?.pageStructure)}

### 5.2 视觉要求
${list(spec.uiux?.visualRequirements)}

### 5.3 响应式要求
${list(spec.uiux?.responsiveRequirements)}

### 5.4 交互要求
${list(spec.uiux?.interactionRequirements)}

## 6. 验收标准
### 6.1 功能验收 Checklist
${checklist(spec.acceptanceCriteria?.checklist)}

### 6.2 Gherkin 验收场景
${gherkin(spec.acceptanceCriteria?.gherkinScenarios)}

## 7. 性能要求
${list(spec.performanceRequirements)}

## 8. 兼容性要求
${list(spec.compatibilityRequirements)}

## 9. 文案要求
### 9.1 正常文案
${list(spec.copywriting?.normalCopy)}

### 9.2 错误文案
${list(spec.copywriting?.errorCopy)}

## 10. 风险与注意事项
${risksTable(spec)}

## 11. Definition of Done
${definitionOfDoneChecklist(spec.definitionOfDone)}

## 12. 待确认问题
${openQuestionsList(spec.openQuestions)}
`;
}
