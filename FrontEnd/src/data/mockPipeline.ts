import type { Pipeline, Stage } from "../types/pipeline";

export const exampleRequirement =
  "将任务列表页中的完成按钮调整为更醒目的主按钮样式，并在用户完成任务后展示状态变化。";

const commonInput = `用户需求：
${exampleRequirement}

业务上下文：
这是一次前端代码变更 Demo。AI 需要自动推进需求分析、方案设计、代码生成、测试生成、代码评审和交付集成，人类只在关键检查点审批。`;

const structuredRequirementDocument = `# 结构化需求文档：任务列表完成按钮视觉强化与状态反馈

> PRD 阶段仅确认需求本身，不读取代码库上下文；代码路径、组件拆分与测试文件将在下一步方案设计阶段处理。

## 1. 基本信息
| 字段 | 内容 |
| --- | --- |
| 需求名称 | 任务列表完成按钮视觉强化与状态反馈 |
| 需求类型 | 前端 UI / 交互优化 |
| 优先级 | P1 |
| 负责人 | 产品 / 设计 / 前端协作确认 |
| 相关页面 / 模块 | 任务列表页 |
| 预计交付时间 | Demo 阶段当日交付 |
| 当前状态 | 待人工确认 |

## 2. 背景与问题说明
### 背景
任务列表页中，“完成”是用户处理任务时的核心动作。当前按钮视觉层级偏弱，用户在扫视任务列表时难以快速定位主要操作。

### 当前问题
- 完成按钮与普通操作按钮区分不明显。
- 用户完成任务后，状态变化反馈不够清晰。
- 已完成任务缺少明确的不可重复操作提示。

### 目标用户
- 需要快速处理待办任务的普通用户。
- 需要批量浏览任务状态的运营或项目成员。

## 3. 需求目标
### 本次要实现什么
- 将任务列表页中的“完成”按钮调整为更醒目的主按钮样式。
- 用户点击完成后，任务状态立即变化，并展示明确的“已完成”反馈。
- 确保按钮 hover、禁用态和完成态具有清晰视觉区分。

### 本次不做什么
- 不新增任务筛选、排序或批量操作能力。
- 不改动任务创建、编辑、删除流程。
- 不在 PRD 阶段定义具体代码文件、组件拆分或测试文件路径。

## 4. 需求影响范围说明
| 范围 | 说明 |
| --- | --- |
| 涉及页面 / 模块 | 任务列表页、任务列表项展示区域 |
| 涉及用户角色 | 普通任务处理用户、任务管理用户 |
| 涉及业务流程 | 查看任务列表 → 点击完成 → 查看完成状态 |
| 涉及接口 / 数据 | 可能涉及任务完成状态字段，例如 completed / status；具体接口确认放入方案设计阶段。 |

## 5. UI / UX 要求
### 页面结构
- 任务列表结构保持稳定，不新增额外操作区域。
- 完成按钮仍位于任务项的主要操作位置。

### 视觉要求
- 完成按钮使用主按钮视觉层级，颜色需与当前设计系统保持一致。
- 按钮文字清晰，未完成状态显示“完成”，已完成状态显示“已完成”。

### 响应式要求
- 桌面端按钮不挤压任务标题和状态信息。
- 窄屏下按钮仍可点击，文字不溢出。

### 交互要求
- Hover 时有轻微反馈，避免过度动画。
- 点击完成后禁止重复触发。
- 完成状态变化应在当前任务项内即时可见。

## 6. 验收标准
### 功能验收 Checklist
- [ ] 未完成任务展示醒目的“完成”主按钮。
- [ ] 点击“完成”后任务状态变为已完成。
- [ ] 已完成任务展示“已完成”状态。
- [ ] 已完成任务不可重复点击完成操作。
- [ ] Hover、点击、禁用态均有清晰视觉反馈。

### Gherkin 验收场景
\`\`\`gherkin
Given 用户打开任务列表页
When 用户看到未完成任务
Then 任务项应展示醒目的“完成”按钮

Given 用户点击某个任务的“完成”按钮
When 完成操作成功
Then 该任务应展示“已完成”状态
And 用户不能重复触发完成操作
\`\`\`

## 7. 性能要求
- 按钮样式和状态变化不应引入明显渲染抖动。
- 完成状态更新应在用户操作后即时反馈。

## 8. 兼容性要求
- 支持主流桌面浏览器的现代版本。
- 在常见窄屏宽度下按钮文案不应溢出。

## 9. 文案要求
| 类型 | 文案 |
| --- | --- |
| 正常文案 | 完成、已完成 |
| 错误文案 | 完成失败，请稍后重试 |

## 10. 风险与注意事项
| 风险 | 影响 | 缓解方式 |
| --- | --- | --- |
| 主按钮样式与现有设计规范不一致 | 视觉割裂 | 方案设计阶段对齐 Design Tokens |
| 完成状态反馈不够明确 | 用户重复点击 | 增加禁用态和“已完成”文案 |

## 11. Definition of Done
- 需求范围、验收标准和待确认问题已通过人工审核。
- 方案设计阶段可基于本文档继续拆解实现策略。
- 相关 UI 状态、交互反馈和文案要求已明确。
- 不在需求分析阶段引入代码路径或测试文件决策。`;

