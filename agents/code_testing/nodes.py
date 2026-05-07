from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, cast

from .io_utils import read_json, read_text, write_json, write_text, resolve_path_maybe_relative
from .prompts import (
    TEST_GEN_SYSTEM,
    TEST_PLAN_SYSTEM,
    test_files_prompt,
    test_plan_prompt,
)
from .schemas import CodeTestState, TestCaseResult
from .workspace import copy_task_repository, safe_repo_path
from stage_contracts import (
    probe_js_toolchain,
    record_dep_install,
    record_pm_fallback,
    record_pm_fallback_blocked,
    record_preflight_failure,
)


def _repair_feedback_suffix(state: CodeTestState) -> str:
    raw = state.get("repair_feedback_path") or ""
    path = Path(str(raw).strip()) if raw else None
    if not path or not path.is_file():
        return ""
    text = read_text(str(path.resolve()))
    return "\n\n---\nRepair feedback (prior failing run):\n" + _truncate(text, 16_000)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20] + "\n...(truncated)..."


def _max_llm_calls() -> int:
    raw = os.getenv("CODETEST_LLM_MAX_CALLS_PER_RUN", "12")
    try:
        return max(1, int(raw))
    except ValueError:
        return 12


def _bool_env(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _allow_pm_fallback() -> bool:
    return _bool_env("CODETEST_ALLOW_PM_FALLBACK", True)


def _bump_llm(state: CodeTestState) -> None:
    c = int(state.get("llm_calls") or 0) + 1
    cap = int(state.get("max_llm_calls") or _max_llm_calls())
    if c > cap:
        raise RuntimeError(
            f"LLM call budget exceeded ({cap} calls per run). Set CODETEST_LLM_MAX_CALLS_PER_RUN to raise."
        )
    state["llm_calls"] = c


def _parse_json_block(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return cast(dict[str, Any], json.loads(text))


def resolve_inputs(state: CodeTestState) -> CodeTestState:
    warnings = list(state.get("warnings") or [])
    errors = list(state.get("errors") or [])

    codegen_path = state.get("codegen_result_path")
    cli_design = state.get("design_path")
    cli_diff = state.get("diff_path")
    cli_repo = state.get("repo_path")
    cli_task = state.get("task_id")

    design_path: str | None = cli_design
    diff_path: str | None = cli_diff
    repo_source: str | None = cli_repo
    task_id: str | None = cli_task if cli_task else None

    if codegen_path:
        cg = Path(codegen_path).resolve()
        data = read_json(str(cg))
        base = cg.parent
        task_id = task_id or str(data.get("task_id") or "")
        if not design_path:
            design_path = resolve_path_maybe_relative(str(data.get("technical_design_path")), base)
        if not diff_path:
            diff_path = resolve_path_maybe_relative(str(data.get("diff_path")), base)
        if not repo_source:
            repo_source = resolve_path_maybe_relative(str(data.get("codegen_repo_path")), base)

    if not task_id or not str(task_id).strip():
        errors.append("task_id is required (via --task-id or codegen_result.json).")
    if not design_path:
        errors.append("design is required: pass --design or use --codegen-result with technical_design_path.")
    if not diff_path:
        errors.append("diff is required: pass --diff or use --codegen-result with diff_path.")
    if not repo_source:
        errors.append("repo path is required: pass --repo-path or use --codegen-result with codegen_repo_path.")

    state["errors"] = errors
    if errors:
        return state

    assert design_path and diff_path and repo_source and task_id
    d_path = Path(design_path)
    f_path = Path(diff_path)
    r_path = Path(repo_source)
    if not d_path.is_file():
        errors.append(f"Design file not found: {d_path}")
    if not f_path.is_file():
        errors.append(f"Diff file not found: {f_path}")
    if not r_path.is_dir():
        errors.append(f"Repository root not found: {r_path}")

    state["design_path"] = str(d_path.resolve())
    state["diff_path"] = str(f_path.resolve())
    state["source_codegen_repo"] = str(r_path.resolve())
    state["task_id"] = str(task_id)

    state["design_markdown"] = read_text(state["design_path"])
    state["diff_text"] = read_text(state["diff_path"])

    req = state.get("requirement_path")
    if req:
        rp = Path(req)
        if rp.is_file():
            state["requirement_text"] = read_text(rp)
        else:
            warnings.append(f"Requirement file not found (ignored): {rp}")
    else:
        state["requirement_text"] = ""

    state["warnings"] = warnings
    return state


def materialize_task_copy(state: CodeTestState) -> CodeTestState:
    if state.get("errors"):
        return state
    workspace_dir = Path(state["workspace_dir"])
    task_id = state["task_id"]
    dest = workspace_dir / "tasks" / task_id / "repo"
    try:
        copy_task_repository(
            source_root=Path(state["source_codegen_repo"]),
            dest_root=dest,
            force=bool(state.get("force")),
        )
    except RuntimeError as exc:
        state.setdefault("errors", []).append(str(exc))
        return state
    state["task_repo_path"] = str(dest.resolve())
    state["task_workspace_dir"] = str(dest.parent)
    return state


def detect_archetype(state: CodeTestState) -> CodeTestState:
    if state.get("errors") or not state.get("task_repo_path"):
        return state
    repo = Path(state["task_repo_path"])
    has_pkg = (repo / "package.json").is_file()
    state["repo_archetype"] = "nodejs_sp" if has_pkg else "static_html"
    state.setdefault("warnings", []).append(f"Repository archetype: {state['repo_archetype']}")
    return state


def preflight_toolchain(state: CodeTestState) -> CodeTestState:
    if state.get("errors") or state.get("local_only"):
        return state
    warnings = list(state.get("warnings") or [])
    probe = _effective_toolchain_probe()
    state["toolchain_probe"] = probe

    if not bool(probe.get("node_available")):
        state["environment_error_code"] = "ENV_NODE_MISSING"
        record_preflight_failure("ENV_NODE_MISSING")
        state.setdefault("errors", []).append(
            "Environment preflight failed: Node.js is unavailable on PATH; cannot execute CodeTest runtime."
        )
        warnings.append("Toolchain preflight: node missing.")
    elif not bool(probe.get("package_manager_available")):
        state["environment_error_code"] = "ENV_PM_MISSING"
        record_preflight_failure("ENV_PM_MISSING")
        state.setdefault("errors", []).append(
            "Environment preflight failed: no package manager (npm/pnpm/yarn) is available on PATH."
        )
        warnings.append("Toolchain preflight: package manager missing.")
    else:
        preferred = str(probe.get("recommended_package_manager") or "")
        if preferred:
            warnings.append(f"Toolchain preflight: using `{preferred}` as primary package manager.")
        if bool(probe.get("node_recovered_by_fallback")):
            warnings.append("Toolchain preflight: node resolved via fallback runtime path injection.")
        if bool(probe.get("pm_recovered_by_fallback")):
            warnings.append("Toolchain preflight: package manager resolved via fallback runtime path injection.")

    state["warnings"] = warnings
    return state


def _effective_toolchain_probe() -> dict[str, Any]:
    """Probe toolchain using the same runtime-env resolution path as command execution.

    `probe_js_toolchain()` inspects the current process PATH only. CodeTest execution
    uses `_subprocess_env()` which prepends fallback Node directories. This helper
    keeps preflight consistent with actual runtime behavior.
    """
    path_probe = probe_js_toolchain()
    env = _subprocess_env({})

    runtime_node_available = _node_executable(env) is not None
    runtime_npm_available = _resolve_npm_invocation(["--version"], env) is not None
    runtime_pnpm_available = _cmd_exists(_resolve_cmd(["pnpm", "--version"]), env)
    runtime_yarn_available = _cmd_exists(_resolve_cmd(["yarn", "--version"]), env)
    runtime_pm_available = runtime_npm_available or runtime_pnpm_available or runtime_yarn_available

    recommended = ""
    if runtime_npm_available:
        recommended = "npm"
    elif runtime_pnpm_available:
        recommended = "pnpm"
    elif runtime_yarn_available:
        recommended = "yarn"

    return {
        "checked_at": path_probe.get("checked_at"),
        "status": "ok" if runtime_node_available and runtime_pm_available else "degraded",
        "node_available": runtime_node_available,
        "package_manager_available": runtime_pm_available,
        "recommended_package_manager": recommended,
        "node_recovered_by_fallback": (not bool(path_probe.get("node_available"))) and runtime_node_available,
        "pm_recovered_by_fallback": (not bool(path_probe.get("package_manager_available"))) and runtime_pm_available,
        "path_probe": path_probe,
        "runtime_probe": {
            "node_available": runtime_node_available,
            "npm_available": runtime_npm_available,
            "pnpm_available": runtime_pnpm_available,
            "yarn_available": runtime_yarn_available,
        },
    }


def _classify_static_html_scenario(
    *,
    ids: set[str],
    classes: set[str],
    has_select: bool,
    checkbox_count: int,
) -> str:
    if checkbox_count > 0 and "inbox" in classes and not has_select:
        return "checkbox_shift_range"
    filter_ids = {"filterStatus", "filterPriority", "sortField", "sortOrder"}
    if has_select and filter_ids.intersection(ids) and ("taskList" in ids or "toolbar" in classes):
        return "task_filter_sort"
    return "generic_static_html"


def compute_static_html_facts(state: CodeTestState) -> CodeTestState:
    """Derive simple DOM facts from the static HTML entry to guide test generation.

    This is intentionally best-effort and only applies to static_html archetype.
    Failures must NOT break the pipeline; we fall back to the original behavior.
    """
    if state.get("errors") or not state.get("task_repo_path"):
        return state
    if state.get("repo_archetype") != "static_html":
        return state

    repo = Path(state["task_repo_path"])

    entry: Path | None = None
    candidate = repo / "index-START.html"
    if candidate.is_file():
        entry = candidate
    else:
        # Fallback: pick a reasonable HTML entry in repo root
        htmls = sorted([p for p in repo.glob("*.html") if p.is_file()])
        if htmls:
            entry = htmls[0]

    if not entry:
        return state

    try:
        html = entry.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return state

    checkbox_pattern = re.compile(r"<input\b[^>]*\btype\s*=\s*[\"']?\s*checkbox\s*[\"']?[^>]*>", re.IGNORECASE)
    id_pattern = re.compile(r"\bid\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
    class_pattern = re.compile(r"\bclass\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
    tag_pattern = re.compile(r"<\s*([a-zA-Z][a-zA-Z0-9:-]*)\b")
    has_select = bool(re.search(r"<select\b", html, re.IGNORECASE))
    count = len(checkbox_pattern.findall(html))
    ids = {v.strip() for v in id_pattern.findall(html) if v.strip()}
    classes: set[str] = set()
    for chunk in class_pattern.findall(html):
        classes.update(part.strip() for part in chunk.split() if part.strip())
    tags = {v.lower().strip() for v in tag_pattern.findall(html) if v.strip()}
    scenario_type = _classify_static_html_scenario(
        ids=ids,
        classes=classes,
        has_select=has_select,
        checkbox_count=int(count),
    )
    state["entry_html_path"] = entry.name
    state["checkbox_count"] = int(count)
    state["scenario_type"] = scenario_type
    state["static_html_facts"] = {
        "ids": sorted(ids),
        "classes": sorted(classes),
        "tags": sorted(tags),
        "has_select": has_select,
        "has_checkbox_inputs": count > 0,
    }
    state.setdefault("warnings", []).append(f"Detected static_html scenario={scenario_type} from {entry.name}")
    if count > 0:
        state.setdefault("warnings", []).append(f"Detected checkbox_count={count} from {entry.name}")
    return state


def _plan_needs_e2e(plan: dict[str, Any]) -> bool:
    for layer in plan.get("layers") or []:
        if str(layer.get("type", "")).lower() == "e2e":
            return True
    env = plan.get("environment") or {}
    if isinstance(env, dict) and env.get("needs_playwright"):
        return True
    return False


def generate_test_plan(state: CodeTestState) -> CodeTestState:
    if state.get("errors") or not state.get("task_repo_path"):
        return state
    if state.get("local_only"):
        state.setdefault("warnings", []).append("local-only: skipped test_plan LLM.")
        state["test_plan_dict"] = {"layers": [], "summary": "local-only"}
        return state

    from .llm import ChatLLM

    llm = ChatLLM()
    if not llm.available:
        raise RuntimeError("LLM is not configured. Set CODETEST_API_KEY or run with --local-only.")

    design_excerpt = _truncate(state.get("design_markdown", ""), 12000)
    diff_excerpt = _truncate(state.get("diff_text", ""), 16000)
    req = state.get("requirement_text") or ""
    if req:
        design_excerpt += "\n\nRequirement (excerpt):\n" + _truncate(req, 8000)

    user = test_plan_prompt(
        design_excerpt=design_excerpt,
        diff_excerpt=diff_excerpt,
        repo_archetype=state.get("repo_archetype", "static_html"),
        repo_hint=state["task_repo_path"],
        entry_html_path=state.get("entry_html_path"),
        checkbox_count=state.get("checkbox_count"),
        scenario_type=state.get("scenario_type"),
    )
    user += _repair_feedback_suffix(state)
    _bump_llm(state)
    raw = llm.complete(system=TEST_PLAN_SYSTEM, user=user)
    state["plan_generation_raw"] = raw
    try:
        plan = _parse_json_block(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Failed to parse test_plan JSON: {exc}") from exc

    state["test_plan_dict"] = plan
    state["needs_e2e"] = _plan_needs_e2e(plan)

    out = Path(state["output_dir"]).resolve() / state["task_id"]
    out.mkdir(parents=True, exist_ok=True)
    tp = out / "test_plan.json"
    write_json(tp, plan)
    state["test_plan_path"] = str(tp)
    return state


def generate_test_files(state: CodeTestState) -> CodeTestState:
    if state.get("errors") or not state.get("task_repo_path"):
        return state
    warnings = list(state.get("warnings") or [])
    generated: list[str] = []
    state["generation_raw"] = ""

    if state.get("local_only"):
        warnings.append("local-only mode: skipped test file generation.")
        state["generated_files"] = []
        state["warnings"] = warnings
        return state

    from .llm import ChatLLM

    llm = ChatLLM()
    if not llm.available:
        raise RuntimeError("LLM is not configured. Set CODETEST_API_KEY or run with --local-only.")

    design_excerpt = _truncate(state.get("design_markdown", ""), 12000)
    diff_excerpt = _truncate(state.get("diff_text", ""), 16000)

    user = test_files_prompt(
        test_plan=state.get("test_plan_dict") or {},
        design_excerpt=design_excerpt,
        diff_excerpt=diff_excerpt,
        repo_archetype=state.get("repo_archetype", "static_html"),
        repo_hint=state["task_repo_path"],
        entry_html_path=state.get("entry_html_path"),
        checkbox_count=state.get("checkbox_count"),
        scenario_type=state.get("scenario_type"),
    )
    user += _repair_feedback_suffix(state)
    _bump_llm(state)
    raw = llm.complete(system=TEST_GEN_SYSTEM, user=user)
    state["generation_raw"] = raw

    try:
        payload = _parse_json_block(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Failed to parse test_generation JSON: {exc}") from exc

    repo_root = Path(state["task_repo_path"])
    for item in payload.get("files", []) or []:
        rel = str(item.get("path", "")).strip().replace("\\", "/")
        content = item.get("content")
        if not rel or content is None:
            continue
        target = safe_repo_path(repo_root, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content).rstrip() + "\n", encoding="utf-8")
        generated.append(rel)

    for note in payload.get("notes", []) or []:
        warnings.append(str(note))

    # Persist generation artifact
    out = Path(state["output_dir"]).resolve() / state["task_id"]
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "test_generation.json", payload)

    state["generated_files"] = generated
    state["warnings"] = warnings

    _post_validate_static_html_e2e(state, warnings)
    return state


def _post_validate_static_html_e2e(state: CodeTestState, warnings: list[str]) -> None:
    """Guardrail: if we know checkbox_count, generated E2E tests must not hardcode counts or go out of bounds."""
    if state.get("repo_archetype") != "static_html":
        return
    entry_html = state.get("entry_html_path")
    if not entry_html:
        return
    repo = Path(state["task_repo_path"])
    entry_path = repo / str(entry_html)
    try:
        html = entry_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    checkbox_count = int(state.get("checkbox_count") or 0)
    static_facts = state.get("static_html_facts") or {}
    ids = {str(v) for v in static_facts.get("ids") or []}
    classes = {str(v) for v in static_facts.get("classes") or []}
    tags = {str(v).lower() for v in static_facts.get("tags") or []}
    has_select = bool(static_facts.get("has_select"))
    has_checkbox_inputs = bool(static_facts.get("has_checkbox_inputs"))
    scenario_type = str(state.get("scenario_type") or "generic_static_html")

    # Only validate if an E2E spec was generated
    spec_paths = [p for p in (repo / "e2e").glob("*.spec.ts")] if (repo / "e2e").is_dir() else []
    if not spec_paths:
        return
    max_index = checkbox_count - 1 if checkbox_count > 0 else -1
    hardcoded_loops = re.compile(r"for\s*\(\s*let\s+\w+\s*=\s*0\s*;\s*\w+\s*<\s*(\d+)\s*;", re.IGNORECASE)
    nth_calls = re.compile(r"\.nth\(\s*(\d+)\s*\)")
    selector_call_pattern = re.compile(
        r"\b(?:waitForSelector|locator|selectOption|click|fill|check|uncheck|hover|dblclick)\(\s*(['\"])([^'\n\"]+)\1"
    )
    class_token_pattern = re.compile(r"\.([A-Za-z_][\w-]*)")
    id_token_pattern = re.compile(r"#([A-Za-z_][\w-]*)")
    tag_token_pattern = re.compile(r"^\s*([a-zA-Z][a-zA-Z0-9-]*)")
    has_select_option = re.compile(r"\bselectOption\(")

    repairable_issues: list[str] = []
    semantic_issues: list[str] = []
    for spec in spec_paths:
        text = spec.read_text(encoding="utf-8", errors="replace")
        for m in hardcoded_loops.finditer(text):
            repairable_issues.append(f"{spec.as_posix()}: hardcoded loop upper bound {m.group(1)}; use checkboxes.count()")
        if checkbox_count > 0:
            for m in nth_calls.finditer(text):
                idx = int(m.group(1))
                if idx > max_index:
                    repairable_issues.append(
                        f"{spec.as_posix()}: nth({idx}) out of range for checkbox_count={checkbox_count} (max {max_index})"
                    )

        if has_select_option.search(text) and not has_select:
            semantic_issues.append(
                f"{spec.as_posix()}: selector-semantic mismatch uses selectOption() but {entry_html} has no <select>."
            )

        if scenario_type == "checkbox_shift_range":
            blocked = ["#filterStatus", "#filterPriority", "#sortField", "#sortOrder", "#taskList", ".toolbar"]
            for token in blocked:
                if token in text:
                    semantic_issues.append(
                        f"{spec.as_posix()}: selector-semantic mismatch uses `{token}` but scenario is checkbox_shift_range."
                    )

        for m in selector_call_pattern.finditer(text):
            selector = m.group(2).strip()
            if not selector:
                continue
            # Skip non-css selector engines and URL-like values.
            if selector.startswith(("text=", "xpath=", "internal:", "role=", "label=", "placeholder=")):
                continue
            if selector.endswith(".html") or selector.startswith("http") or selector.startswith("file:"):
                continue
            if selector.startswith("#"):
                for sel_id in id_token_pattern.findall(selector):
                    if sel_id not in ids:
                        semantic_issues.append(
                            f"{spec.as_posix()}: selector-semantic mismatch id `#{sel_id}` not present in {entry_html}."
                        )
            if "." in selector:
                for cls in class_token_pattern.findall(selector):
                    if cls not in classes:
                        semantic_issues.append(
                            f"{spec.as_posix()}: selector-semantic mismatch class `.{cls}` not present in {entry_html}."
                        )
            if selector.startswith("input") and "checkbox" in selector and not has_checkbox_inputs:
                semantic_issues.append(
                    f"{spec.as_posix()}: selector-semantic mismatch expects checkbox inputs but none were found in {entry_html}."
                )
            if selector[0].isalpha():
                tag_match = tag_token_pattern.match(selector)
                if tag_match:
                    tag = tag_match.group(1).lower()
                    if tag not in tags:
                        semantic_issues.append(
                            f"{spec.as_posix()}: selector-semantic mismatch tag `{tag}` not present in {entry_html}."
                        )

    def _dedupe(items: list[str]) -> list[str]:
        uniq: list[str] = []
        seen: set[str] = set()
        for issue in items:
            if issue in seen:
                continue
            seen.add(issue)
            uniq.append(issue)
        return uniq

    repairable_issues = _dedupe(repairable_issues)
    semantic_issues = _dedupe(semantic_issues)

    if semantic_issues:
        state["validation_error_code"] = "TEST_GENERATION_MISMATCH"
        state["validation_issues"] = semantic_issues
        warnings.append("Generated E2E tests failed selector-semantic validation; skipping test execution.")
        state.setdefault("errors", []).extend(semantic_issues)
        return

    if repairable_issues:
        warnings.append("Generated E2E tests violate static_html guardrails; attempting one automatic fix.")
        if state.get("local_only"):
            state["validation_error_code"] = "TEST_GENERATION_MISMATCH"
            state["validation_issues"] = repairable_issues
            state.setdefault("errors", []).extend(repairable_issues)
            return
        from .llm import ChatLLM

        llm = ChatLLM()
        if not llm.available:
            state["validation_error_code"] = "TEST_GENERATION_MISMATCH"
            state["validation_issues"] = repairable_issues
            state.setdefault("errors", []).extend(repairable_issues)
            return
        if int(state.get("llm_calls") or 0) >= int(state.get("max_llm_calls") or 0):
            state["validation_error_code"] = "TEST_GENERATION_MISMATCH"
            state["validation_issues"] = repairable_issues
            state.setdefault("errors", []).extend(repairable_issues)
            return

        # Try a single-file repair: rewrite each spec to use dynamic count and avoid out-of-range nth().
        for spec in spec_paths:
            original = spec.read_text(encoding="utf-8", errors="replace")
            repair_user = f"""You are fixing an existing Playwright E2E test file for a static HTML repo.
Facts:
- entry_html_path: {entry_html}
- checkbox_count: {checkbox_count}
Fix requirements:
- Do NOT change test intent.
- Replace any hardcoded count loops like `for (i < 10)` with `const n = await checkboxes.count()` and loop over n.
- Remove any `.nth(K)` where K >= {checkbox_count}; rewrite to use valid indices or dynamic iteration.
- Output ONLY the full corrected TypeScript file content. No JSON. No markdown fences.

Original file path: {spec.as_posix()}
Original content:
{original[:24000]}
"""
            _bump_llm(state)
            fixed = llm.complete(system="Output ONLY the corrected TypeScript file content.", user=repair_user)
            if fixed and isinstance(fixed, str) and "test(" in fixed:
                spec.write_text(fixed.rstrip() + "\n", encoding="utf-8")
        # Re-run validation (best effort)
        # If still failing, record issues and let run_tests surface it.
        return


def _detect_package_manager(repo: Path) -> list[str]:
    if (repo / "pnpm-lock.yaml").is_file():
        return ["pnpm", "exec"]
    if (repo / "yarn.lock").is_file():
        return ["yarn"]
    return ["npm"]


def _node_bin_candidates() -> list[Path]:
    candidates: list[Path] = []
    raw = (os.getenv("CODETEST_NODE_BIN_DIR") or "").strip()
    if raw:
        candidates.append(Path(raw))
    for env_name in ("NODE_HOME", "NODEJS_HOME"):
        value = (os.getenv(env_name) or "").strip()
        if value:
            base = Path(value)
            candidates.append(base)
            candidates.append(base / "bin")
    node = shutil.which("node.exe") or shutil.which("node")
    if node:
        candidates.append(Path(node).resolve().parent)
    if os.name == "nt":
        candidates.extend(
            [
                Path(r"C:\Program Files\nodejs"),
                Path(r"C:\Program Files (x86)\nodejs"),
                Path(r"C:\nodejs"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("/usr/local/bin"),
                Path("/usr/bin"),
                Path("/opt/node/bin"),
            ]
        )
    seen: set[str] = set()
    resolved: list[Path] = []
    for path in candidates:
        try:
            p = path.resolve()
        except OSError:
            p = path
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.is_dir():
            resolved.append(p)
    return resolved


def _node_bin_dir() -> str | None:
    """Directory containing node executable (and usually npm/npx shims)."""
    for bindir in _node_bin_candidates():
        node_name = "node.exe" if os.name == "nt" else "node"
        if (bindir / node_name).is_file():
            return str(bindir)
    return str(_node_bin_candidates()[0]) if _node_bin_candidates() else None


def _subprocess_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    if extra:
        env.update(extra)
    bindirs = [str(p) for p in _node_bin_candidates()]
    if bindirs:
        sep = os.pathsep
        path = env.get("PATH", "")
        existing = path.split(sep) if path else []
        merged = bindirs + [item for item in existing if item and item not in bindirs]
        env["PATH"] = sep.join(merged)
    return env


def _resolve_cmd(cmd: list[str]) -> list[str]:
    """Windows CreateProcess cannot resolve `npm` -> `npm.cmd`; use explicit shim path."""
    if not cmd or os.name != "nt":
        return cmd
    head, *rest = cmd
    bindir_s = _node_bin_dir()
    if head in {"npm", "npx"} and bindir_s:
        shim = Path(bindir_s) / f"{head}.cmd"
        if shim.is_file():
            return [str(shim), *rest]
    if head == "pnpm" and bindir_s:
        shim = Path(bindir_s) / "pnpm.cmd"
        if shim.is_file():
            return [str(shim), *rest]
    if head == "yarn" and bindir_s:
        shim = Path(bindir_s) / "yarn.cmd"
        if shim.is_file():
            return [str(shim), *rest]
    return cmd


def _cmd_exists(cmd: list[str], env: dict[str, str]) -> bool:
    if not cmd:
        return False
    head = cmd[0]
    if Path(head).is_file():
        return True
    return shutil.which(head, path=env.get("PATH", "")) is not None


def _node_executable(env: dict[str, str]) -> str | None:
    value = (os.getenv("CODETEST_NODE_EXE") or "").strip()
    if value and Path(value).is_file():
        return str(Path(value).resolve())
    for name in ("node.exe", "node"):
        found = shutil.which(name, path=env.get("PATH", ""))
        if found:
            return str(Path(found).resolve())
    return None


def _npm_cli_candidates(node_exe: str) -> list[Path]:
    node_bin = Path(node_exe).resolve().parent
    npm_rel_paths = [
        Path("node_modules/npm/bin/npm-cli.js"),
        Path("../lib/node_modules/npm/bin/npm-cli.js"),
        Path("../lib64/node_modules/npm/bin/npm-cli.js"),
        Path("npm/node_modules/npm/bin/npm-cli.js"),
    ]
    candidates = [node_bin / rel for rel in npm_rel_paths]
    if os.name != "nt":
        candidates.extend(
            [
                Path("/usr/local/lib/node_modules/npm/bin/npm-cli.js"),
                Path("/usr/lib/node_modules/npm/bin/npm-cli.js"),
                Path("/opt/node/lib/node_modules/npm/bin/npm-cli.js"),
            ]
        )
    else:
        candidates.extend(
            [
                Path(r"C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js"),
                Path(r"C:\Program Files (x86)\nodejs\node_modules\npm\bin\npm-cli.js"),
            ]
        )
    value = (os.getenv("CODETEST_NPM_CLI_PATH") or "").strip()
    if value:
        candidates.insert(0, Path(value))
    seen: set[str] = set()
    resolved: list[Path] = []
    for path in candidates:
        try:
            p = path.resolve()
        except OSError:
            p = path
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(p)
    return resolved


def _resolve_npm_invocation(args: list[str], env: dict[str, str]) -> list[str] | None:
    npm_cmd = _resolve_cmd(["npm", *args])
    if _cmd_exists(npm_cmd, env):
        return npm_cmd
    node_exe = _node_executable(env)
    if not node_exe:
        return None
    for npm_cli in _npm_cli_candidates(node_exe):
        if npm_cli.is_file():
            return [node_exe, str(npm_cli), *args]
    return None


def _resolve_npx_invocation(args: list[str], env: dict[str, str]) -> list[str] | None:
    npx_cmd = _resolve_cmd(["npx", *args])
    if _cmd_exists(npx_cmd, env):
        return npx_cmd
    # Fallback: npm exec -- <args>
    return _resolve_npm_invocation(["exec", "--", *args], env)


def _install_timeout_seconds() -> float:
    raw = os.getenv("CODETEST_INSTALL_TIMEOUT_SECONDS", "900")
    try:
        return float(raw)
    except ValueError:
        return 900.0


def _install_dependencies(repo: Path, pm: list[str], log_lines: list[str]) -> bool:
    env = _subprocess_env({})
    install_start = time.perf_counter()

    def _finalize(success: bool) -> bool:
        duration_ms = int((time.perf_counter() - install_start) * 1000)
        record_dep_install(duration_ms=duration_ms, success=success)
        return success

    if pm == ["pnpm", "exec"]:
        cmd = _resolve_cmd(["pnpm", "install", "--frozen-lockfile"])
        if not _cmd_exists(cmd, env):
            cmd = _resolve_cmd(["pnpm", "install"])
    elif pm == ["yarn"]:
        cmd = _resolve_cmd(["yarn", "install", "--frozen-lockfile"])
        if not _cmd_exists(cmd, env):
            cmd = _resolve_cmd(["yarn", "install"])
    else:
        if (repo / "package-lock.json").is_file():
            cmd = _resolve_npm_invocation(["ci"], env)
        else:
            cmd = _resolve_npm_invocation(["install"], env)
        if cmd is None:
            if _allow_pm_fallback():
                # Lightweight fallback: try other package managers when npm is unavailable.
                pnpm_cmd = _resolve_cmd(["pnpm", "install"])
                yarn_cmd = _resolve_cmd(["yarn", "install"])
                if _cmd_exists(pnpm_cmd, env):
                    cmd = pnpm_cmd
                    log_lines.append("npm unavailable; fallback to pnpm install")
                    record_pm_fallback("pnpm")
                elif _cmd_exists(yarn_cmd, env):
                    cmd = yarn_cmd
                    log_lines.append("npm unavailable; fallback to yarn install")
                    record_pm_fallback("yarn")
            if cmd is None:
                if not _allow_pm_fallback():
                    record_pm_fallback_blocked()
                    log_lines.append("npm unavailable and CODETEST_ALLOW_PM_FALLBACK=false")
                log_lines.append("package manager not found on PATH")
                log_lines.append(f"node_bin_candidates={', '.join(str(p) for p in _node_bin_candidates())}")
                return _finalize(False)

    log_lines.append(f"$ {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=_install_timeout_seconds(),
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        log_lines.append(proc.stdout or "")
        log_lines.append(proc.stderr or "")
        return _finalize(proc.returncode == 0)
    except subprocess.TimeoutExpired:
        log_lines.append("install timed out")
        return _finalize(False)
    except FileNotFoundError:
        log_lines.append("package manager not found on PATH")
        return _finalize(False)


def _test_timeout_seconds() -> float:
    raw = os.getenv("CODETEST_TEST_TIMEOUT_SECONDS", "600")
    try:
        return float(raw)
    except ValueError:
        return 600.0


def _maybe_playwright_install(repo: Path, pm: list[str], log_lines: list[str]) -> None:
    pkg = repo / "package.json"
    if not pkg.is_file():
        return
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    if "@playwright/test" not in deps and "playwright" not in deps:
        return
    env = _subprocess_env({"CI": "1"})
    cmd = _resolve_npx_invocation(["playwright", "install", "--with-deps"], env)
    if cmd is None:
        log_lines.append("playwright install skipped: npx/npm is unavailable on PATH")
        return
    log_lines.append(f"$ {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=_install_timeout_seconds(),
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        log_lines.append(proc.stdout or "")
        log_lines.append(proc.stderr or "")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        log_lines.append(f"playwright install skipped or failed: {exc}")


def run_tests(state: CodeTestState) -> CodeTestState:
    if state.get("errors") or not state.get("task_repo_path"):
        return state
    warnings = list(state.get("warnings") or [])
    repo = Path(state["task_repo_path"])
    commands: list[str] = []
    all_stdout: list[str] = []
    all_stderr: list[str] = []
    exit_code: int | None = 0
    duration_ms = 0

    if state.get("local_only"):
        warnings.append("local-only: skipped install and test execution.")
        state["status"] = "test"
        state["summary"] = "local-only smoke: copied repo; no LLM test plan/files and no npm test."
        state["test_commands"] = []
        state["exit_code"] = None
        state["duration_ms"] = 0
        state["stdout_tail"] = ""
        state["stderr_tail"] = ""
        state["case_results"] = []
        state["warnings"] = warnings
        state["log_body"] = "\n".join(warnings)
        return state

    pkg = repo / "package.json"
    if not pkg.is_file():
        state["status"] = "failed"
        state["summary"] = "No package.json after generation; cannot run tests."
        state["test_commands"] = []
        state["exit_code"] = 1
        state["warnings"] = warnings
        return state

    pm = _detect_package_manager(repo)
    log_lines: list[str] = []
    env_for_cmd = _subprocess_env({"CI": "true"})

    if not _install_dependencies(repo, pm, log_lines):
        if any("package manager not found on PATH" in line for line in log_lines):
            state["environment_error_code"] = "ENV_PM_MISSING"
        state["status"] = "failed"
        state["summary"] = "Dependency install failed; see test_run log."
        state["test_commands"] = commands
        state["exit_code"] = 1
        state["stdout_tail"] = "\n".join(log_lines)[-8000:]
        state["stderr_tail"] = ""
        state["log_body"] = "\n".join(log_lines)
        state["warnings"] = warnings
        return state

    _maybe_playwright_install(repo, pm, log_lines)

    pkg_data = json.loads(pkg.read_text(encoding="utf-8"))
    scripts = pkg_data.get("scripts") or {}

    if "test" not in scripts:
        state["status"] = "failed"
        state["summary"] = 'package.json has no "test" script after generation.'
        state["test_commands"] = []
        state["exit_code"] = 1
        state["warnings"] = warnings
        state["log_body"] = "\n".join(log_lines)
        return state

    def run_cmd(cmd_list: list[str], label: str) -> tuple[int, int]:
        nonlocal duration_ms
        commands.append(" ".join(cmd_list))
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd_list,
                cwd=str(repo),
                capture_output=True,
                text=True,
                timeout=_test_timeout_seconds(),
                encoding="utf-8",
                errors="replace",
                env=env_for_cmd,
            )
            dur = int((time.perf_counter() - start) * 1000)
            duration_ms += dur
            out = proc.stdout or ""
            err = proc.stderr or ""
            all_stdout.append(f"=== {label} ===\n{out}")
            all_stderr.append(f"=== {label} ===\n{err}")
            log_lines.append(f"$ {' '.join(cmd_list)}")
            log_lines.append(out)
            log_lines.append(err)
            return proc.returncode, dur
        except subprocess.TimeoutExpired:
            duration_ms += int(_test_timeout_seconds() * 1000)
            all_stdout.append(f"{label}: timed out")
            return 124, 0
        except FileNotFoundError:
            all_stderr.append(f"{label}: command not found")
            return 127, 0

    # Build npm/pnpm test command base
    if pm == ["pnpm", "exec"]:
        base_test = ["pnpm", "test", "--"]
    elif pm == ["yarn"]:
        base_test = ["yarn", "test"]
    else:
        npm_test = _resolve_npm_invocation(["test", "--"], env_for_cmd)
        if npm_test is None:
            if _allow_pm_fallback():
                pnpm_test = _resolve_cmd(["pnpm", "test", "--"])
                yarn_test = _resolve_cmd(["yarn", "test"])
                if _cmd_exists(pnpm_test, env_for_cmd):
                    base_test = pnpm_test
                    log_lines.append("npm test unavailable; fallback to pnpm test")
                    record_pm_fallback("pnpm-test")
                elif _cmd_exists(yarn_test, env_for_cmd):
                    base_test = yarn_test
                    log_lines.append("npm test unavailable; fallback to yarn test")
                    record_pm_fallback("yarn-test")
                else:
                    state["environment_error_code"] = "ENV_PM_MISSING"
                    state["status"] = "failed"
                    state["summary"] = "npm is unavailable for running tests; see test_run log."
                    state["test_commands"] = commands
                    state["exit_code"] = 127
                    state["stdout_tail"] = ""
                    state["stderr_tail"] = ""
                    state["log_body"] = "\n".join(
                        [
                            "npm test command could not be resolved.",
                            f"node_bin_candidates={', '.join(str(p) for p in _node_bin_candidates())}",
                        ]
                    )
                    state["warnings"] = warnings
                    return state
            else:
                record_pm_fallback_blocked()
                state["environment_error_code"] = "ENV_PM_MISSING"
                state["status"] = "failed"
                state["summary"] = "npm is unavailable for running tests; fallback disabled."
                state["test_commands"] = commands
                state["exit_code"] = 127
                state["stdout_tail"] = ""
                state["stderr_tail"] = ""
                state["log_body"] = "\n".join(
                    [
                        "npm test command could not be resolved.",
                        "CODETEST_ALLOW_PM_FALLBACK=false",
                        f"node_bin_candidates={', '.join(str(p) for p in _node_bin_candidates())}",
                    ]
                )
                state["warnings"] = warnings
                return state
        else:
            base_test = npm_test

    extra = ["--run"] if "vitest" in str(scripts.get("test", "")).lower() else []
    cmd = _resolve_cmd(base_test + extra if extra else base_test)
    unit_rc, _ = run_cmd(cmd, "unit/component (npm test)")
    if unit_rc != 0:
        state["status"] = "failed"
        state["summary"] = f"Tests failed (exit {unit_rc}). See log."
        state["test_commands"] = commands
        state["exit_code"] = unit_rc
        state["duration_ms"] = duration_ms
        state["stdout_tail"] = "\n".join(all_stdout)[-12000:]
        state["stderr_tail"] = "\n".join(all_stderr)[-12000:]
        state["case_results"] = []
        state["warnings"] = warnings
        state["log_body"] = "\n".join(log_lines)
        return state

    exit_code = 0
    if state.get("needs_e2e"):
        e2e_cmd: list[str] | None = None
        if "test:e2e" in scripts:
            if pm == ["pnpm", "exec"]:
                e2e_cmd = ["pnpm", "run", "test:e2e"]
            elif pm == ["yarn"]:
                e2e_cmd = ["yarn", "run", "test:e2e"]
            else:
                e2e_cmd = _resolve_npm_invocation(["run", "test:e2e"], env_for_cmd)
                if e2e_cmd is None and _allow_pm_fallback():
                    pnpm_e2e = _resolve_cmd(["pnpm", "run", "test:e2e"])
                    yarn_e2e = _resolve_cmd(["yarn", "run", "test:e2e"])
                    if _cmd_exists(pnpm_e2e, env_for_cmd):
                        e2e_cmd = pnpm_e2e
                        log_lines.append("npm run test:e2e unavailable; fallback to pnpm run test:e2e")
                        record_pm_fallback("pnpm-e2e")
                    elif _cmd_exists(yarn_e2e, env_for_cmd):
                        e2e_cmd = yarn_e2e
                        log_lines.append("npm run test:e2e unavailable; fallback to yarn run test:e2e")
                        record_pm_fallback("yarn-e2e")
        elif (repo / "playwright.config.ts").is_file() or (repo / "playwright.config.mjs").is_file() or (repo / "playwright.config.js").is_file():
            e2e_cmd = _resolve_npx_invocation(["playwright", "test"], env_for_cmd)
        if e2e_cmd:
            e2e_cmd = _resolve_cmd(e2e_cmd)
            e2e_rc, _ = run_cmd(e2e_cmd, "e2e")
            exit_code = e2e_rc

    passed = exit_code == 0
    state["status"] = "passed" if passed else "failed"
    state["summary"] = f"Tests {'passed' if passed else 'failed'} (exit {exit_code}) in {duration_ms}ms."
    state["test_commands"] = commands
    state["exit_code"] = exit_code
    state["duration_ms"] = duration_ms
    state["stdout_tail"] = "\n".join(all_stdout)[-12000:]
    state["stderr_tail"] = "\n".join(all_stderr)[-12000:]
    state["case_results"] = []
    state["warnings"] = warnings
    state["log_body"] = "\n".join(log_lines)
    return state


def write_outputs(state: CodeTestState) -> CodeTestState:
    if state.get("errors") and not state.get("status"):
        state["status"] = "failed"
        state.setdefault("summary", "; ".join(state.get("errors") or []))

    tid = state.get("task_id") or "task"
    output_dir = Path(state["output_dir"]).resolve() / tid
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "code_test_report.md"
    result_path = output_dir / "code_test_result.json"
    log_path = output_dir / "test_run.log"

    lines = [
        "# CodeTest Report",
        "",
        f"- Task id: `{tid}`",
        f"- Archetype: `{state.get('repo_archetype', '')}`",
        f"- Mode: **{'local-only' if state.get('local_only') else 'full'}**",
        f"- Task repository: `{state.get('task_repo_path', '')}`",
        f"- LLM calls: `{state.get('llm_calls', 0)}` / cap `{state.get('max_llm_calls', _max_llm_calls())}`",
        f"- Status: **{state.get('status', '')}**",
        f"- Summary: {state.get('summary', '')}",
        "",
        "## Generated files",
        "",
    ]
    for p in state.get("generated_files") or []:
        lines.append(f"- `{p}`")
    if not state.get("generated_files"):
        lines.append("- _(none)_")
    lines.extend(["", "## Warnings", ""])
    for w in state.get("warnings") or []:
        lines.append(f"- {w}")
    if state.get("errors"):
        lines.extend(["", "## Errors", ""])
        for e in state.get("errors") or []:
            lines.append(f"- {e}")

    write_text(report_path, "\n".join(lines) + "\n")

    log_body = str(state.get("log_body") or "")
    if log_body:
        write_text(log_path, log_body)
    elif state.get("local_only"):
        write_text(log_path, "local-only: no test command executed.\n")

    payload: dict[str, Any] = {
        "task_id": tid,
        "status": state.get("status") or ("failed" if state.get("errors") else "unknown"),
        "summary": state.get("summary", ""),
        "local_only": bool(state.get("local_only")),
        "repo_archetype": state.get("repo_archetype"),
        "llm_calls": state.get("llm_calls", 0),
        "max_llm_calls": state.get("max_llm_calls", _max_llm_calls()),
        "test_plan_path": state.get("test_plan_path", ""),
        "design_path": state.get("design_path"),
        "diff_path": state.get("diff_path"),
        "source_codegen_repo": state.get("source_codegen_repo"),
        "task_repo_path": state.get("task_repo_path"),
        "requirement_path": state.get("requirement_path"),
        "generated_files": state.get("generated_files") or [],
        "needs_e2e": bool(state.get("needs_e2e")),
        "test_commands": state.get("test_commands") or [],
        "exit_code": state.get("exit_code"),
        "duration_ms": state.get("duration_ms", 0),
        "stdout_tail": state.get("stdout_tail", ""),
        "stderr_tail": state.get("stderr_tail", ""),
        "case_results": state.get("case_results") or [],
        "warnings": state.get("warnings") or [],
        "errors": state.get("errors") or [],
        "environment_error_code": state.get("environment_error_code", ""),
        "validation_error_code": state.get("validation_error_code", ""),
        "validation_issues": state.get("validation_issues") or [],
        "toolchain_probe": state.get("toolchain_probe") or {},
        "allow_pm_fallback": _allow_pm_fallback(),
        "report_path": str(report_path),
        "result_json_path": str(result_path),
        "log_path": str(log_path) if log_path.exists() else "",
    }

    write_json(result_path, payload)
    state["result_json_path"] = str(result_path)
    state["report_path"] = str(report_path)
    state["log_path"] = str(log_path)
    return state


def fail_fast_errors(state: CodeTestState) -> CodeTestState:
    if not state.get("errors"):
        return state
    state.setdefault("status", "failed")
    state.setdefault("summary", "; ".join(state.get("errors") or []))
    state.setdefault("generated_files", [])
    state.setdefault("warnings", state.get("warnings") or [])
    tid_ff = state.get("task_id") or "task"
    output_dir = Path(state["output_dir"]).resolve() / tid_ff
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "code_test_result.json"
    write_json(
        str(result_path),
        {
            "task_id": tid_ff,
            "status": "failed",
            "summary": state.get("summary", ""),
            "local_only": bool(state.get("local_only")),
            "errors": state.get("errors"),
            "warnings": state.get("warnings") or [],
            "result_json_path": str(result_path.resolve()),
        },
    )
    state["result_json_path"] = str(result_path.resolve())
    return state
