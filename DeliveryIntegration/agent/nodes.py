from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .format_validator import validate_delivery_documents
from .io_utils import (
    make_output_paths,
    read_json,
    resolve_relative_path,
    write_json,
    write_text,
)
from .llm import ChatLLM
from .prompts import SYSTEM_PROMPT, delivery_summary_prompt
from .schemas import DeliveryIntegrationState
from .upstream_results import (
    assert_review_approved,
    assert_test_passed,
    load_review_result,
    load_test_result,
)
from .workspace import (
    apply_diff,
    assert_safe_changed_files,
    build_diff_stat,
    build_final_diff,
    commit_integrated_changes,
    git_head,
    git_status,
    list_changed_files,
    prepare_integration_repository,
    safe_name,
)


def load_prevalidated_changes(state: DeliveryIntegrationState) -> DeliveryIntegrationState:
    state.setdefault("warnings", [])
    state.setdefault("errors", [])

    changeset = _load_changeset(state.get("changeset_path"))
    state["changeset"] = changeset

    codegen_result_path = _resolve_codegen_result_path(
        state.get("codegen_result_path"),
        changeset,
        state.get("changeset_path"),
    )
    if not codegen_result_path:
        raise RuntimeError("No CodeGen result was provided. Use --codegen-result or changeset.codegen_result_path.")

    codegen_result = read_json(codegen_result_path)
    state["codegen_result_path"] = codegen_result_path
    state["codegen_result"] = codegen_result

    codegen_dir = Path(codegen_result_path).resolve().parent
    source_repo_root = codegen_result.get("source_repo_root")
    source_base = codegen_dir
    if not source_repo_root:
        source_repo_root = changeset.get("repo", {}).get("source_repo_root") or changeset.get("source_repo_root")
        source_base = Path(state["changeset_path"]).resolve().parent if state.get("changeset_path") else Path.cwd()

    diff_path = codegen_result.get("diff_path")
    diff_base = codegen_dir
    if not diff_path:
        diff_path = changeset.get("changes", {}).get("diff_path") or changeset.get("diff_path")
        diff_base = Path(state["changeset_path"]).resolve().parent if state.get("changeset_path") else Path.cwd()
    if not source_repo_root:
        raise RuntimeError("CodeGen result does not contain source_repo_root.")
    if not diff_path:
        raise RuntimeError("CodeGen result does not contain diff_path.")

    state["source_repo_root"] = resolve_relative_path(str(source_repo_root), source_base) or ""
    state["diff_path"] = resolve_relative_path(str(diff_path), diff_base) or ""
    state["source_commit_sha"] = codegen_result.get("source_commit_sha") or codegen_result.get("expected_commit_sha")
    state["changed_files"] = _changed_files_from_codegen(codegen_result, changeset)
    if not state.get("task_id"):
        state["task_id"] = safe_name(f"delivery-{codegen_result.get('task_id') or 'task'}")
    return state


def verify_test_and_review_results(state: DeliveryIntegrationState) -> DeliveryIntegrationState:
    changeset = state.get("changeset", {})
    test_result_path = state.get("test_result_path") or changeset.get("test", {}).get("result_path")
    review_result_path = state.get("review_result_path") or changeset.get("review", {}).get("result_path")
    changeset_base = Path(state["changeset_path"]).resolve().parent if state.get("changeset_path") else Path.cwd()

    test = load_test_result(
        result_path=resolve_relative_path(test_result_path, changeset_base),
        explicit_status=state.get("test_status") or changeset.get("test", {}).get("status"),
    )
    review = load_review_result(
        result_path=resolve_relative_path(review_result_path, changeset_base),
        explicit_status=state.get("review_status") or changeset.get("review", {}).get("status"),
    )
    assert_test_passed(test)
    assert_review_approved(review)
    state["test"] = test
    state["review"] = review
    if test.get("source") == "assumed":
        state.setdefault("warnings", []).append("未提供代码测试结果文件或状态，本阶段按契约假定测试已通过。")
    if review.get("source") == "assumed":
        state.setdefault("warnings", []).append("未提供代码评审结果文件或状态，本阶段按契约假定评审已通过。")
    return state


def resolve_solution_workspace_repo(state: DeliveryIntegrationState) -> DeliveryIntegrationState:
    source = Path(state["source_repo_root"]).resolve()
    if not source.exists():
        raise RuntimeError(f"SolutionDesign workspace repository does not exist: {source}")
    state["source_repo_root"] = str(source)
    state["source_head_sha"] = git_head(source)
    state["source_git_status"] = git_status(source)
    return state


