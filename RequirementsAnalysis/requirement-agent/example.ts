import { deepseekLlmCall } from "./deepseekLlmCall";
import { runRequirementAnalysis } from "./requirementAgent";
import type { RequirementSpec } from "./types";

const userInput = "做一个评论列表，用户可以查看评论内容、点赞评论，点赞后数量增加，如果失败需要提示";

const mockSpec: RequirementSpec = {
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
    context: "用户需要在统一页面中查看任务并跟进任务完成情况，以提升任务处理效率。",
    currentProblems: ["当前缺少清晰的任务查看入口", "用户完成任务后的状态反馈不够明确", "移动端访问体验需要保障"],
    targetUsers: ["需要处理任务的普通用户"],
    scenarios: ["用户进入任务列表查看待处理任务", "用户完成任务后将任务标记为完成", "任务数据获取异常时用户需要获得明确提示"],
    entryPoints: ["任务相关导航入口", "业务流程中的任务入口"],
  },
  goals: {
    inScope: ["支持用户查看任务列表", "支持用户将任务标记为完成", "支持移动端正常浏览和操作", "在数据异常时展示可理解的错误提示"],
    outOfScope: ["不包含任务创建能力", "不包含任务编辑能力", "不包含任务删除能力", "不包含批量操作能力"],
  },
  impactScope: {
    pagesOrModules: ["任务列表页"],
    userRoles: ["普通用户"],
    businessFlows: ["查看任务", "完成任务", "异常提示"],
    dataOrApiScenarios: ["任务列表数据读取", "任务完成状态更新", "数据异常或更新失败反馈"],
  },
  uiux: {
    pageStructure: ["页面需要清晰呈现任务列表", "每条任务需要展示任务名称和完成状态", "用户应能识别可完成的任务操作"],
    visualRequirements: ["任务状态需要有明确区分", "错误提示需要醒目但不干扰用户继续理解页面"],
    responsiveRequirements: ["移动端需要保持任务信息可读", "移动端操作区域需要便于点击"],
    interactionRequirements: ["用户标记完成后需要看到状态变化", "异常时需要展示明确提示文案"],
  },
  acceptanceCriteria: {
    checklist: [
      "用户可以进入任务列表页并看到任务信息",
      "用户可以将未完成任务标记为完成",
      "任务完成后页面能体现完成状态",
      "移动端可以正常查看任务列表并完成操作",
      "数据异常时页面展示错误提示",
    ],
    gherkinScenarios: [
      "Feature: 任务列表查看\nScenario: 用户查看任务\nGiven 用户进入任务列表页\nWhen 任务数据可用\nThen 用户可以看到任务列表",
      "Feature: 标记任务完成\nScenario: 用户完成任务\nGiven 用户看到一个未完成任务\nWhen 用户将该任务标记为完成\nThen 该任务展示为已完成状态",
      "Feature: 异常提示\nScenario: 任务数据异常\nGiven 用户进入任务列表页\nWhen 任务数据无法正常获取\nThen 页面展示错误提示",
    ],
  },
  performanceRequirements: ["任务列表页在常规数据量下应及时完成内容展示", "用户操作后的反馈应及时可感知"],
  compatibilityRequirements: ["支持主流桌面浏览器访问", "支持主流移动端浏览器访问"],
  copywriting: {
    normalCopy: ["任务", "已完成", "标记为完成"],
    errorCopy: ["任务加载失败，请稍后重试", "任务状态更新失败，请稍后重试"],
  },
  risks: [
    {
      risk: "任务状态变化后用户感知不明确",
      impact: "用户可能重复操作或误以为操作失败",
      mitigation: "需求验收中明确完成状态展示和反馈要求",
    },
    {
      risk: "移动端任务信息展示拥挤",
      impact: "影响用户阅读和操作效率",
      mitigation: "需求验收中覆盖移动端可读性和可操作性",
    },
  ],
  definitionOfDone: ["结构化需求文档已生成", "越界内容校验通过", "需求范围与待确认问题已可供评审"],
  openQuestions: ["任务列表中是否需要展示截止时间、负责人等附加信息？", "任务完成后是否允许撤销完成状态？", "异常提示是否需要提供重试入口？"],
};

async function mockLlmCall(): Promise<string> {
  return JSON.stringify(mockSpec);
}

const llmCall = process.env.USE_REAL_LLM === "true" ? deepseekLlmCall : mockLlmCall;

console.log("LLM mode:", process.env.USE_REAL_LLM === "true" ? "deepseek" : "mock");

runRequirementAnalysis({
  userInput,
  llmCall,
})
  .then((result) => {
    console.log("status:");
    console.log(result.status);
    console.log("validation:");
    console.log(JSON.stringify(result.validation, null, 2));
    console.log("error:");
    console.log(result.error ? JSON.stringify(result.error, null, 2) : "undefined");
    console.log("\nmarkdown:");
    console.log(result.markdown);
  })
  .catch((error) => {
    console.error(error);
  });
