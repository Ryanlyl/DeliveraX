import assert from "node:assert/strict";
import test from "node:test";
import { validateRequirementBoundary } from "./boundaryValidator";
import { renderRequirementMarkdown } from "./markdownRenderer";
import { runRequirementAnalysis } from "./requirementAgent";
import type { RequirementSpec } from "./types";

function createValidSpec(overrides: Partial<RequirementSpec> = {}): RequirementSpec {
  return {
    basicInfo: {
      requirementName: "任务列表页需求",
      requirementType: "前端功能需求",
      priority: "P1",
      owner: "待确认",
      relatedPageOrModule: "任务列表页",
      estimatedDeliveryTime: "待确认",
      status: "In Review",
    },
    background: {
      context: "用户需要查看任务并跟进完成情况。",
      currentProblems: ["缺少清晰的任务查看能力"],
      targetUsers: ["普通用户"],
      scenarios: ["查看任务", "标记任务完成"],
      entryPoints: ["任务入口"],
    },
    goals: {
      inScope: ["查看任务列表", "标记任务完成"],
      outOfScope: ["不包含任务创建", "不包含任务删除"],
    },
    impactScope: {
      pagesOrModules: ["任务列表页"],
      userRoles: ["普通用户"],
      businessFlows: ["查看任务", "完成任务"],
      dataOrApiScenarios: ["任务数据读取", "任务状态更新"],
    },
    uiux: {
      pageStructure: ["清晰呈现任务列表"],
      visualRequirements: ["任务状态需要明确区分"],
      responsiveRequirements: ["移动端需要可读且易操作"],
      interactionRequirements: ["操作后需要有明确反馈"],
    },
    acceptanceCriteria: {
      checklist: ["用户可以看到任务列表", "用户可以标记任务完成"],
      gherkinScenarios: [
        "Feature: 任务列表\nScenario: 查看任务\nGiven 用户进入任务列表页\nWhen 任务数据可用\nThen 用户可以看到任务列表",
      ],
    },
    performanceRequirements: ["页面内容应及时展示"],
    compatibilityRequirements: ["支持主流桌面和移动端浏览器"],
    copywriting: {
      normalCopy: ["任务", "已完成"],
      errorCopy: ["任务加载失败，请稍后重试"],
    },
    risks: [
      {
        risk: "完成状态不清晰",
        impact: "用户可能重复操作",
        mitigation: "验收时确认状态表达清晰",
      },
    ],
    definitionOfDone: ["需求文档已生成", "边界校验通过"],
    openQuestions: ["是否允许撤销完成状态？"],
    ...overrides,
  };
}

test("正常自然语言输入可以生成 markdown", async () => {
  const spec = createValidSpec();
  let llmCalled = false;
  const result = await runRequirementAnalysis({
    userInput: "我想做一个任务列表页。",
    llmCall: async () => {
      llmCalled = true;
      return JSON.stringify(spec);
    },
  });

  assert.equal(llmCalled, true);
  assert.equal(result.validation.valid, true);
  assert.equal(result.status, "In Review");
  assert.equal(result.error, undefined);
  assert.ok(result.markdown);
  assert.ok(result.markdown?.includes("# Frontend Feature PRD"));
  assert.ok(result.markdown?.includes("## 6. 验收标准"));
  assert.ok(result.markdown?.includes("## 11. Definition of Done"));
  assert.ok(result.markdown?.includes("## 12. 待确认问题"));
});

test("空输入返回 EMPTY_INPUT", async () => {
  let llmCalled = false;
  const result = await runRequirementAnalysis({
    userInput: "   ",
    llmCall: async () => {
      llmCalled = true;
      return "{}";
    },
  });

  assert.equal(result.status, "Failed");
  assert.equal(result.spec, null);
  assert.equal(result.markdown, null);
  assert.equal(result.validation.valid, false);
  assert.deepEqual(result.validation.errors, []);
  assert.equal(result.error?.code, "EMPTY_INPUT");
  assert.equal(result.error?.message, "请输入前端需求描述");
  assert.equal(llmCalled, false);
});

