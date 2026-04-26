from __future__ import annotations

from .repo_context import format_repo_context_for_prompt
from .schemas import RepoContext


SYSTEM_PROMPT = """你是 DeliveraX 的方案设计 Agent。

你的任务是把结构化前端需求文档和真实代码库上下文结合，输出可执行的技术方案。

要求：
- 必须基于给定代码库上下文，不要编造不存在的文件路径。
- 如果上下文不足，要明确写入“待确认问题”，不要假装确定。
- 输出应同时服务人类 reviewer 和下一阶段代码实现 Agent，但优先保证实现 Agent 可执行。
- 技术方案必须是 Markdown。
- 文件变更清单、API 设计、状态/数据设计、测试计划必须结构化。
- 不要直接写代码实现，除非是为了说明接口形状或类型草案。
"""


def architecture_prompt(requirement_markdown: str, repo_context: RepoContext) -> str:
    return f"""请分析这个前端仓库的现有架构，并说明它和需求可能相关的部分。

## 结构化需求

```markdown
{requirement_markdown}
```

## 代码库上下文

{format_repo_context_for_prompt(repo_context)}

请输出：
1. 技术栈与项目结构
2. 关键入口、页面、组件、状态、API 封装位置
3. 与需求相似或相关的已有实现
4. 对后续影响范围分析有帮助的观察
"""


def impact_prompt(requirement_markdown: str, repo_context: RepoContext, architecture_summary: str) -> str:
    return f"""请基于需求、代码库上下文和架构分析，判断本次需求的影响范围。

## 结构化需求

```markdown
{requirement_markdown}
```

## 架构分析

```markdown
{architecture_summary}
```

## 代码库上下文

{format_repo_context_for_prompt(repo_context)}

请输出：
1. 可能需要新增/修改/删除的文件清单
2. 涉及的页面、组件、状态、API、路由、样式、测试
3. 对现有行为的潜在影响
4. 明确的不确定点和需要人工确认的问题
"""


def design_prompt(
    *,
    requirement_markdown: str,
    repo_context: RepoContext,
    architecture_summary: str,
    impact_analysis: str,
    template: str,
) -> str:
    return f"""请根据模板生成完整技术方案设计文档。

## 输出模板

```markdown
{template}
```

## 结构化需求

```markdown
{requirement_markdown}
```

## 架构分析

```markdown
{architecture_summary}
```

## 影响范围分析

```markdown
{impact_analysis}
```

## 代码库上下文

{format_repo_context_for_prompt(repo_context)}

请直接输出最终 Markdown 文档，不要包裹在代码块里。
"""


def review_prompt(requirement_markdown: str, technical_design: str) -> str:
    return f"""请审查下面的技术方案是否满足结构化需求，并补充一致性自检结果。

## 结构化需求

```markdown
{requirement_markdown}
```

## 技术方案

```markdown
{technical_design}
```

请输出简短审查结论，包含：
- 是否覆盖需求目标
- 是否有遗漏的验收标准
- 是否有不明确或不可执行的文件/API/测试描述
- 建议写入技术方案的待确认问题
"""


def format_repair_prompt(
    *,
    template: str,
    technical_design: str,
    validation_report: str,
    repo_context: RepoContext,
) -> str:
    candidate_files = "\n".join(f"- `{path}`" for path in repo_context.get("candidate_files", [])[:300])
    return f"""请修复下面技术方案文档的格式问题，并只输出修复后的完整 Markdown 文档。

修复要求：
- 必须严格包含模板中的所有一级/二级标题。
- `## 5. 文件变更清单` 必须包含 Markdown 表格。
- `## 6. API 设计` 必须存在且保留 API 变更说明；如果无 API 变更，也要明确写“无 API 变更”。
- `## 11. 给下一个实现 Agent 的执行指令` 必须包含 fenced YAML block，且其中必须有 `implementation_contract:`。
- 文件变更清单中，`Modify / Update / Delete / 修改 / 删除` 类型的路径必须来自仓库文件列表。
- 如果路径不在仓库文件列表里，但确实需要新增，请把操作标为 `Add`；如果不确定，请移入“待确认问题”。
- 尽量保留原方案的有效技术内容，不要新增无依据的代码路径。
- 不要把输出包裹在额外代码块里。

## 输出模板

```markdown
{template}
```

## 格式校验报告

{validation_report}

## 仓库已扫描文件列表

{candidate_files}

## 待修复技术方案

```markdown
{technical_design}
```
"""
