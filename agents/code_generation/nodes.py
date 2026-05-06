from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .design_parser import parse_technical_design
from .diff_utils import build_git_diff, has_git_diff
from .llm import ChatLLM
from .markdown_io import make_output_paths, read_markdown, write_text
from .prompts import SYSTEM_PROMPT, code_generation_prompt
from .repo_context import (
    build_repo_context,
    git_status,
    normalize_contract_paths,
    resolve_repo_root,
    safe_repo_path,
)
from .schemas import CodeGenState, GeneratedFileChange, SmokeCheck
from .task_workspace import prepare_task_repository


def load_design(state: CodeGenState) -> CodeGenState:
    markdown = read_markdown(state["design_path"])
    contract, metadata, warnings = parse_technical_design(markdown)
    if not contract.get("change_files"):
        message = "No change_files were found in the technical design."
        if state.get("local_only"):
            state.setdefault("warnings", []).append(message + " local-only mode allows empty change_files.")
        else:
            state.setdefault("errors", []).append(message)
    state["design_markdown"] = markdown
    state["implementation_contract"] = contract
    state["design_metadata"] = metadata
    state["parser_warnings"] = warnings
    state.setdefault("warnings", []).extend(warnings)
    return state


def resolve_workspace(state: CodeGenState) -> CodeGenState:
    source_repo_root = resolve_repo_root(
        contract_repo_root=state.get("implementation_contract", {}).get("repo_root"),
        workspace_dir=state.get("workspace_dir"),
        repo_path=state.get("repo_path"),
        task_id=state.get("task_id"),
    )
    state["source_repo_root"] = str(source_repo_root)
    source_status = git_status(source_repo_root)
    state["source_git_status"] = source_status
    if source_status:
        state.setdefault("warnings", []).append(
            f"Source cache repository has pre-existing changes: {_inline_status(source_status)}"
        )
    state["implementation_contract"] = normalize_contract_paths(state["implementation_contract"], source_repo_root)
    workspace = prepare_task_repository(
        source_repo_root=source_repo_root,
        design_metadata=state.get("design_metadata", {}),
        task_id=state["task_id"] or "task",
    )
    state["repo_root"] = str(workspace["task_repo_root"])
    state["repo_name"] = source_repo_root.name
    state["task_workspace_dir"] = str(Path(state["repo_root"]).parent)
    state["source_commit_sha"] = workspace.get("source_commit_sha")
    state["expected_commit_sha"] = workspace.get("expected_commit_sha")
    state["task_base_commit_sha"] = workspace.get("task_base_commit_sha")
    state["worktree_method"] = str(workspace.get("worktree_method") or "")
    return state


def load_file_context(state: CodeGenState) -> CodeGenState:
    context = build_repo_context(
        repo_root=state["repo_root"],
        contract=state["implementation_contract"],
        max_context_files=state.get("max_context_files", 32),
        max_file_chars=state.get("max_file_chars", 24000),
    )
    state["repo_context"] = context
    if context.get("git_status"):
        state.setdefault("warnings", []).append(f"Initial git status: {context['git_status']}")
    return state


def generate_changes(state: CodeGenState) -> CodeGenState:
    if state.get("local_only"):
        state["generation_raw"] = ""
        state["generated_changes"] = []
        state.setdefault("warnings", []).append("local-only mode: skipped LLM code generation.")
        return state

    llm = ChatLLM()
    if not llm.available:
        raise RuntimeError("LLM is not configured. Set CODEGEN_API_KEY or run with --local-only.")

    raw = llm.complete(
        system=SYSTEM_PROMPT,
        user=code_generation_prompt(
            design_markdown=state["design_markdown"],
            contract=state["implementation_contract"],
            repo_context=state["repo_context"],
        ),
    )
    state["generation_raw"] = raw
    parsed = _parse_generation_json(raw)
    changes = _validate_generated_changes(
        parsed.get("files", []),
        allowed_paths={item["path"] for item in state["implementation_contract"].get("change_files", [])},
    )
    state["generated_changes"] = changes
    for note in parsed.get("notes", []) or []:
        state.setdefault("warnings", []).append(str(note))
    return state