test("输入过短返回 INPUT_TOO_SHORT", async () => {
  let llmCalled = false;
  const result = await runRequirementAnalysis({
    userInput: "页面",
    llmCall: async () => {
      llmCalled = true;
      return "{}";
    },
  });

  assert.equal(result.status, "Failed");
  assert.equal(result.validation.valid, false);
  assert.deepEqual(result.validation.errors, []);
  assert.equal(result.error?.code, "INPUT_TOO_SHORT");
  assert.equal(result.error?.message, "需求描述过短，请补充目标、页面或交互信息");
  assert.equal(llmCalled, false);
});

test("非前端需求返回 NOT_FRONTEND_REQUIREMENT", async () => {
  let llmCalled = false;
  const result = await runRequirementAnalysis({
    userInput: "帮我规划后端数据库迁移和索引优化事项",
    llmCall: async () => {
      llmCalled = true;
      return "{}";
    },
  });

  assert.equal(result.status, "Failed");
  assert.equal(result.validation.valid, false);
  assert.deepEqual(result.validation.errors, []);
  assert.equal(result.error?.code, "NOT_FRONTEND_REQUIREMENT");
  assert.equal(result.error?.message, "当前需求不属于前端需求分析范围");
  assert.equal(llmCalled, false);
});

test("用户原始输入包含方案设计内容时返回 INPUT_BOUNDARY_VIOLATION", async () => {
  let llmCalled = false;
  const result = await runRequirementAnalysis({
    userInput: "做一个页面，用 React 写，调用接口获取数据，用useState管理状态",
    llmCall: async () => {
      llmCalled = true;
      return "{}";
    },
  });

  assert.equal(result.status, "Failed");
  assert.equal(result.spec, null);
  assert.equal(result.markdown, null);
  assert.equal(result.validation.valid, false);
  assert.equal(result.error?.code, "INPUT_BOUNDARY_VIOLATION");
  assert.equal(result.error?.message, "输入需求包含方案设计或实现细节，请仅描述前端需求目标、用户行为和验收标准");
  assert.ok(result.validation.errors.some((error) => error.category === "framework" && error.keyword === "React"));
  assert.ok(result.validation.errors.some((error) => error.category === "state" && error.keyword === "useState"));
  assert.ok(result.validation.errors.some((error) => error.category === "api_design" && error.keyword === "调用接口"));
  assert.equal(llmCalled, false);
});

test("弱越界表达会注入提示但不阻断需求分析", async () => {
  const spec = createValidSpec({
    goals: {
      inScope: ["读取数据", "展示数据"],
      outOfScope: ["不包含数据编辑能力"],
    },
    impactScope: {
      pagesOrModules: ["数据展示页"],
      userRoles: ["普通用户"],
      businessFlows: ["加载数据", "展示数据"],
      dataOrApiScenarios: ["读取数据", "数据异常时展示错误提示"],
    },
  });
  let receivedPrompt = "";

  const result = await runRequirementAnalysis({
    userInput: "做一个页面，从接口获取数据展示出来",
    llmCall: async (prompt) => {
      receivedPrompt = prompt;
      return JSON.stringify(spec);
    },
  });

  assert.ok(receivedPrompt.includes("用户输入中包含偏实现表达"));
  assert.equal(result.status, "In Review");
  assert.equal(result.validation.valid, true);
  assert.ok(result.markdown);
  assert.equal(result.markdown?.includes("接口获取"), false);
  assert.equal(result.markdown?.includes("请求数据"), false);
  assert.ok(result.markdown?.includes("读取数据"));
  assert.ok(result.markdown?.includes("展示数据"));
});

