from __future__ import annotations

import re

from .errors import failed_result
from .models import RequirementAnalysisResult

# Keep these keywords ASCII-first for stable matching in mixed CN/EN input,
# e.g. "给list加一个编号".
FRONTEND_STRONG_EN_KEYWORDS = {
    "ui",
    "ux",
    "page",
    "screen",
    "layout",
    "form",
    "button",
    "input",
    "search",
    "filter",
    "sort",
    "modal",
    "drawer",
    "toast",
    "frontend",
    "responsive",
    "dashboard",
    "component",
    "css",
}

FRONTEND_WEAK_EN_KEYWORDS = {
    "list",
    "table",
}

NON_FRONTEND_EN_KEYWORDS = {
    "database",
    "sql",
    "schema",
    "migration",
    "redis",
    "kafka",
    "rabbitmq",
    "grpc",
    "middleware",
    "backend",
    "server",
    "etl",
}

FRONTEND_CN_PATTERN = re.compile(
    r"(页面|列表|按钮|交互|样式|前端|组件|布局|弹窗|表单|输入|搜索|筛选|排序|响应式|仪表盘)"
)
NON_FRONTEND_CN_PATTERN = re.compile(
    r"(数据库|索引|中间件|后端|服务端|迁移脚本|消息队列|缓存集群)"
)


def _frontend_signal_score(text: str) -> int:
    lowered = text.lower()
    score = 0
    if any(token in lowered for token in FRONTEND_STRONG_EN_KEYWORDS):
        score += 2
    if any(token in lowered for token in FRONTEND_WEAK_EN_KEYWORDS):
        score += 1
    if FRONTEND_CN_PATTERN.search(text):
        score += 2
    return score


def _contains_non_frontend_signal(text: str) -> bool:
    lowered = text.lower()
    if any(token in lowered for token in NON_FRONTEND_EN_KEYWORDS):
        return True
    return bool(NON_FRONTEND_CN_PATTERN.search(text))


def validate_requirement_input(user_input: str) -> RequirementAnalysisResult | None:
    trimmed = user_input.strip()
    if len(trimmed) == 0:
        return failed_result("EMPTY_INPUT", "请输入前端需求描述")

    compact = "".join(trimmed.split())
    frontend_score = _frontend_signal_score(trimmed)
    is_frontend_requirement = frontend_score > 0
    has_non_frontend_signal = _contains_non_frontend_signal(trimmed)

    # Keep very short inputs blocked, but allow concise mixed-language frontend asks.
    if len(compact) < 6:
        return failed_result(
            "INPUT_TOO_SHORT", "需求描述过短，请补充目标、页面或交互信息"
        )
    if len(compact) < 10 and not is_frontend_requirement:
        return failed_result(
            "INPUT_TOO_SHORT", "需求描述过短，请补充目标、页面或交互信息"
        )

    if not is_frontend_requirement:
        return failed_result(
            "NOT_FRONTEND_REQUIREMENT", "当前需求不属于前端需求分析范围"
        )

    # Reject backend-leaning requests that only matched weak frontend words.
    if has_non_frontend_signal and frontend_score < 2:
        return failed_result(
            "NOT_FRONTEND_REQUIREMENT", "当前需求更偏后端实现，不属于前端需求分析范围"
        )

    return None
