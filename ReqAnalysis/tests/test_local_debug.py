from pathlib import Path

from requirement_analysis.local_debug import write_local_debug_artifacts
from requirement_analysis.models import (
    AnalysisMeta,
    BasicInfo,
    Background,
    Copywriting,
    Goals,
    ImpactScope,
    RequirementAnalysisError,
    RequirementAnalysisResult,
    RequirementBoundaryValidation,
    RequirementSpec,
    RiskItem,
    UiUx,
    AcceptanceCriteria,
)


def build_success_result() -> RequirementAnalysisResult:
    spec = RequirementSpec(
        basicInfo=BasicInfo(
            requirementName="任务列表页需求",
            requirementType="前端功能需求",
            priority="P1",
            owner="待确认",
            relatedPageOrModule="任务列表页",
            estimatedDeliveryTime="待确认",
            status="In Review",
        ),
        background=Background(
            context="用户需要查看任务并跟进完成情况。",
            currentProblems=["缺少清晰的任务查看能力"],
            targetUsers=["普通用户"],
            scenarios=["查看任务", "标记任务完成"],
            entryPoints=["任务入口"],
        ),
        goals=Goals(
            inScope=["查看任务列表", "标记任务完成"],
            outOfScope=["不包含任务创建", "不包含任务删除"],
        ),
        impactScope=ImpactScope(
            pagesOrModules=["任务列表页"],
            userRoles=["普通用户"],
            businessFlows=["查看任务", "完成任务"],
            dataOrApiScenarios=["任务数据读取", "任务状态更新"],
        ),
        uiux=UiUx(
            pageStructure=["清晰呈现任务列表"],
            visualRequirements=["任务状态需要明确区分"],
            responsiveRequirements=["移动端需要可读且易操作"],
            interactionRequirements=["操作后需要有明确反馈"],
        ),
        acceptanceCriteria=AcceptanceCriteria(
            checklist=["用户可以看到任务列表", "用户可以标记任务完成"],
            gherkinScenarios=["Feature: 任务列表"],
        ),
        performanceRequirements=["页面内容应及时展示"],
        compatibilityRequirements=["支持主流桌面和移动端浏览器"],
        copywriting=Copywriting(
            normalCopy=["任务"], errorCopy=["任务加载失败，请稍后重试"]
        ),
        risks=[
            RiskItem(
                risk="完成状态不清晰",
                impact="用户可能重复操作",
                mitigation="验收时确认状态表达清晰",
            )
        ],
        definitionOfDone=["需求文档已生成"],
        openQuestions=["是否允许撤销完成状态？"],
    )
    return RequirementAnalysisResult(
        spec=spec,
        markdown="# Frontend Feature PRD",
        status="In Review",
        validation=RequirementBoundaryValidation(valid=True, errors=[]),
        error=None,
        meta=AnalysisMeta(
            promptVersion="v1", attempts=1, model="mock", latencyMs=10
        ),
    )


def test_write_local_debug_artifacts_success(tmp_path: Path) -> None:
    artifacts = write_local_debug_artifacts(
        output_dir=tmp_path,
        user_input="会议纪要原文",
        result=build_success_result(),
        run_id="test_run",
    )

    assert artifacts.run_dir.exists()
    assert artifacts.input_path.exists()
    assert artifacts.spec_path is not None and artifacts.spec_path.exists()
    assert (
        artifacts.markdown_path is not None
        and artifacts.markdown_path.exists()
    )
    assert artifacts.report_path.exists()
    assert artifacts.input_path.read_text(encoding="utf-8") == "会议纪要原文"


def test_write_local_debug_artifacts_failed_result(tmp_path: Path) -> None:
    failed_result = RequirementAnalysisResult(
        spec=None,
        markdown=None,
        status="Failed",
        validation=RequirementBoundaryValidation(valid=False, errors=[]),
        error=RequirementAnalysisError(
            code="EMPTY_INPUT", message="请输入前端需求描述"
        ),
    )
    artifacts = write_local_debug_artifacts(
        output_dir=tmp_path,
        user_input="",
        result=failed_result,
        run_id="failed_run",
    )

    assert artifacts.spec_path is None
    assert artifacts.markdown_path is None
    assert artifacts.report_path.exists()