def create_integration_worktree(state: DeliveryIntegrationState) -> DeliveryIntegrationState:
    prepared = prepare_integration_repository(
        source_repo_root=state["source_repo_root"],
        source_commit_sha=state.get("source_commit_sha"),
        workspace_dir=state["workspace_dir"],
        task_id=state["task_id"] or "task",
        integration_branch=state.get("integration_branch"),
        force=bool(state.get("force")),
        allow_source_head_drift=bool(state.get("allow_source_head_drift")),
    )
    state["task_workspace_dir"] = str(prepared["task_workspace_dir"])
    state["integration_repo_path"] = str(prepared["integration_repo_path"])
    state["integration_branch_name"] = str(prepared["integration_branch_name"])
    state["task_base_commit_sha"] = prepared.get("task_base_commit_sha")
    state["source_head_sha"] = prepared.get("source_head_sha") or state.get("source_head_sha")
    return state


def apply_reviewed_diff(state: DeliveryIntegrationState) -> DeliveryIntegrationState:
    result = apply_diff(repo_root=state["integration_repo_path"], diff_path=state["diff_path"])
    state["applied_diff"] = result  # type: ignore[assignment]
    if not result.get("check_passed"):
        raise RuntimeError(f"Reviewed diff failed git apply --check:\n{result.get('check_output', '')}")
    if not result.get("applied"):
        raise RuntimeError(f"Reviewed diff failed git apply --3way:\n{result.get('apply_output', '')}")
    return state


def verify_integrated_diff(state: DeliveryIntegrationState) -> DeliveryIntegrationState:
    repo = state["integration_repo_path"]
    base = state.get("task_base_commit_sha")
    planned_files = state.get("changed_files", [])
    assert_safe_changed_files(repo, planned_files)

    committed = False
    if state.get("create_commit", True):
        head = commit_integrated_changes(repo, f"Integrate reviewed changes for {state.get('task_id', 'delivery task')}")
        state["head_commit_sha"] = head
        committed = True
    else:
        state["head_commit_sha"] = git_head(repo)
    state["committed"] = committed

    final_diff = build_final_diff(repo, base, committed=committed)
    final_files = list_changed_files(repo, base, committed=committed)
    assert_safe_changed_files(repo, final_files)
    if not final_diff.strip():
        raise RuntimeError("Integrated diff is empty after applying reviewed changes.")

    state["final_diff"] = final_diff
    state["final_diff_stat"] = build_diff_stat(repo, base, committed=committed)
    state["integrated_files"] = final_files
    state["merge_ready"] = True
    return state


def generate_delivery_summary(state: DeliveryIntegrationState) -> DeliveryIntegrationState:
    final_diff_path, summary_path, pr_body_path, result_json_path = make_output_paths(
        state["output_dir"], state["task_id"] or "task"
    )
    write_text(final_diff_path, state["final_diff"])
    summary_text, pr_body_text, summary_mode, summary_model = _generate_summary_documents(
        state,
        final_diff_path=final_diff_path,
        summary_path=summary_path,
        pr_body_path=pr_body_path,
    )
    format_errors = validate_delivery_documents(summary_text, pr_body_text)
    if format_errors:
        raise RuntimeError("交付输出格式检查失败：" + "；".join(format_errors))
    write_text(summary_path, summary_text)
    write_text(pr_body_path, pr_body_text)
    state["final_diff_path"] = str(final_diff_path)
    state["summary_path"] = str(summary_path)
    state["pr_body_path"] = str(pr_body_path)
    state["result_json_path"] = str(result_json_path)
    state["summary_mode"] = summary_mode
    state["summary_model"] = summary_model
    state["summary_format_errors"] = format_errors
    return state


def package_merge_ready_output(state: DeliveryIntegrationState) -> DeliveryIntegrationState:
    write_json(Path(state["result_json_path"]), _build_result_json(state))
    return state