def apply_changes(state: CodeGenState) -> CodeGenState:
    applied: list[GeneratedFileChange] = []
    for change in state.get("generated_changes", []):
        rel_path = change["path"]
        operation = _normalize_operation(change.get("operation", "Modify"))
        target = safe_repo_path(state["repo_root"], rel_path)
        if operation == "Delete":
            if target.exists():
                target.unlink()
            else:
                state.setdefault("warnings", []).append(f"Delete skipped because file does not exist: {rel_path}")
            applied.append({**change, "operation": "Delete"})
            continue
        content = change.get("content")
        if content is None:
            raise ValueError(f"Generated content is required for {operation}: {rel_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content).rstrip() + "\n", encoding="utf-8")
        applied.append({**change, "operation": operation})
    state["applied_changes"] = applied
    return state


def generate_diff(state: CodeGenState) -> CodeGenState:
    change_paths = [item["path"] for item in state["implementation_contract"].get("change_files", []) if item.get("path")]
    state["diff"] = build_git_diff(state["repo_root"], change_paths)
    return state


def smoke_check(state: CodeGenState) -> CodeGenState:
    checks: list[SmokeCheck] = []
    checks.append(
        {
            "name": "technical design parsed",
            "passed": bool(state.get("implementation_contract")),
            "detail": "implementation_contract loaded",
        }
    )
    repo_root = Path(state["repo_root"])
    checks.append(
        {
            "name": "source repository resolved",
            "passed": Path(state.get("source_repo_root", "")).exists(),
            "detail": state.get("source_repo_root", ""),
        }
    )
    checks.append(
        {
            "name": "task repository prepared",
            "passed": repo_root.exists(),
            "detail": str(repo_root),
        }
    )
    checks.append(
        {
            "name": "baseline aligned",
            "passed": _baseline_is_aligned(state),
            "detail": _baseline_detail(state),
        }
    )
    path_errors: list[str] = []
    for item in state.get("implementation_contract", {}).get("change_files", []):
        try:
            safe_repo_path(repo_root, item.get("path", ""))
        except Exception as exc:
            path_errors.append(str(exc))
    checks.append(
        {
            "name": "change paths are safe",
            "passed": not path_errors,
            "detail": "; ".join(path_errors) if path_errors else "all paths stay inside repository root",
        }
    )
    if state.get("local_only"):
        checks.append(
            {
                "name": "diff generation path",
                "passed": "diff" in state,
                "detail": "local-only mode allows an empty diff",
            }
        )
    else:
        diff_text = state.get("diff") or ""
        checks.append(
            {
                "name": "diff generated",
                "passed": bool(diff_text.strip()),
                "detail": "non-empty diff" if diff_text.strip() else "no changed lines were detected",
            }
        )
    for change in state.get("applied_changes", []):
        rel_path = change["path"]
        operation = _normalize_operation(change.get("operation", "Modify"))
        target = safe_repo_path(repo_root, rel_path)
        if operation == "Delete":
            passed = not target.exists()
            detail = "deleted" if passed else "still exists"
        else:
            passed = target.exists()
            detail = "file exists" if passed else "file missing"
        if passed:
            changed = has_git_diff(repo_root, rel_path)
            passed = changed
            detail = f"{detail}; git diff detected" if changed else f"{detail}; no git diff detected"
        checks.append({"name": f"{operation} {rel_path}", "passed": passed, "detail": detail})
    state["smoke_checks"] = checks
    if any(not check["passed"] for check in checks):
        state.setdefault("warnings", []).append("One or more smoke checks did not pass.")
    return state


def write_outputs(state: CodeGenState) -> CodeGenState:
    diff_path, report_path, result_json_path = make_output_paths(state["output_dir"], state["task_id"] or "task")
    write_text(diff_path, state.get("diff") or "")
    write_text(report_path, _build_report(state, diff_path, report_path))
    write_text(result_json_path, json.dumps(_build_result_json(state, diff_path, report_path, result_json_path), ensure_ascii=False, indent=2) + "\n")
    state["diff_path"] = str(diff_path)
    state["report_path"] = str(report_path)
    state["result_json_path"] = str(result_json_path)
    return state


def _parse_generation_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
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


def _validate_generated_changes(files: Any, allowed_paths: set[str]) -> list[GeneratedFileChange]:
    if not isinstance(files, list):
        raise ValueError("Generated JSON field `files` must be a list.")
    changes: list[GeneratedFileChange] = []
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Each generated file change must be an object.")
        path = str(item.get("path", "")).replace("\\", "/").lstrip("/")
        if path not in allowed_paths:
            raise ValueError(f"Generated file is not in allowed_change_files: {path}")
        operation = _normalize_operation(str(item.get("operation", "Modify")))
        changes.append(
            {
                "path": path,
                "operation": operation,
                "content": item.get("content"),
                "reason": str(item.get("reason", "")),
            }
        )
    return changes


def _normalize_operation(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"add", "added", "new"}:
        return "Add"
    if lowered in {"delete", "remove", "removed"}:
        return "Delete"
    return "Modify"


def _baseline_is_aligned(state: CodeGenState) -> bool:
    expected = state.get("expected_commit_sha")
    source = state.get("source_commit_sha")
    if not expected or not source:
        return True
    return expected.startswith(source) or source.startswith(expected)


def _baseline_detail(state: CodeGenState) -> str:
    expected = state.get("expected_commit_sha") or "not specified"
    source = state.get("source_commit_sha") or "not available"
    task_base = state.get("task_base_commit_sha") or "not available"
    return f"expected={expected}; source={source}; task_base={task_base}; method={state.get('worktree_method', '')}"


def _build_result_json(state: CodeGenState, diff_path: Path, report_path: Path, result_json_path: Path) -> dict[str, Any]:
    return {
        "task_id": state.get("task_id"),
        "technical_design_path": state.get("design_path"),
        "source_repo_root": state.get("source_repo_root"),
        "source_git_status": state.get("source_git_status"),
        "codegen_repo_path": state.get("repo_root"),
        "task_workspace_dir": state.get("task_workspace_dir"),
        "expected_commit_sha": state.get("expected_commit_sha"),
        "source_commit_sha": state.get("source_commit_sha"),
        "task_base_commit_sha": state.get("task_base_commit_sha"),
        "worktree_method": state.get("worktree_method"),
        "diff_path": str(diff_path),
        "report_path": str(report_path),
        "result_json_path": str(result_json_path),
        "changed_files": [
            {
                "path": change.get("path"),
                "operation": change.get("operation"),
                "reason": change.get("reason", ""),
            }
            for change in state.get("applied_changes", [])
        ],
        "planned_change_files": state.get("implementation_contract", {}).get("change_files", []),
        "smoke_checks": state.get("smoke_checks", []),
        "warnings": state.get("warnings", []),
        "errors": state.get("errors", []),
    }


def _build_report(state: CodeGenState, diff_path: Path, report_path: Path) -> str:
    contract = state.get("implementation_contract", {})
    changes = state.get("applied_changes", [])
    checks = state.get("smoke_checks", [])
    warnings = state.get("warnings", [])
    errors = state.get("errors", [])
    lines = [
        "# CodeGen Report",
        "",
        "## Summary",
        "",
        f"- Technical design: `{state.get('design_path', '')}`",
        f"- Source repository root: `{state.get('source_repo_root', '')}`",
        f"- Source repository status before CodeGen: `{_inline_status(state.get('source_git_status', '') or 'clean')}`",
        f"- CodeGen repository path: `{state.get('repo_root', '')}`",
        f"- Task workspace: `{state.get('task_workspace_dir', '')}`",
        f"- Baseline: {_baseline_detail(state)}",
        f"- Objective: {contract.get('objective', '')}",
        f"- Mode: {'local-only' if state.get('local_only') else 'LLM code generation'}",
        f"- Diff output: `{diff_path}`",
        f"- Report output: `{report_path}`",
        f"- Result JSON output: `{Path(report_path).with_name('codegen_result.json')}`",
        "",
        "## Applied Changes",
        "",
    ]
    if changes:
        for change in changes:
            reason = change.get("reason", "")
            suffix = f" - {reason}" if reason else ""
            lines.append(f"- {change.get('operation', '')}: `{change.get('path', '')}`{suffix}")
    else:
        lines.append("- No code files were modified.")
    lines.extend(["", "## Smoke Checks", ""])
    for check in checks:
        marker = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- {marker}: {check['name']} - {check['detail']}")
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    if errors:
        lines.extend(["", "## Errors", ""])
        for error in errors:
            lines.append(f"- {error}")
    if not (state.get("diff") or "").strip():
        lines.extend(["", "## Diff", "", "No diff content was generated."])
    return "\n".join(lines).rstrip() + "\n"


def _inline_status(status: str) -> str:
    return "; ".join(line.strip() for line in status.splitlines() if line.strip())