test("spec 中出现越界关键词时，boundaryValidator 返回分类错误", () => {
  const invalidSpec = createValidSpec({
    goals: {
      inScope: [
        "使用 React 实现任务列表",
        "通过 useState 管理完成状态",
        "补充 API 路径说明",
        "使用复选框完成标记",
        "接口对接完成",
        "获取任务列表接口可用",
        "用户操作后触发接口",
        "接口返回成功时展示列表",
        "接口返回失败时展示提示",
        "测试通过后进入下一阶段",
      ],
      outOfScope: ["待确认"],
    },
  });

  const validation = validateRequirementBoundary(invalidSpec);

  assert.equal(validation.valid, false);
  assert.ok(
    validation.errors.some((error) => error.category === "framework" && error.keyword === "React"),
  );
  assert.ok(validation.errors.some((error) => error.category === "state" && error.keyword === "useState"));
  assert.ok(validation.errors.some((error) => error.category === "api_design" && error.keyword === "API 路径"));
  assert.ok(validation.errors.some((error) => error.category === "api_design" && error.keyword === "获取任务列表接口"));
  assert.ok(validation.errors.some((error) => error.category === "api_design" && error.keyword === "触发接口"));
  assert.ok(validation.errors.some((error) => error.category === "api_design" && error.keyword === "接口返回成功"));
  assert.ok(validation.errors.some((error) => error.category === "api_design" && error.keyword === "接口返回失败"));
  assert.ok(validation.errors.some((error) => error.category === "ui_implementation" && error.keyword === "复选框"));
  assert.ok(validation.errors.some((error) => error.category === "implementation_process" && error.keyword === "测试通过"));
  assert.ok(
    validation.errors.some(
      (error) => error.category === "implementation_process" && error.keyword === "接口对接完成",
    ),
  );
});

test("第一次返回非法 JSON 时第二次修复成功", async () => {
  const spec = createValidSpec();
  let callCount = 0;

  const result = await runRequirementAnalysis({
    userInput: "我想做一个任务列表页。",
    llmCall: async () => {
      callCount += 1;
      return callCount === 1 ? "not json" : JSON.stringify(spec);
    },
  });

  assert.equal(callCount, 2);
  assert.equal(result.status, "In Review");
  assert.equal(result.validation.valid, true);
  assert.equal(result.error, undefined);
  assert.ok(result.spec);
  assert.ok(result.markdown?.includes("# Frontend Feature PRD"));
});

test("第一次返回 boundary 违规内容时第二次修复成功", async () => {
  const validSpec = createValidSpec();
  const invalidSpec = createValidSpec({
    goals: {
      inScope: ["接口返回成功时展示任务列表"],
      outOfScope: ["待确认"],
    },
  });
  let callCount = 0;

  const result = await runRequirementAnalysis({
    userInput: "我想做一个任务列表页。",
    llmCall: async () => {
      callCount += 1;
      return callCount === 1 ? JSON.stringify(invalidSpec) : JSON.stringify(validSpec);
    },
  });

  assert.equal(callCount, 2);
  assert.equal(result.status, "In Review");
  assert.equal(result.validation.valid, true);
  assert.equal(result.error, undefined);
  assert.ok(result.markdown?.includes("## 11. Definition of Done"));
});

test("两次都失败时返回 AUTO_FIX_FAILED", async () => {
  const invalidSpec = createValidSpec({
    goals: {
      outOfScope: ["待确认"],
    } as RequirementSpec["goals"],
  });

  const result = await runRequirementAnalysis({
    userInput: "我想做一个任务列表页。",
    llmCall: async () => JSON.stringify(invalidSpec),
  });

  assert.equal(result.status, "Failed");
  assert.equal(result.spec, null);
  assert.equal(result.markdown, null);
  assert.equal(result.validation.valid, false);
  assert.equal(result.error?.code, "AUTO_FIX_FAILED");
  assert.equal(result.error?.message, "自动修复后仍不符合 Requirement Agent 输出要求");
  assert.ok(
    result.validation.errors.some(
      (error) =>
        error.category === "schema" &&
        error.keyword === "goals.inScope" &&
        error.message === "LLM 返回内容缺少必要字段：goals.inScope",
    ),
  );
});

test("Markdown 渲染器为空字段填充待确认", () => {
  const markdown = renderRequirementMarkdown(
    createValidSpec({
      performanceRequirements: [],
      openQuestions: [],
    }),
  );

  assert.ok(markdown.includes("- 待确认"));
});

test("Markdown 渲染器始终输出第 11 和第 12 章并提供默认内容", () => {
  const markdown = renderRequirementMarkdown(
    createValidSpec({
      definitionOfDone: [],
      openQuestions: [],
    }),
  );

  assert.ok(markdown.includes("## 11. Definition of Done"));
  assert.ok(markdown.includes("- [ ] 需求目标已确认"));
  assert.ok(markdown.includes("- [ ] 验收标准已确认"));
  assert.ok(markdown.includes("- [ ] 无未解决的阻塞问题"));
  assert.ok(markdown.includes("## 12. 待确认问题"));
  assert.ok(markdown.includes("- 暂无"));
});