def _load_changeset(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return read_json(Path(path).resolve())


def _resolve_codegen_result_path(
    configured: str | None,
    changeset: dict[str, Any],
    changeset_path: str | None,
) -> str | None:
    if configured:
        return str(Path(configured).resolve())
    raw = changeset.get("codegen_result_path")
    if not raw:
        return None
    base = Path(changeset_path).resolve().parent if changeset_path else Path.cwd()
    return resolve_relative_path(str(raw), base)


def _changed_files_from_codegen(codegen_result: dict[str, Any], changeset: dict[str, Any]) -> list[str]:
    files: list[str] = []
    for item in codegen_result.get("changed_files", []):
        if isinstance(item, dict) and item.get("path"):
            files.append(str(item["path"]).replace("\\", "/").lstrip("/"))
        elif isinstance(item, str):
            files.append(item.replace("\\", "/").lstrip("/"))
    for item in changeset.get("changes", {}).get("changed_files", []):
        if isinstance(item, str):
            normalized = item.replace("\\", "/").lstrip("/")
            if normalized not in files:
                files.append(normalized)
    return files


def _build_summary(state: DeliveryIntegrationState, final_diff_path: Path, pr_body_path: Path) -> str:
    files = state.get("integrated_files", [])
    lines = [
        "# 交付集成摘要",
        "",
        "## 概览",
        "",
        f"- 任务 ID：`{state.get('task_id', '')}`",
        f"- 源 workspace 仓库：`{state.get('source_repo_root', '')}`",
        f"- 集成仓库：`{state.get('integration_repo_path', '')}`",
        f"- 集成分支：`{state.get('integration_branch_name', '')}`",
        f"- 基线 commit：`{state.get('task_base_commit_sha') or ''}`",
        f"- 当前 commit：`{state.get('head_commit_sha') or ''}`",
        f"- 可合并状态：`{state.get('merge_ready', False)}`",
        "",
        "## 上游结果",
        "",
        "| 阶段 | 状态 | 来源 | 说明 |",
        "| --- | --- | --- | --- |",
        f"| 代码测试 | {state.get('test', {}).get('status', '')} | {state.get('test', {}).get('source', '')} | {_table_cell(state.get('test', {}).get('detail', ''))} |",
        f"| 代码评审 | {state.get('review', {}).get('status', '')} | {state.get('review', {}).get('source', '')} | {_table_cell(state.get('review', {}).get('detail', ''))} |",
        "",
        "## 集成文件",
        "",
    ]
    if files:
        lines.extend(f"- `{path}`" for path in files)
    else:
        lines.append("- 未检测到文件变更。")
    lines.extend(
        [
            "",
            "## Diff 统计",
            "",
            "```text",
            state.get("final_diff_stat", "").strip() or "没有可用的 diff 统计。",
            "```",
            "",
            "## 输出产物",
            "",
            f"- 最终 diff：`{final_diff_path}`",
            f"- PR 描述：`{pr_body_path}`",
        ]
    )
    warnings = state.get("warnings", [])
    if warnings:
        lines.extend(["", "## 警告", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines).rstrip() + "\n"


def _build_pr_body(state: DeliveryIntegrationState, final_diff_path: Path, summary_path: Path) -> str:
    files = state.get("integrated_files", [])
    lines = [
        "## 变更摘要",
        "",
        f"已完成 `{state.get('task_id', '')}` 的交付集成，变更来自已通过测试和评审的 CodeGen diff。",
        "",
        "## 上游验证",
        "",
        f"- 代码测试：`{state.get('test', {}).get('status', '')}`（{state.get('test', {}).get('source', '')}）",
        f"- 代码评审：`{state.get('review', {}).get('status', '')}`（{state.get('review', {}).get('source', '')}）",
        "",
        "## 变更文件",
        "",
    ]
    if files:
        lines.extend(f"- `{path}`" for path in files)
    else:
        lines.append("- 未检测到文件变更。")
    lines.extend(
        [
            "",
            "## 集成元数据",
            "",
            f"- 源 workspace 仓库：`{state.get('source_repo_root', '')}`",
            f"- 集成分支：`{state.get('integration_branch_name', '')}`",
            f"- 基线 commit：`{state.get('task_base_commit_sha') or ''}`",
            f"- 当前 commit：`{state.get('head_commit_sha') or ''}`",
            f"- 最终 diff：`{final_diff_path}`",
            f"- 交付摘要：`{summary_path}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _generate_summary_documents(
    state: DeliveryIntegrationState,
    *,
    final_diff_path: Path,
    summary_path: Path,
    pr_body_path: Path,
) -> tuple[str, str, str, str | None]:
    fallback_summary = _build_summary(state, final_diff_path, pr_body_path)
    fallback_pr_body = _build_pr_body(state, final_diff_path, summary_path)
    _assert_valid_delivery_documents(fallback_summary, fallback_pr_body)
    if not state.get("use_llm", True):
        return fallback_summary, fallback_pr_body, "template", None

    llm = ChatLLM()
    if not llm.available:
        if state.get("require_llm"):
            raise RuntimeError(
                "已要求使用 LLM 生成交付摘要，但 LLM 配置不完整。"
                "请设置 DELIVERY_INTEGRATION_LLM_API_KEY 和 DELIVERY_INTEGRATION_LLM_MODEL。"
                "使用非默认 OpenAI-compatible 服务时还需要设置 DELIVERY_INTEGRATION_LLM_BASE_URL。"
            )
        state.setdefault("warnings", []).append(
            "未配置 LLM，交付摘要和 PR 描述已使用中文模板生成。"
        )
        return fallback_summary, fallback_pr_body, "template_no_llm_config", None

    try:
        raw = llm.complete(
            system=SYSTEM_PROMPT,
            user=delivery_summary_prompt(
                facts=_summary_facts(state, final_diff_path, summary_path, pr_body_path),
                final_diff=state.get("final_diff", ""),
                max_diff_chars=state.get("summary_max_diff_chars", 24000),
            ),
        )
        parsed = _parse_llm_summary_json(raw)
        summary = str(parsed.get("summary_markdown") or "").strip()
        pr_body = str(parsed.get("pr_body_markdown") or "").strip()
        if not summary or not pr_body:
            raise ValueError("LLM 输出必须包含 summary_markdown 和 pr_body_markdown。")
        _assert_valid_delivery_documents(summary, pr_body)
        return summary + "\n", pr_body + "\n", "llm", llm.config.model
    except Exception as exc:
        if state.get("require_llm"):
            raise RuntimeError(f"已要求使用 LLM 生成交付摘要，但生成失败：{exc}") from exc
        state.setdefault("warnings", []).append(f"LLM 摘要生成失败，已回退到中文模板：{exc}")
        return fallback_summary, fallback_pr_body, "template_llm_failed", llm.config.model


def _assert_valid_delivery_documents(summary_markdown: str, pr_body_markdown: str) -> None:
    errors = validate_delivery_documents(summary_markdown, pr_body_markdown)
    if errors:
        raise ValueError("交付输出格式检查失败：" + "；".join(errors))


def _summary_facts(
    state: DeliveryIntegrationState,
    final_diff_path: Path,
    summary_path: Path,
    pr_body_path: Path,
) -> dict[str, Any]:
    return {
        "task_id": state.get("task_id"),
        "source_repo_root": state.get("source_repo_root"),
        "integration_repo_path": state.get("integration_repo_path"),
        "integration_branch": state.get("integration_branch_name"),
        "base_commit": state.get("task_base_commit_sha"),
        "head_commit": state.get("head_commit_sha"),
        "merge_ready": state.get("merge_ready", False),
        "test_result": state.get("test", {}),
        "review_result": state.get("review", {}),
        "changed_files": state.get("integrated_files", []),
        "planned_changed_files": state.get("changed_files", []),
        "diff_stat": state.get("final_diff_stat", ""),
        "final_diff_path": str(final_diff_path),
        "summary_path": str(summary_path),
        "pr_body_path": str(pr_body_path),
        "warnings": state.get("warnings", []),
    }


def _parse_llm_summary_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _build_result_json(state: DeliveryIntegrationState) -> dict[str, Any]:
    return {
        "task_id": state.get("task_id"),
        "codegen_result_path": state.get("codegen_result_path"),
        "source_repo_root": state.get("source_repo_root"),
        "source_commit_sha": state.get("source_commit_sha"),
        "source_head_sha": state.get("source_head_sha"),
        "source_git_status": state.get("source_git_status"),
        "integration_repo_path": state.get("integration_repo_path"),
        "task_workspace_dir": state.get("task_workspace_dir"),
        "integration_branch": state.get("integration_branch_name"),
        "base_commit": state.get("task_base_commit_sha"),
        "head_commit": state.get("head_commit_sha"),
        "committed": state.get("committed", False),
        "pushed": False,
        "test_status": state.get("test", {}).get("status"),
        "test_result": state.get("test", {}),
        "review_status": state.get("review", {}).get("status"),
        "review_result": state.get("review", {}),
        "merge_ready": state.get("merge_ready", False),
        "diff_path": state.get("diff_path"),
        "final_diff_path": state.get("final_diff_path"),
        "summary_path": state.get("summary_path"),
        "pr_body_path": state.get("pr_body_path"),
        "result_json_path": state.get("result_json_path"),
        "summary_mode": state.get("summary_mode"),
        "summary_model": state.get("summary_model"),
        "summary_format_errors": state.get("summary_format_errors", []),
        "changed_files": state.get("integrated_files", []),
        "planned_changed_files": state.get("changed_files", []),
        "warnings": state.get("warnings", []),
        "errors": state.get("errors", []),
    }


def _table_cell(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
