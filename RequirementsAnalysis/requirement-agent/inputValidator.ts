import type { RequirementAnalysisResult } from "./types";

const FRONTEND_REQUIREMENT_KEYWORDS = [
  "页面",
  "按钮",
  "表单",
  "弹窗",
  "列表",
  "交互",
  "样式",
  "移动端",
  "登录",
  "展示",
  "点击",
  "输入",
  "提交",
  "错误提示",
  "loading",
  "空状态",
  "UI",
  "UX",
  "前端",
  "页面改版",
  "组件",
  "布局",
  "响应式",
  "文案",
  "Toast",
  "Drawer",
  "Modal",
];

function failedInputValidation(code: string, message: string): RequirementAnalysisResult {
  return {
    spec: null,
    markdown: null,
    status: "Failed",
    validation: {
      valid: false,
      errors: [],
    },
    error: {
      code,
      message,
    },
  };
}

export function validateRequirementInput(userInput: string): RequirementAnalysisResult | null {
  const trimmedInput = userInput.trim();

  if (trimmedInput.length === 0) {
    return failedInputValidation("EMPTY_INPUT", "请输入前端需求描述");
  }

  const compactInput = trimmedInput.replace(/\s/g, "");
  if (compactInput.length < 10) {
    return failedInputValidation("INPUT_TOO_SHORT", "需求描述过短，请补充目标、页面或交互信息");
  }

  const isFrontendRequirement = FRONTEND_REQUIREMENT_KEYWORDS.some((keyword) => trimmedInput.includes(keyword));
  if (!isFrontendRequirement) {
    return failedInputValidation("NOT_FRONTEND_REQUIREMENT", "当前需求不属于前端需求分析范围");
  }

  return null;
}