const requirementSpec = {
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
    scenarios: ["用户在任务列表中快速完成某个待办事项。", "用户浏览任务列表并识别哪些任务已经完成。"],
    entryPoints: ["任务列表页", "任务列表项主操作区域"],
  },
  goals: {
    inScope: ["将“完成”按钮调整为更醒目的主按钮样式。", "点击完成后展示明确的“已完成”状态。", "补充 hover、禁用态和完成态要求。"],
    outOfScope: ["不新增筛选、排序或批量操作。", "不改动任务创建、编辑、删除流程。", "PRD 阶段不定义代码路径、组件拆分或测试文件。"],
  },
  impactScope: {
    pagesOrModules: ["任务列表页", "任务列表项展示区域"],
    userRoles: ["普通任务处理用户", "任务管理用户"],
    businessFlows: ["查看任务列表 → 点击完成 → 查看完成状态"],
    dataOrApiScenarios: ["可能涉及任务完成状态字段，例如 completed / status；具体接口确认放入方案设计阶段。"],
  },
  uiux: {
    pageStructure: ["任务列表结构保持稳定。", "完成按钮仍位于任务项的主要操作位置。"],
    visualRequirements: ["完成按钮使用主按钮视觉层级。", "未完成状态显示“完成”，已完成状态显示“已完成”。"],
    responsiveRequirements: ["桌面端按钮不挤压任务标题和状态信息。", "窄屏下按钮文字不溢出。"],
    interactionRequirements: ["Hover 时有轻微反馈。", "点击完成后禁止重复触发。", "状态变化应即时可见。"],
  },
  acceptanceCriteria: {
    checklist: ["未完成任务展示醒目的“完成”主按钮。", "点击“完成”后任务状态变为已完成。", "已完成任务展示“已完成”状态。", "已完成任务不可重复点击完成操作。", "Hover、点击、禁用态均有清晰视觉反馈。"],
    gherkinScenarios: [
      "Given 用户打开任务列表页\nWhen 用户看到未完成任务\nThen 任务项应展示醒目的“完成”按钮",
      "Given 用户点击某个任务的“完成”按钮\nWhen 完成操作成功\nThen 该任务应展示“已完成”状态\nAnd 用户不能重复触发完成操作",
    ],
  },
  performanceRequirements: ["按钮样式和状态变化不应引入明显渲染抖动。", "完成状态更新应在用户操作后即时反馈。"],
  compatibilityRequirements: ["支持主流桌面浏览器的现代版本。", "在常见窄屏宽度下按钮文案不应溢出。"],
  copywriting: {
    normalCopy: ["完成", "已完成"],
    errorCopy: ["完成失败，请稍后重试"],
  },
  risks: [
    { risk: "主按钮样式与现有设计规范不一致", impact: "视觉割裂", mitigation: "方案设计阶段对齐 Design Tokens" },
    { risk: "完成状态反馈不够明确", impact: "用户重复点击", mitigation: "增加禁用态和“已完成”文案" },
  ],
  definitionOfDone: ["需求范围、验收标准和待确认问题已通过人工审核。", "方案设计阶段可基于本文档继续拆解实现策略。", "相关 UI 状态、交互反馈和文案要求已明确。", "不在需求分析阶段引入代码路径或测试文件决策。"],
  openQuestions: ["主按钮视觉是否需要完全沿用现有 Design Tokens？", "完成失败时是否需要 Toast 或行内错误提示？"],
};

