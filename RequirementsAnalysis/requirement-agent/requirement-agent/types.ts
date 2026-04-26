export type RequirementStatus = "Draft" | "In Review" | "Approved" | "Rejected" | "待确认" | string;

export interface RequirementSpec {
  basicInfo: {
    requirementName: string;
    requirementType: string;
    priority: string;
    owner: string;
    relatedPageOrModule: string;
    estimatedDeliveryTime: string;
    status: RequirementStatus;
  };
  background: {
    context: string;
    currentProblems: string[];
    targetUsers: string[];
    scenarios: string[];
    entryPoints: string[];
  };
  goals: {
    inScope: string[];
    outOfScope: string[];
  };
  impactScope: {
    pagesOrModules: string[];
    userRoles: string[];
    businessFlows: string[];
    dataOrApiScenarios: string[];
  };
  uiux: {
    pageStructure: string[];
    visualRequirements: string[];
    responsiveRequirements: string[];
    interactionRequirements: string[];
  };
  acceptanceCriteria: {
    checklist: string[];
    gherkinScenarios: string[];
  };
  performanceRequirements: string[];
  compatibilityRequirements: string[];
  copywriting: {
    normalCopy: string[];
    errorCopy: string[];
  };
  risks: Array<{
    risk: string;
    impact: string;
    mitigation: string;
  }>;
  definitionOfDone: string[];
  openQuestions: string[];
}

export interface RequirementBoundaryValidation {
  valid: boolean;
  errors: RequirementValidationError[];
}

export type RequirementValidationResult = RequirementBoundaryValidation;

export interface RequirementValidationError {
  category: string;
  keyword: string;
  message: string;
}

export interface RequirementAnalysisInput {
  userInput: string;
  llmCall: (prompt: string) => Promise<string>;
}

export interface RequirementAnalysisResult {
  spec: RequirementSpec | null;
  markdown: string | null;
  status: "In Review" | "Failed";
  validation: RequirementBoundaryValidation;
  error?: {
    code: string;
    message: string;
  };
}
