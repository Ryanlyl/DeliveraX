import type { RequirementValidationError } from "./types";

const REQUIRED_TOP_LEVEL_FIELDS = [
  "basicInfo",
  "background",
  "goals",
  "impactScope",
  "uiux",
  "acceptanceCriteria",
  "performanceRequirements",
  "compatibilityRequirements",
  "copywriting",
  "risks",
  "definitionOfDone",
  "openQuestions",
];

const REQUIRED_FIELD_PATHS = [
  "basicInfo.requirementName",
  "basicInfo.requirementType",
  "basicInfo.priority",
  "basicInfo.status",
  "background.context",
  "goals.inScope",
  "goals.outOfScope",
  "acceptanceCriteria.checklist",
  "acceptanceCriteria.gherkinScenarios",
];

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasPath(value: unknown, path: string): boolean {
  const segments = path.split(".");
  let current: unknown = value;

  for (const segment of segments) {
    if (!isObject(current) || !(segment in current)) {
      return false;
    }

    current = current[segment];
  }

  return true;
}

function missingFieldError(path: string): RequirementValidationError {
  return {
    category: "schema",
    keyword: path,
    message: `LLM 返回内容缺少必要字段：${path}`,
  };
}

export function validateRequirementSpecShape(spec: unknown): {
  valid: boolean;
  errors: RequirementValidationError[];
} {
  const errors: RequirementValidationError[] = [];

  if (!isObject(spec)) {
    return {
      valid: false,
      errors: [missingFieldError("RequirementSpec")],
    };
  }

  for (const field of REQUIRED_TOP_LEVEL_FIELDS) {
    if (!hasPath(spec, field)) {
      errors.push(missingFieldError(field));
    }
  }

  for (const path of REQUIRED_FIELD_PATHS) {
    if (!hasPath(spec, path)) {
      errors.push(missingFieldError(path));
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
