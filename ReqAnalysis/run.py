import argparse
import asyncio
import json
import os
from pathlib import Path

from requirement_analysis import RequirementAnalysisInput, run_requirement_analysis
from requirement_analysis.local_debug import write_local_debug_artifacts
from requirement_analysis.providers import deepseek_llm_call


def build_mock_spec() -> dict:
    return {
        "basicInfo": {
            "requirementName": "任务列表页需求",
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
                (
                    "Feature: 任务列表\n"
                    "Scenario: 查看任务\n"
                    "Given 用户进入任务列表页\n"
                    "When 任务数据可用\n"
                    "Then 用户可以看到任务列表"
                )
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


async def mock_llm_call(_: str) -> str:
    return json.dumps(build_mock_spec(), ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run RequirementAnalysis locally and save debug artifacts."
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Path to unstructured requirement input text file.",
    )
    parser.add_argument(
        "--user-input",
        type=str,
        default=None,
        help=(
            "Direct raw requirement text input "
            "(overridden by --input-file when provided)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Directory where local debug artifacts are saved.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional run directory name under output dir.",
    )
    parser.add_argument(
        "--use-real-llm",
        action="store_true",
        help="Use DeepSeek API call instead of mock output.",
    )
    return parser.parse_args()


def resolve_user_input(input_file: str | None, user_input: str | None) -> str:
    if input_file:
        return Path(input_file).read_text(encoding="utf-8")
    if user_input:
        return user_input
    return "做一个评论列表，用户可以查看评论内容、点赞评论，点赞后数量增加，如果失败需要提示"


async def main() -> None:
    args = parse_args()
    user_input = resolve_user_input(args.input_file, args.user_input)
    use_real_llm = (
        args.use_real_llm
        or os.getenv("USE_REAL_LLM", "false").lower() == "true"
    )
    llm_call = deepseek_llm_call if use_real_llm else mock_llm_call

    result = await run_requirement_analysis(
        RequirementAnalysisInput(userInput=user_input),
        llm_call=llm_call,
    )
    artifacts = write_local_debug_artifacts(
        output_dir=Path(args.output_dir),
        user_input=user_input,
        result=result,
        run_id=args.run_id,
    )

    print("artifacts:")
    print(str(artifacts.run_dir))
    print("status:")
    print(result.status)
    print("validation:")
    print(
        json.dumps(
            result.validation.model_dump(), ensure_ascii=False, indent=2
        )
    )
    print("error:")
    print(
        json.dumps(result.error.model_dump(), ensure_ascii=False, indent=2)
        if result.error
        else "undefined"
    )
    print("\nmarkdown:")
    print(result.markdown)


if __name__ == "__main__":
    asyncio.run(main())
