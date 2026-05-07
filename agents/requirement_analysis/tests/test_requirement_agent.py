import asyncio
import json

from requirement_analysis.boundary_validator import validate_requirement_boundary
from requirement_analysis.markdown_renderer import render_requirement_markdown
from requirement_analysis.models import RequirementAnalysisInput, RequirementSpec
from requirement_analysis.runner import run_requirement_analysis


def create_valid_spec(overrides: dict | None = None) -> dict:
    spec = {
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
    if overrides:
        spec.update(overrides)
    return spec


def test_successful_input_generates_markdown() -> None:
    spec = create_valid_spec()

    async def llm_call(_: str) -> str:
        return json.dumps(spec, ensure_ascii=False)

    result = asyncio.run(
        run_requirement_analysis(
            RequirementAnalysisInput(userInput="我想做一个任务列表页。"),
            llm_call=llm_call,
        )
    )
    assert result.validation.valid is True
    assert result.status == "In Review"
    assert result.error is None
    assert result.markdown is not None
    assert "# Frontend Feature PRD" in result.markdown


def test_empty_input_returns_error() -> None:
    async def llm_call(_: str) -> str:
        return "{}"

    result = asyncio.run(
        run_requirement_analysis(
            RequirementAnalysisInput(userInput="   "), llm_call=llm_call
        )
    )
    assert result.status == "Failed"
    assert result.error is not None
    assert result.error.code == "EMPTY_INPUT"


def test_boundary_violation_in_user_input() -> None:
    async def llm_call(_: str) -> str:
        return "{}"

    result = asyncio.run(
        run_requirement_analysis(
            RequirementAnalysisInput(
                userInput="做一个页面，用 React 写，调用接口获取数据，用useState管理状态"
            ),
            llm_call=llm_call,
        )
    )
    assert result.status == "Failed"
    assert result.error is not None
    assert result.error.code == "INPUT_BOUNDARY_VIOLATION"
    assert any(
        error.category == "framework" and error.keyword == "React"
        for error in result.validation.errors
    )


def test_invalid_json_repair_success() -> None:
    spec = create_valid_spec()
    calls = {"count": 0}

    async def llm_call(_: str) -> str:
        calls["count"] += 1
        return (
            "not json"
            if calls["count"] == 1
            else json.dumps(spec, ensure_ascii=False)
        )

    result = asyncio.run(
        run_requirement_analysis(
            RequirementAnalysisInput(userInput="我想做一个任务列表页。"),
            llm_call=llm_call,
        )
    )
    assert calls["count"] == 2
    assert result.status == "In Review"
    assert result.validation.valid is True


def test_all_attempts_fail_returns_auto_fix_failed() -> None:
    invalid_spec = create_valid_spec({"goals": {"outOfScope": ["待确认"]}})

    async def llm_call(_: str) -> str:
        return json.dumps(invalid_spec, ensure_ascii=False)

    result = asyncio.run(
        run_requirement_analysis(
            RequirementAnalysisInput(userInput="我想做一个任务列表页。"),
            llm_call=llm_call,
        )
    )
    assert result.status == "Failed"
    assert result.error is not None
    assert result.error.code == "AUTO_FIX_FAILED"


def test_boundary_validator_classification() -> None:
    invalid_spec = create_valid_spec(
        {
            "goals": {
                "inScope": [
                    "使用 React 实现任务列表",
                    "通过 useState 管理完成状态",
                    "补充 API 路径说明",
                    "使用复选框完成标记",
                ],
                "outOfScope": ["待确认"],
            }
        }
    )
    validation = validate_requirement_boundary(
        RequirementSpec.model_validate(invalid_spec)
    )
    assert validation.valid is False
    assert any(error.category == "framework" for error in validation.errors)
    assert any(error.category == "state" for error in validation.errors)
    assert any(error.category == "api_design" for error in validation.errors)


def test_markdown_renderer_default_sections() -> None:
    spec = create_valid_spec({"definitionOfDone": [], "openQuestions": []})
    markdown = render_requirement_markdown(
        RequirementSpec.model_validate(spec)
    )
    assert "# Frontend Feature PRD Template" in markdown
    assert "## 1. 基本信息" in markdown
    assert "| 当前状态 | In Review |" in markdown
    assert "## 6. 验收标准" in markdown
    assert "## 4. 需求影响范围说明" not in markdown


def test_mixed_language_short_frontend_input_is_accepted() -> None:
    spec = create_valid_spec()

    async def llm_call(_: str) -> str:
        return json.dumps(spec, ensure_ascii=False)

    result = asyncio.run(
        run_requirement_analysis(
            RequirementAnalysisInput(userInput="\u7ed9list\u52a0\u4e00\u4e2a\u7f16\u53f7"),
            llm_call=llm_call,
        )
    )
    assert result.status == "In Review"
    assert result.error is None


def test_non_frontend_input_is_rejected() -> None:
    async def llm_call(_: str) -> str:
        return "{}"

    result = asyncio.run(
        run_requirement_analysis(
            RequirementAnalysisInput(
                userInput="Add a database migration for users table and optimize SQL indexes."
            ),
            llm_call=llm_call,
        )
    )
    assert result.status == "Failed"
    assert result.error is not None
    assert result.error.code == "NOT_FRONTEND_REQUIREMENT"
