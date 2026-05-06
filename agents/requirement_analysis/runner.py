from __future__ import annotations

import json
import time
from typing import Any

from pydantic import ValidationError

from .boundary_validator import (
    validate_requirement_boundary,
    validate_text_boundary,
)
from .errors import failed_result
from .input_validator import validate_requirement_input
from .markdown_renderer import render_requirement_markdown
from .models import (
    AnalyzeRawOutputFailed,
    AnalyzeRawOutputResult,
    AnalyzeRawOutputSuccess,
    AnalysisMeta,
    AnalyzerOptions,
    LlmCall,
    RequirementAnalysisError,
    RequirementAnalysisInput,
    RequirementAnalysisResult,
    RequirementBoundaryValidation,
    RequirementValidationError,
)
from .prompts import build_fix_prompt, build_requirement_prompt
from .spec_validator import validate_requirement_spec_shape

SOFT_BOUNDARY_HINT_KEYWORDS = [
    "从接口获取",
    "请求数据",
    "调用接口获取",
    "接口返回数据",
    "拉取数据",
]
SOFT_BOUNDARY_HINT = """用户输入中包含偏实现表达，请在生成需求时进行语义纠正：
- 将‘接口/请求’相关表达转为‘读取数据/加载数据’
- 不要描述技术实现方式，只描述用户可感知行为和结果"""


def _invalid_json_error() -> RequirementValidationError:
    return RequirementValidationError(
        category="llm", keyword="JSON", message="LLM 返回内容不是合法 JSON"
    )


def _detect_soft_boundary_hints(user_input: str) -> bool:
    return any(
        keyword in user_input for keyword in SOFT_BOUNDARY_HINT_KEYWORDS
    )


def _build_prompt_with_soft_boundary_hint(user_input: str) -> str:
    prompt = build_requirement_prompt(user_input)
    if not _detect_soft_boundary_hints(user_input):
        return prompt
    return f"{SOFT_BOUNDARY_HINT}\n\n{prompt}"


def _parse_requirement_spec(llm_response: str) -> Any:
    return json.loads(llm_response)


def _analyze_raw_output(raw_output: str) -> AnalyzeRawOutputResult:
    try:
        parsed = _parse_requirement_spec(raw_output)
    except json.JSONDecodeError:
        return AnalyzeRawOutputFailed(ok=False, errors=[_invalid_json_error()])

    valid_shape, shape_errors, spec = validate_requirement_spec_shape(parsed)
    if not valid_shape or spec is None:
        return AnalyzeRawOutputFailed(ok=False, errors=shape_errors)

    boundary = validate_requirement_boundary(spec)
    if not boundary.valid:
        return AnalyzeRawOutputFailed(ok=False, errors=boundary.errors)

    markdown = render_requirement_markdown(spec)
    return AnalyzeRawOutputSuccess(
        ok=True,
        spec=spec,
        markdown=markdown,
        validation=RequirementBoundaryValidation(valid=True, errors=[]),
    )


async def run_requirement_analysis(
    input_data: RequirementAnalysisInput | dict[str, Any],
    llm_call: LlmCall,
    options: AnalyzerOptions | None = None,
) -> RequirementAnalysisResult:
    opts = options or AnalyzerOptions()
    if isinstance(input_data, dict):
        input_model = RequirementAnalysisInput.model_validate(input_data)
    else:
        input_model = input_data

    input_validation = validate_requirement_input(input_model.userInput)
    if input_validation:
        return input_validation

    input_boundary_validation = validate_text_boundary(input_model.userInput)
    if not input_boundary_validation.valid:
        return failed_result(
            "INPUT_BOUNDARY_VIOLATION",
            "输入需求包含方案设计或实现细节，请仅描述前端需求目标、用户行为和验收标准",
            validation=input_boundary_validation,
        )

    prompt = _build_prompt_with_soft_boundary_hint(input_model.userInput)

    begin_ms = time.perf_counter_ns() // 1_000_000
    attempts = 0
    last_errors: list[RequirementValidationError] = []
    try:
        raw_output = await llm_call(prompt)
        attempts += 1
        first_analysis = _analyze_raw_output(raw_output)
        if first_analysis.ok:
            elapsed = (time.perf_counter_ns() // 1_000_000) - begin_ms
            return RequirementAnalysisResult(
                spec=first_analysis.spec,
                markdown=first_analysis.markdown,
                status="In Review",
                validation=first_analysis.validation,
                issues=[] if not opts.includeIssues else [],
                meta=AnalysisMeta(
                    promptVersion=opts.promptVersion,
                    attempts=attempts,
                    model=opts.providerName,
                    latencyMs=elapsed,
                ),
            )

        last_errors = first_analysis.errors
        retry_count = 0
        while retry_count < opts.maxRetry:
            retry_count += 1
            fix_prompt = build_fix_prompt(
                prompt, raw_output, [err.model_dump() for err in last_errors]
            )
            raw_output = await llm_call(fix_prompt)
            attempts += 1
            fixed = _analyze_raw_output(raw_output)
            if fixed.ok:
                elapsed = (time.perf_counter_ns() // 1_000_000) - begin_ms
                return RequirementAnalysisResult(
                    spec=fixed.spec,
                    markdown=fixed.markdown,
                    status="In Review",
                    validation=fixed.validation,
                    issues=[] if not opts.includeIssues else [],
                    meta=AnalysisMeta(
                        promptVersion=opts.promptVersion,
                        attempts=attempts,
                        model=opts.providerName,
                        latencyMs=elapsed,
                    ),
                )
            last_errors = fixed.errors
    except ValidationError as err:
        return failed_result("INPUT_VALIDATION_ERROR", str(err))

    elapsed = (time.perf_counter_ns() // 1_000_000) - begin_ms
    return RequirementAnalysisResult(
        spec=None,
        markdown=None,
        status="Failed",
        validation=RequirementBoundaryValidation(
            valid=False, errors=last_errors
        ),
        error=RequirementAnalysisError(
            code="AUTO_FIX_FAILED",
            message="自动修复后仍不符合 ReqAnalysis 输出要求",
        ),
        issues=last_errors if opts.includeIssues else [],
        meta=AnalysisMeta(
            promptVersion=opts.promptVersion,
            attempts=attempts,
            model=opts.providerName,
            latencyMs=elapsed,
        ),
    )