export const initialStages: Stage[] = [
  {
    id: "requirement",
    name: "需求分析",
    agent: "Requirement Agent",
    status: "running",
    duration: "0.0s",
    checkpoint: true,
    checkpointLabel: "需求确认 / Requirement Review",
    checkpointDescription: "AI 已生成结构化需求文档，请确认需求范围、验收标准与待确认问题是否准确。",
    input: exampleRequirement,
    output: structuredRequirementDocument,
    json: requirementSpec,
    logs: ["Requirement Agent started", "Parsing natural language requirement", "Generated RequirementSpec JSON"],
  },
  {
    id: "design",
    name: "方案设计",
    agent: "Design Agent",
    status: "waiting",
    duration: "0.0s",
    input: "RequirementSpec JSON + current frontend component context",
    output: `# 技术方案设计：任务列表完成按钮视觉强化与状态反馈

## 0. 元信息
| 字段 | 内容 |
| --- | --- |
| 需求名称 | 任务列表完成按钮视觉强化与状态反馈 |
| 目标仓库 | DeliveraX Frontend Demo |
| 请求 ref | main |
| 实际 ref | main |
| 实际 commit SHA | demo-local-context |
| 拉取方式 | 本地 Demo 上下文 |
| package.json | React + TypeScript + Vite |
| 生成时间 | Demo 运行时生成 |
| 方案状态 | Draft |
| 方案作者 | SolutionDesign Agent |

## 1. 需求理解
### 1.1 需求目标
- 强化任务列表页「完成」按钮视觉层级。
- 点击完成后展示清晰的状态变化。

### 1.2 核心用户流程
1. 用户进入任务列表页。
2. 用户点击未完成任务的「完成」按钮。
3. 当前任务项变为「已完成」状态。

### 1.3 本次不做
- 不新增筛选、排序或批量操作。
- 不改动任务创建、编辑、删除流程。

### 1.4 验收标准映射
| 验收项 | 技术响应 |
| --- | --- |
| 完成按钮更醒目 | 新增主按钮视觉样式 |
| 完成后展示状态变化 | 基于 completed / status 切换文案 |

## 2. 现有架构分析
### 2.1 技术栈与项目结构
- React + TypeScript + Vite。
- 任务列表真实文件路径需要实现 Agent 读取仓库确认。

### 2.2 关键入口
| 入口 | 说明 | 确定性 |
| --- | --- | --- |
| 任务列表页面 | 任务项渲染入口 | 待确认 |
| 任务项组件 | 完成按钮所在组件 | 待确认 |

### 2.3 可复用的已有实现
| 能力 | 复用方式 |
| --- | --- |
| Design Tokens | 复用品牌蓝、圆角、阴影 |
| 完成状态字段 | 优先复用 completed / status |

## 3. 影响范围
### 3.1 页面与组件影响
| 范围 | 说明 |
| --- | --- |
| 任务列表页 | 完成按钮视觉与状态反馈 |
| 任务项组件 | 按钮 className、文案、disabled 状态 |

### 3.2 状态与数据流影响
- 不新增全局状态。
- 成功后更新当前任务项展示状态。

### 3.3 API 与请求影响
- 优先复用已有任务完成接口。
- 不确定接口进入待确认问题。

### 3.4 样式与交互影响
- 新增主按钮视觉。
- 补充 hover、disabled、completed 状态。

### 3.5 测试影响
- 补充按钮渲染、点击完成、不可重复点击测试。

## 4. 推荐技术方案
### 4.1 总体思路
- 小范围改动任务项组件与样式。
- 不改变现有任务列表结构。

### 4.2 前端实现方案
- 为完成按钮增加主按钮 class。
- 根据 completed 状态切换「完成 / 已完成」。

### 4.3 后端 / API 协作方案
- 复用已有任务完成接口。
- 字段不确定时由实现 Agent 确认。

### 4.4 错误、Loading、空状态处理
| 状态 | 处理 |
| --- | --- |
| Loading | 点击后进入处理中状态 |
| Success | 展示「已完成」 |
| Error | 保持原状态并提示失败 |
| Empty | 无任务时不展示完成按钮 |
| Retry | 失败后允许再次点击 |

### 4.5 响应式与可访问性方案
- 窄屏下按钮文案不溢出。
- 保留原生 button 语义。

## 5. 文件变更清单
| 文件路径 | 操作 | 变更内容 | 下游 Agent 执行说明 |
| --- | --- | --- | --- |
| 待确认：任务项组件路径 | 修改 | 完成按钮 className 与文案 | 先读取仓库确认真实路径 |
| 待确认：任务列表样式路径 | 修改 / 新增 | 主按钮状态样式 | 复用 Design Tokens |
| 待确认：测试文件路径 | 新增 / 修改 | 完成按钮交互测试 | 覆盖核心场景 |

## 6. API 设计
### 6.1 API 变更总览
| 接口 | 变更类型 | 说明 |
| --- | --- | --- |
| 任务完成接口 | 复用 / 待确认 | 不编造实际路径 |

### 6.2 请求与响应草案
\`\`\`json
PATCH /api/tasks/:taskId
{ "completed": true }
\`\`\`

### 6.3 异常处理
| 错误场景 | 处理方式 |
| --- | --- |
| 网络失败 | 保持原状态并提示失败 |
| 重复提交 | disabled 避免二次触发 |

## 7. 数据结构与状态设计
### 7.1 类型定义草案
\`\`\`ts
type Task = {
  id: string;
  title: string;
  completed: boolean;
  status?: "todo" | "completed";
};
\`\`\`

### 7.2 状态来源与更新方式
- 状态来源优先使用 completed。
- 成功后更新当前任务项状态。

### 7.3 边界条件
- 已完成任务不可重复提交。
- 失败时不展示错误的已完成状态。

## 8. 实施步骤
1. 读取仓库并确认真实文件路径。
2. 定位任务项组件和完成状态字段。
3. 修改按钮 className、文案与 disabled 状态。
4. 补充样式与测试。

## 9. 测试计划
### 9.1 自动化检查
| 测试项 | 预期 |
| --- | --- |
| 完成按钮渲染 | 展示主按钮样式 |
| 点击完成 | 状态变为已完成 |

### 9.2 手工验收
- [ ] 按钮视觉层级明确。
- [ ] Hover、禁用态和完成态可区分。

### 9.3 回归范围
- 任务列表渲染。
- 任务完成操作。

## 10. 风险与待确认问题
### 10.1 风险
| 风险 | 影响 | 缓解方式 |
| --- | --- | --- |
| 真实路径不确定 | 代码生成可能落错文件 | 实现前读取仓库确认 |

### 10.2 待确认问题
- 任务项组件真实路径。
- 失败反馈使用 Toast 还是行内提示。
- 后端返回字段是 completed 还是 status。

## 11. 给下一个实现 Agent 的执行指令
\`\`\`yaml
implementation_contract:
  author: SolutionDesign Agent
  objective: 强化任务列表完成按钮视觉层级，并补充完成态反馈
  must_do:
    - 先读取仓库，确认真实路径
    - 复用现有状态字段与样式体系
    - 补充自动化测试
  must_not_do:
    - 不要编造不存在的文件路径
    - 不要新增无关功能
\`\`\`

## 12. 一致性自检
| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 覆盖需求目标 | 通过 | 覆盖按钮强化与状态反馈 |
| 未编造代码路径 | 通过 | 不确定项已进入待确认 |
| 可交给实现 Agent | 通过 | 包含实施步骤和执行指令 |`,
    json: {
      changedFiles: ["TaskItem.tsx", "task-list.css", "TaskItem.test.tsx"],
      strategy: "minimal scoped frontend change",
      riskLevel: "low",
    },
    logs: ["Design Agent started", "Analyzing codebase context", "Generated implementation plan"],
  },
  {
    id: "code",
    name: "代码生成",
    agent: "Code Agent",
    status: "waiting",
    duration: "0.0s",
    input: "Approved technical design + target component files",
    output: `diff --git a/src/components/TaskItem.tsx b/src/components/TaskItem.tsx
- <button className="task-action">完成</button>
+ <button className="task-action task-action-primary" disabled={task.completed}>
+   {task.completed ? "已完成" : "完成"}
+ </button>

diff --git a/src/styles/task-list.css b/src/styles/task-list.css
+.task-action-primary {
+  color: #fff;
+  background: linear-gradient(135deg, #3370ff 0%, #7c3aed 100%);
+  box-shadow: 0 8px 18px rgba(51, 112, 255, 0.24);
+  transition: transform 160ms ease, box-shadow 160ms ease;
+}
+
+.task-action-primary:hover {
+  transform: translateY(-1px);
+  box-shadow: 0 12px 24px rgba(51, 112, 255, 0.3);
+}
+
+.task-action-primary:disabled {
+  opacity: 0.72;
+  cursor: default;
+  transform: none;
+}`,
    json: {
      diffSummary: ["removed plain button style", "added primary button style", "added completed label"],
      filesTouched: 2,
    },
    logs: ["Code Agent started", "Applying component changes", "Generated frontend diff"],
  },
  {
    id: "test",
    name: "测试生成",
    agent: "Test Agent",
    status: "waiting",
    duration: "0.0s",
    input: "Generated code diff + acceptance criteria",
    output: `import { fireEvent, render, screen } from "@testing-library/react";
import { TaskItem } from "../TaskItem";

it("renders completion button with primary class", () => {
  render(<TaskItem task={{ id: "1", title: "Review PR", completed: false }} />);
  expect(screen.getByRole("button", { name: "完成" })).toHaveClass("task-action-primary");
});

it("updates task state after completion", () => {
  const onComplete = vi.fn();
  render(<TaskItem task={{ id: "1", title: "Review PR", completed: false }} onComplete={onComplete} />);
  fireEvent.click(screen.getByRole("button", { name: "完成" }));
  expect(onComplete).toHaveBeenCalledWith("1");
});

Test Results
- 5 passed
- 0 failed
- coverage 86%
- hover class exists
- abnormal state does not update incorrectly`,
    json: {
      passed: 5,
      failed: 0,
      coverage: "86%",
      assertions: ["render", "click state", "hover class", "abnormal state"],
    },
    logs: ["Test Agent started", "Generating interaction tests", "Test suite completed"],
  },
  {
    id: "review",
    name: "代码评审",
    agent: "Review Agent",
    status: "waiting",
    duration: "0.0s",
    checkpoint: true,
    checkpointLabel: "代码评审确认",
    checkpointDescription: "AI 已生成代码评审报告，请确认是否允许进入交付集成阶段。",
    input: "Generated diff + test results + acceptance criteria",
    output: `# Review Report

## 正确性
实现符合需求描述：完成按钮获得更高视觉层级，点击后状态文案变化明确。

## 可维护性
样式类名清晰，组件结构未被破坏；状态展示逻辑集中在按钮文案和 disabled 状态中。

## UI 一致性
按钮视觉层级更明确，蓝紫渐变与 SaaS 风格一致，hover 反馈克制。

## 风险项
需要确认主按钮样式是否符合设计规范，尤其是渐变色和阴影 Token。

## 测试结果
- 5 passed
- 0 failed
- coverage 86%
- hover class exists
- abnormal state does not update incorrectly

## 优化建议
后续可抽象为统一 Button 组件，减少多处按钮样式分叉。`,
    json: {
      correctness: "pass",
      maintainability: "pass",
      uiConsistency: "pass_with_design_confirmation",
      tests: { passed: 5, failed: 0, coverage: "86%" },
      checkpoint: true,
    },
    logs: ["Review Agent started", "Analyzing generated diff", "Waiting for human approval"],
  },
  {
    id: "merge",
    name: "交付集成",
    agent: "Merge Agent",
    status: "waiting",
    duration: "0.0s",
    input: "Approved review report + generated artifacts",
    output: `# Delivery Result

## MR Summary
Enhance task completion button visual hierarchy and completed-state feedback.

## Changed Files
- src/components/TaskItem.tsx
- src/styles/task-list.css
- src/components/__tests__/TaskItem.test.tsx

## Delivery Checklist
- Requirement mapped to implementation
- Tests generated and passed
- Review checkpoint approved
- Merge package ready

## Final Status
Ready to Merge`,
    json: {
      finalStatus: "Ready to Merge",
      changedFiles: 3,
      checklist: ["implementation", "tests", "review", "delivery"],
    },
    logs: ["Merge Agent started", "Preparing delivery package"],
  },
];

export const mockPipeline: Pipeline = {
  id: "demo-001",
  name: "AI DevFlow Pipeline",
  status: "Running",
  provider: "GPT-4",
  totalDuration: "0.0s",
  requirement: exampleRequirement,
  stages: initialStages,
};
