from .models import RequirementSpec

EMPTY_VALUE = "待确认"


def _text(value: object) -> str:
    if not isinstance(value, str):
        return EMPTY_VALUE
    trimmed = value.strip()
    return trimmed if trimmed else EMPTY_VALUE


def _list(values: list[str] | None) -> str:
    if not values:
        return f"- {EMPTY_VALUE}"
    return "\n".join(f"- {_text(value)}" for value in values)


def _numbered_list(values: list[str] | None) -> str:
    if not values:
        return f"1. {EMPTY_VALUE}"
    return "\n".join(
        f"{idx}. {_text(value)}" for idx, value in enumerate(values, start=1)
    )


def _checklist(values: list[str] | None) -> str:
    if not values:
        return f"- [ ] {EMPTY_VALUE}"
    return "\n".join(f"- [ ] {_text(value)}" for value in values)


def _table(rows: list[tuple[str, object]]) -> str:
    lines = ["| 字段 | 内容 |", "| --- | --- |"]
    lines.extend(f"| {key} | {_text(value)} |" for key, value in rows)
    return "\n".join(lines)


def render_requirement_markdown(spec: RequirementSpec) -> str:
    basic_info_table = _table(
        [
            ("需求名称", spec.basicInfo.requirementName),
            ("需求类型", spec.basicInfo.requirementType),
            ("优先级", spec.basicInfo.priority),
            ("负责人", spec.basicInfo.owner),
            ("相关页面 / 模块", spec.basicInfo.relatedPageOrModule),
            ("预计交付时间", spec.basicInfo.estimatedDeliveryTime),
            ("当前状态", spec.basicInfo.status),
        ]
    )
    background_context = _text(spec.background.context)
    background_problems = _list(spec.background.currentProblems)
    target_user = _text(
        spec.background.targetUsers[0] if spec.background.targetUsers else None
    )
    user_scenario = _text(
        spec.background.scenarios[0] if spec.background.scenarios else None
    )
    entry_point = _text(
        spec.background.entryPoints[0] if spec.background.entryPoints else None
    )
    acceptance_criteria = _checklist(spec.acceptanceCriteria.checklist)

    return f"""# Frontend Feature PRD Template

> 示例输入，用于测试 SolDesign。真实项目中请替换为上一步生成的结构化需求 Markdown。

---

## 1. 基本信息

{basic_info_table}

---

## 2. 背景与问题说明

### 2.1 背景
{background_context}

### 2.2 当前问题
{background_problems}

### 2.3 目标用户
- 主要用户：{target_user}
- 使用场景：{user_scenario}
- 触发入口：{entry_point}

---

## 3. 需求目标

### 3.1 本次要实现什么
{_numbered_list(spec.goals.inScope)}

### 3.2 本次不做什么
{_numbered_list(spec.goals.outOfScope)}

---

## 6. 验收标准

{acceptance_criteria}
"""
