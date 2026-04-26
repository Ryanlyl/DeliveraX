from __future__ import annotations

from .llm import ChatLLM
from .markdown_io import make_output_path, parse_markdown_sections, read_markdown, read_template, write_markdown
from .format_validator import format_validation_report, validate_technical_design
from .prompts import SYSTEM_PROMPT, architecture_prompt, design_prompt, format_repair_prompt, impact_prompt, review_prompt
from .repo_context import build_repo_context, prepare_repository as fetch_repository
from .schemas import SolutionDesignState


def load_requirement(state: SolutionDesignState) -> SolutionDesignState:
    markdown = read_markdown(state["requirement_path"])
    state["requirement_markdown"] = markdown
    state["requirement_sections"] = parse_markdown_sections(markdown)
    return state


def prepare_repository(state: SolutionDesignState) -> SolutionDesignState:
    repo_fetch = fetch_repository(
        repo_url=state.get("repo_url"),
        repo_path=state.get("repo_path"),
        repo_ref=state.get("repo_ref"),
        workspace_dir=state.get("workspace_dir"),
        task_id=state.get("task_id"),
    )
    state["repo_fetch"] = repo_fetch
    state["repo_root"] = repo_fetch["repo_root"]
    return state


def scan_repository(state: SolutionDesignState) -> SolutionDesignState:
    context = build_repo_context(
        state["repo_root"],
        state["requirement_markdown"],
        max_context_files=state.get("max_context_files", 24),
        repo_fetch=state.get("repo_fetch"),
    )
    if state.get("repo_fetch", {}).get("resolved_ref"):
        context["repo_ref"] = state["repo_fetch"].get("resolved_ref")
    state["repo_context"] = context
    return state


def analyze_architecture(state: SolutionDesignState) -> SolutionDesignState:
    if state.get("local_only"):
        state["architecture_summary"] = _local_architecture_summary(state)
        return state

    llm = ChatLLM()
    if not llm.available:
        state["architecture_summary"] = _local_architecture_summary(state)
        state.setdefault("errors", []).append("LLM not configured; used local architecture summary fallback.")
        return state

    state["architecture_summary"] = llm.complete(
        system=SYSTEM_PROMPT,
        user=architecture_prompt(state["requirement_markdown"], state["repo_context"]),
    )
    return state


def analyze_impact(state: SolutionDesignState) -> SolutionDesignState:
    if state.get("local_only"):
        state["impact_analysis"] = _local_impact_analysis(state)
        return state

    llm = ChatLLM()
    if not llm.available:
        state["impact_analysis"] = _local_impact_analysis(state)
        state.setdefault("errors", []).append("LLM not configured; used local impact analysis fallback.")
        return state

    state["impact_analysis"] = llm.complete(
        system=SYSTEM_PROMPT,
        user=impact_prompt(
            state["requirement_markdown"],
            state["repo_context"],
            state["architecture_summary"],
        ),
    )
    return state


def plan_design(state: SolutionDesignState) -> SolutionDesignState:
    template = read_template(state["template_path"])
    if state.get("local_only"):
        state["technical_design"] = _local_design_draft(state, template)
        return state

    llm = ChatLLM()
    if not llm.available:
        state["technical_design"] = _local_design_draft(state, template)
        state.setdefault("errors", []).append("LLM not configured; used local design draft fallback.")
        return state

    state["technical_design"] = llm.complete(
        system=SYSTEM_PROMPT,
        user=design_prompt(
            requirement_markdown=state["requirement_markdown"],
            repo_context=state["repo_context"],
            architecture_summary=state["architecture_summary"],
            impact_analysis=state["impact_analysis"],
            template=template,
        ),
    )
    return state


def validate_format(state: SolutionDesignState) -> SolutionDesignState:
    result = validate_technical_design(state["technical_design"], state["repo_context"])
    state["format_validation"] = result
    state["format_repaired"] = False
    if result.get("passed"):
        return state

    if state.get("local_only"):
        state.setdefault("errors", []).append("Format validation failed in local-only mode.")
        return state

    llm = ChatLLM()
    if not llm.available:
        state.setdefault("errors", []).append("Format validation failed and LLM is not configured for repair.")
        return state

    template = read_template(state["template_path"])
    repaired_design = llm.complete(
        system=SYSTEM_PROMPT,
        user=format_repair_prompt(
            template=template,
            technical_design=state["technical_design"],
            validation_report=format_validation_report(result),
            repo_context=state["repo_context"],
        ),
    )
    if repaired_design.strip():
        state["technical_design"] = repaired_design.strip()
        state["format_repaired"] = True
        repaired_result = validate_technical_design(state["technical_design"], state["repo_context"])
        state["format_validation"] = repaired_result
        if not repaired_result.get("passed"):
            state.setdefault("errors", []).append("Format repair ran once but validation still failed.")
    return state


def review_design(state: SolutionDesignState) -> SolutionDesignState:
    if state.get("local_only"):
        state["review_notes"] = _local_review_notes()
    else:
        llm = ChatLLM()
        if llm.available:
            state["review_notes"] = llm.complete(
                system=SYSTEM_PROMPT,
                user=review_prompt(state["requirement_markdown"], state["technical_design"]),
            )
        else:
            state["review_notes"] = _local_review_notes()

    validation = state.get("format_validation")
    validation_appendix = ""
    if validation and not validation.get("passed"):
        validation_appendix = "\n\n### 格式校验补充\n\n" + format_validation_report(validation)

    if "## 12. 一致性自检" not in state["technical_design"]:
        state["technical_design"] += "\n\n## 12. 一致性自检\n\n" + state["review_notes"].strip() + validation_appendix + "\n"
    elif state["review_notes"].strip() not in state["technical_design"]:
        state["technical_design"] += "\n\n---\n\n## Agent 自检补充\n\n" + state["review_notes"].strip() + validation_appendix + "\n"
    return state


