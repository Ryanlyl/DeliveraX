from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field


class RequirementValidationError(BaseModel):
    category: str
    keyword: str
    message: str


class RequirementBoundaryValidation(BaseModel):
    valid: bool
    errors: list[RequirementValidationError] = Field(default_factory=list)


class BasicInfo(BaseModel):
    requirementName: str
    requirementType: str
    priority: str
    owner: str
    relatedPageOrModule: str
    estimatedDeliveryTime: str
    status: str


class Background(BaseModel):
    context: str
    currentProblems: list[str]
    targetUsers: list[str]
    scenarios: list[str]
    entryPoints: list[str]


class Goals(BaseModel):
    inScope: list[str]
    outOfScope: list[str]


class ImpactScope(BaseModel):
    pagesOrModules: list[str]
    userRoles: list[str]
    businessFlows: list[str]
    dataOrApiScenarios: list[str]


class UiUx(BaseModel):
    pageStructure: list[str]
    visualRequirements: list[str]
    responsiveRequirements: list[str]
    interactionRequirements: list[str]


class AcceptanceCriteria(BaseModel):
    checklist: list[str]
    gherkinScenarios: list[str]


class Copywriting(BaseModel):
    normalCopy: list[str]
    errorCopy: list[str]


class RiskItem(BaseModel):
    risk: str
    impact: str
    mitigation: str


class RequirementSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basicInfo: BasicInfo
    background: Background
    goals: Goals
    impactScope: ImpactScope
    uiux: UiUx
    acceptanceCriteria: AcceptanceCriteria
    performanceRequirements: list[str]
    compatibilityRequirements: list[str]
    copywriting: Copywriting
    risks: list[RiskItem]
    definitionOfDone: list[str]
    openQuestions: list[str]


class RequirementAnalysisError(BaseModel):
    code: str
    message: str


class RequirementAnalysisInput(BaseModel):
    userInput: str


class AnalysisMeta(BaseModel):
    promptVersion: str = "v1"
    attempts: int = 1
    model: str = "unknown"
    latencyMs: int = 0


class RequirementAnalysisResult(BaseModel):
    spec: RequirementSpec | None
    markdown: str | None
    status: Literal["In Review", "Failed"]
    validation: RequirementBoundaryValidation
    error: RequirementAnalysisError | None = None
    issues: list[RequirementValidationError] = Field(default_factory=list)
    meta: AnalysisMeta = Field(default_factory=AnalysisMeta)


LlmCall = Callable[[str], Awaitable[str]]


class AnalyzerOptions(BaseModel):
    maxRetry: int = 1
    providerName: str = "custom"
    promptVersion: str = "v1"
    includeIssues: bool = True
    includeMeta: bool = True


class AnalyzeRawOutputSuccess(BaseModel):
    ok: Literal[True]
    spec: RequirementSpec
    markdown: str
    validation: RequirementBoundaryValidation


class AnalyzeRawOutputFailed(BaseModel):
    ok: Literal[False]
    errors: list[RequirementValidationError]


AnalyzeRawOutputResult = AnalyzeRawOutputSuccess | AnalyzeRawOutputFailed


def to_plain_dict(model: BaseModel | None) -> dict[str, Any] | None:
    if model is None:
        return None
    return model.model_dump()
