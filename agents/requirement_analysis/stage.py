from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from stage_contracts import (
    ArtifactRef,
    StageRunRequest,
    StageRunResult,
    get_current_llm_config,
    resolve_stage_artifact_dir,
    write_stage_artifacts,
)

from .models import RequirementAnalysisInput
from .providers import deepseek_llm_call
from .runner import run_requirement_analysis


def _build_mock_spec() -> dict[str, Any]:
    return {
        "basicInfo": {
            "requirementName": "任务列表页面需求",
            "requirementType": "前端功能需求",
            "priority": "P1",
            "owner": "待确认",
            "relatedPageOrModule": "任务列表页",
            "estimatedDeliveryTime": "待确认",
            "status": "In Review",
        },
        "background": {
            "context": "用户需要查看任务并跟进完成情况。",
            "currentProblems": ["缺少清晰的任务查看能力"],
            "targetUsers": ["普通用户"],
            "scenarios": ["查看任务", "标记任务完成"],
            "entryPoints": ["任务入口"],
        },
        "goals": {
            "inScope": ["查看任务列表", "标记任务完成"],
            "outOfScope": ["不包含任务创建", "不包含任务删除"],
        },
        "impactScope": {
            "pagesOrModules": ["任务列表页"],
            "userRoles": ["普通用户"],
            "businessFlows": ["查看任务", "完成任务"],
            "dataOrApiScenarios": ["任务数据读取", "任务状态更新"],
        },
        "uiux": {
            "pageStructure": ["清晰呈现任务列表"],
            "visualRequirements": ["任务状态需要明确区分"],
            "responsiveRequirements": ["移动端需要可读且易操作"],
            "interactionRequirements": ["操作后需要有明确反馈"],
        },
        "acceptanceCriteria": {
            "checklist": ["用户可以看到任务列表", "用户可以标记任务完成"],
            "gherkinScenarios": [
                "Feature: 任务列表\nScenario: 查看任务\nGiven 用户进入任务列表页\nWhen 任务数据可用\nThen 用户可以看到任务列表"
            ],
        },
        "performanceRequirements": ["页面内容应及时展示"],
        "compatibilityRequirements": ["支持主流桌面和移动端浏览器"],
        "copywriting": {
            "normalCopy": ["任务", "已完成"],
            "errorCopy": ["任务加载失败，请稍后重试"],
        },
        "risks": [
            {
                "risk": "完成状态不清晰",
                "impact": "用户可能重复操作",
                "mitigation": "验收时确认状态表达清晰",
            }
        ],
        "definitionOfDone": ["需求文档已生成", "边界校验通过"],
        "openQuestions": ["是否允许撤销完成状态？"],
    }


async def _mock_llm_call(_: str) -> str:
    return json.dumps(_build_mock_spec(), ensure_ascii=False)


def _resolve_user_input(request: StageRunRequest) -> str:
    options = request.options
    if options.get("user_input"):
        return str(options["user_input"])
    if options.get("input_text"):
        return str(options["input_text"])
    if options.get("input_file"):
        return Path(str(options["input_file"])).read_text(encoding="utf-8")
    for artifact in request.input_artifacts:
        if artifact.type in {"text", "markdown"}:
            return Path(artifact.path).read_text(encoding="utf-8")
    return "请描述一个任务列表页面，用户可以查看任务并标记任务完成。"


async def run_stage(request: StageRunRequest) -> StageRunResult:
    started_at = datetime.now(timezone.utc)
    logs = ["ReqAnalysis stage started"]
    try:
        user_input = _resolve_user_input(request)
        runtime = get_current_llm_config()
        if runtime is not None:
            use_real_llm = bool(runtime.use_real_llm and not runtime.local_only)
        else:
            use_real_llm = bool(
                request.options.get("use_real_llm")
                or os.getenv("USE_REAL_LLM", "false").lower() == "true"
            )
        llm_call = deepseek_llm_call if use_real_llm else _mock_llm_call
        logs.append("Using real LLM" if use_real_llm else "Using deterministic local mock")

        analysis = await run_requirement_analysis(
            RequirementAnalysisInput(userInput=user_input),
            llm_call=llm_call,
        )

        stage_dir = resolve_stage_artifact_dir(request)
        stage_dir.mkdir(parents=True, exist_ok=True)
        output_artifacts: list[ArtifactRef] = []
        if analysis.spec is not None:
            spec_path = stage_dir / "requirement_spec.json"
            spec_path.write_text(
                json.dumps(analysis.spec.model_dump(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            output_artifacts.append(
                ArtifactRef(name="requirement_spec", type="json", path=str(spec_path), role="machine")
            )
        if analysis.markdown is not None:
            prd_path = stage_dir / "requirement_prd.md"
            prd_path.write_text(analysis.markdown.rstrip() + "\n", encoding="utf-8")
            output_artifacts.append(
                ArtifactRef(name="requirement_prd", type="markdown", path=str(prd_path), role="handoff")
            )

        ended_at = datetime.now(timezone.utc)
        requires_approval = bool(request.options.get("requires_approval", True))
        status = "failed" if analysis.status == "Failed" else "pending_approval" if requires_approval else "succeeded"
        result = StageRunResult(
            pipeline_id=request.pipeline_id,
            stage_id=request.stage_id,
            run_id=request.run_id,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=max(0, int((ended_at - started_at).total_seconds() * 1000)),
            input_artifacts=request.input_artifacts,
            output_artifacts=output_artifacts,
            human_output=analysis.markdown,
            data=analysis.model_dump(mode="json"),
            logs=[*logs, f"ReqAnalysis completed with status: {analysis.status}"],
        )
        return write_stage_artifacts(
            request=request,
            result=result,
            input_payload={"user_input": user_input, "options": request.options},
        )
    except Exception as exc:
        result = StageRunResult.from_exception(request=request, started_at=started_at, exc=exc, logs=logs)
        return write_stage_artifacts(request=request, result=result)
