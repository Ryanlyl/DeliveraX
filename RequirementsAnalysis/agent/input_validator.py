from .errors import failed_result
from .models import RequirementAnalysisResult

FRONTEND_REQUIREMENT_KEYWORDS = [
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
]


def validate_requirement_input(
    user_input: str,
) -> RequirementAnalysisResult | None:
    trimmed = user_input.strip()
    if len(trimmed) == 0:
        return failed_result("EMPTY_INPUT", "请输入前端需求描述")

    compact = "".join(trimmed.split())
    if len(compact) < 10:
        return failed_result(
            "INPUT_TOO_SHORT", "需求描述过短，请补充目标、页面或交互信息"
        )

    is_frontend_requirement = any(
        keyword in trimmed for keyword in FRONTEND_REQUIREMENT_KEYWORDS
    )
    if not is_frontend_requirement:
        return failed_result(
            "NOT_FRONTEND_REQUIREMENT", "当前需求不属于前端需求分析范围"
        )

    return None