def write_output(state: SolutionDesignState) -> SolutionDesignState:
    output_path = make_output_path(state["output_dir"], state["requirement_path"])
    write_markdown(output_path, state["technical_design"])
    state["output_path"] = str(output_path)
    return state


def _local_architecture_summary(state: SolutionDesignState) -> str:
    context = state["repo_context"]
    files = "\n".join(f"- `{item['path']}`" for item in context.get("key_files", []))
    return f"""## 本地启发式架构摘要

- 仓库：`{context.get('repo_name', '')}`
- 检测到的技术栈：`{context.get('detected_stack', {})}`
- 已选入上下文的关键文件：
{files}

本摘要由 `--local-only` 或无 LLM 配置时生成，只用于跑通流程。正式方案应使用 LLM 结合文件内容进一步分析。
"""


def _local_impact_analysis(state: SolutionDesignState) -> str:
    context = state["repo_context"]
    candidates = context.get("candidate_files", [])[:40]
    files = "\n".join(f"- `{path}`" for path in candidates)
    return f"""## 本地启发式影响范围

以下文件可能需要进一步人工或 LLM 检查：

{files}

待确认：
- 需求对应的具体页面入口。
- 是否已有 API 封装或状态管理模式可复用。
- 项目测试命令和测试目录位置。
"""


def _local_design_draft(state: SolutionDesignState, template: str) -> str:
    requirement_name = _infer_requirement_name(state)
    repo_name = state["repo_context"].get("repo_name", "")
    repo_ref = state["repo_context"].get("resolved_ref") or state.get("repo_ref") or "默认分支 / 本地路径"
    commit_sha = state["repo_context"].get("commit_sha") or "未记录"
    fetch_method = state["repo_context"].get("fetch_method") or "unknown"
    package_json_path = state["repo_context"].get("package_json_path") or "未找到"
    repo_root = state.get("repo_root", "")
    return f"""# 技术方案设计：{requirement_name}

> 本文档由 SolutionDesign Agent 本地启发式模式生成。由于未调用 LLM，内容只适合作为流程 smoke test 和方案占位稿。

---

## 0. 元信息

| 字段 | 内容 |
|---|---|
| 需求名称 | {requirement_name} |
| 目标仓库 | {repo_name} |
| 仓库 ref | {repo_ref} |
| 实际 commit SHA | {commit_sha} |
| 拉取方式 | {fetch_method} |
| package.json | {package_json_path} |
| 生成模式 | local-only |
| 方案状态 | Draft |

---

## 1. 需求理解

```markdown
{state['requirement_markdown'][:4000]}
```

---

## 2. 现有架构分析

{state['architecture_summary']}

---

## 3. 影响范围

{state['impact_analysis']}

---

## 4. 推荐技术方案

- 先确认需求对应的页面、组件和 API 数据流。
- 复用现有组件、样式、状态管理和请求封装。
- 将变更限制在影响范围内，避免无关重构。

---

## 5. 文件变更清单

| 文件路径 | 操作 | 变更说明 | 确定性 |
|---|---|---|---|
| 待 LLM 分析后补充 | TBD | 本地模式无法可靠确定具体文件 | Low |

---

## 6. API 设计

| API | 方法 | 入参 | 出参 | 说明 |
|---|---|---|---|---|
| 待确认 | TBD | TBD | TBD | 根据需求和代码库 API 封装进一步确认 |

---

## 7. 数据结构与状态设计

```ts
// Local-only mode cannot infer reliable project-specific types.
```

- 状态来源、类型定义和边界条件需要在 LLM 模式下结合目标文件补全。

---

## 8. 实施步骤

1. 阅读结构化需求与本方案。
2. 定位目标页面、组件、API 封装和状态管理文件。
3. 按文件变更清单实现，并避免修改无关文件。
4. 运行项目已有校验命令并回填测试结果。

---

## 9. 测试计划

- 运行项目已有类型检查、lint、单元测试和构建命令。
- 根据验收标准补充交互、异常、空状态和响应式检查。

---

## 10. 风险与待确认问题

- 目标页面/模块在代码库中的准确路径是什么？
- 是否需要新增后端接口，还是只消费已有接口？
- 项目当前推荐的测试命令是什么？

---

## 11. 给下一个实现 Agent 的执行指令

```yaml
implementation_contract:
  objective: "{requirement_name}"
  repo_root: "{repo_root}"
  must_read_files: []
  change_files: []
  api_changes: []
  state_changes: []
  test_commands: []
  acceptance_checks: []
  constraints:
    - "不要修改无关文件"
    - "优先复用现有项目模式"
    - "不确定事项先标注，不要编造"
```

---

## 12. 一致性自检

{_local_review_notes()}

<!-- Template reference retained for maintainers.

{template[:3000]}
-->
"""


def _local_review_notes() -> str:
    return """- 本地模式已生成基础结构，但没有进行深度语义审查。
- 正式使用时应配置 LLM，让 Agent 基于代码内容补全文件级方案、API 设计和测试计划。
"""


def _infer_requirement_name(state: SolutionDesignState) -> str:
    sections = state.get("requirement_sections", {})
    basic = sections.get("1. 基本信息") or sections.get("基本信息") or ""
    for line in basic.splitlines():
        if "需求名称" in line and "|" in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[1]:
                return cells[1]
    return "未命名需求"
