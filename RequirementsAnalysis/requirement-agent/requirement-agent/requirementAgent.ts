import { validateRequirementBoundary, validateTextBoundary } from "./boundaryValidator";
import { validateRequirementInput } from "./inputValidator";
import { renderRequirementMarkdown } from "./markdownRenderer";
import { buildFixPrompt, buildRequirementPrompt } from "./prompts";
import { validateRequirementSpecShape } from "./specValidator";
import type {
  RequirementAnalysisInput,
  RequirementAnalysisResult,
  RequirementSpec,
  RequirementValidationError,
} from "./types";

const MAX_RETRY = 1;
const SOFT_BOUNDARY_HINT_KEYWORDS = ["从接口获取", "请求数据", "调用接口获取", "接口返回数据", "拉取数据"];
const SOFT_BOUNDARY_HINT = `用户输入中包含偏实现表达，请在生成需求时进行语义纠正：
- 将‘接口/请求’相关表达转为‘读取数据/加载数据’
- 不要描述技术实现方式，只描述用户可感知行为和结果`;

function parseRequirementSpec(llmResponse: string): unknown {
  return JSON.parse(llmResponse) as unknown;
}

function invalidJsonError(): RequirementValidationError {
  return {
    category: "llm",
    keyword: "JSON",
    message: "LLM 返回内容不是合法 JSON",
  };
}

function detectSoftBoundaryHints(userInput: string): boolean {
  return SOFT_BOUNDARY_HINT_KEYWORDS.some((keyword) => userInput.includes(keyword));
}

function buildPromptWithSoftBoundaryHint(userInput: string): string {
  const prompt = buildRequirementPrompt(userInput);
  if (!detectSoftBoundaryHints(userInput)) {
    return prompt;
  }

  return `${SOFT_BOUNDARY_HINT}\n\n${prompt}`;
}

function analyzeRawOutput(rawOutput: string):
  | {
      ok: true;
      spec: RequirementSpec;
      markdown: string;
      validation: { valid: true; errors: [] };
    }
  | {
      ok: false;
      errors: RequirementValidationError[];
    } {
  let parsedSpec: unknown;

  try {
    parsedSpec = parseRequirementSpec(rawOutput);
  } catch {
    return {
      ok: false,
      errors: [invalidJsonError()],
    };
  }

  const schemaValidation = validateRequirementSpecShape(parsedSpec);
  if (!schemaValidation.valid) {
    return {
      ok: false,
      errors: schemaValidation.errors,
    };
  }

  const spec = parsedSpec as RequirementSpec;
  const validation = validateRequirementBoundary(spec);
  if (!validation.valid) {
    return {
      ok: false,
      errors: validation.errors,
    };
  }

  return {
    ok: true,
    spec,
    markdown: renderRequirementMarkdown(spec),
    validation: {
      valid: true,
      errors: [],
    },
  };
}

export async function runRequirementAnalysis(input: RequirementAnalysisInput): Promise<RequirementAnalysisResult> {
  const { userInput, llmCall } = input;
  const inputValidation = validateRequirementInput(userInput);
  if (inputValidation) {
    return inputValidation;
  }

  const inputBoundaryValidation = validateTextBoundary(userInput);
  if (!inputBoundaryValidation.valid) {
    return {
      spec: null,
      markdown: null,
      status: "Failed",
      validation: inputBoundaryValidation,
      error: {
        code: "INPUT_BOUNDARY_VIOLATION",
        message: "输入需求包含方案设计或实现细节，请仅描述前端需求目标、用户行为和验收标准",
      },
    };
  }

  const prompt = buildPromptWithSoftBoundaryHint(userInput);
  const rawOutput = await llmCall(prompt);
  const firstAnalysis = analyzeRawOutput(rawOutput);
  if (firstAnalysis.ok) {
    return {
      spec: firstAnalysis.spec,
      markdown: firstAnalysis.markdown,
      status: "In Review",
      validation: firstAnalysis.validation,
    };
  }

  let lastErrors = firstAnalysis.errors;
  let retryCount = 0;
  while (retryCount < MAX_RETRY) {
    retryCount += 1;
    const fixPrompt = buildFixPrompt(prompt, rawOutput, lastErrors);
    const fixedRawOutput = await llmCall(fixPrompt);
    const fixedAnalysis = analyzeRawOutput(fixedRawOutput);

    if (fixedAnalysis.ok) {
      return {
        spec: fixedAnalysis.spec,
        markdown: fixedAnalysis.markdown,
        status: "In Review",
        validation: fixedAnalysis.validation,
      };
    }

    lastErrors = fixedAnalysis.errors;
  }

  return {
    spec: null,
    markdown: null,
    status: "Failed",
    validation: {
      valid: false,
      errors: lastErrors,
    },
    error: {
      code: "AUTO_FIX_FAILED",
      message: "自动修复后仍不符合 Requirement Agent 输出要求",
    },
  };
}
