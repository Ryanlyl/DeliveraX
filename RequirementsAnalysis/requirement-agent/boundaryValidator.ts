import type { RequirementSpec, RequirementValidationError, RequirementValidationResult } from "./types";

const BOUNDARY_RULES: Array<{
  category: string;
  messagePrefix: string;
  keywords: string[];
}> = [
  {
    category: "framework",
    messagePrefix: "需求分析阶段不应包含框架或技术选型内容",
    keywords: ["React", "Vue", "Next.js", "Nuxt", "Svelte"],
  },
  {
    category: "state",
    messagePrefix: "需求分析阶段不应包含状态管理方案内容",
    keywords: ["useState", "Redux", "Zustand", "MobX", "Pinia", "状态管理方案"],
  },
  {
    category: "code_structure",
    messagePrefix: "需求分析阶段不应包含代码结构或文件组织内容",
    keywords: ["文件路径", "组件拆分", "目录结构", "service 层", "hooks", "utils", "components 目录"],
  },
  {
    category: "api_design",
    messagePrefix: "需求分析阶段不应包含接口设计内容",
    keywords: [
      "API 路径",
      "接口设计",
      "请求方法",
      "GET",
      "POST",
      "axios",
      "fetch",
      "接口对接",
      "获取任务列表接口",
      "更新任务完成状态接口",
      "具体接口",
      "触发接口",
      "调用接口",
      "接口返回成功",
      "接口返回失败",
      "请求成功",
      "请求失败",
    ],
  },
  {
    category: "ui_implementation",
    messagePrefix: "需求分析阶段不应包含具体 UI 控件或反馈载体",
    keywords: ["checkbox", "复选框", "toast", "Toast", "弹窗", "Modal", "Drawer"],
  },
  {
    category: "implementation_process",
    messagePrefix: "需求分析阶段不应包含开发、联调或测试实现流程",
    keywords: ["UI开发完成", "接口对接完成", "测试通过", "开发完成", "单元测试", "集成测试", "自动化测试", "QA验证"],
  },
  {
    category: "test_implementation",
    messagePrefix: "需求分析阶段不应包含测试实现内容",
    keywords: ["Vitest", "Jest", "Playwright", "测试文件", "Mock 数据", "mock 文件"],
  },
];

export function validateTextBoundary(text: string): RequirementValidationResult {
  const errors: RequirementValidationError[] = [];

  for (const rule of BOUNDARY_RULES) {
    for (const keyword of rule.keywords) {
      if (text.includes(keyword)) {
        errors.push({
          category: rule.category,
          keyword,
          message: `${rule.messagePrefix}：${keyword}`,
        });
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

export function validateRequirementBoundary(spec: RequirementSpec): RequirementValidationResult {
  return validateTextBoundary(JSON.stringify(spec));
}
