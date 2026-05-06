from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, cast

from .io_utils import (
    read_json,
    read_text,
    write_json,
    write_text,
    resolve_path_maybe_relative,
    apply_unified_diff_to_repo,
)
from .prompts import (
    TEST_GEN_SYSTEM,
    TEST_PLAN_SYSTEM,
    test_files_prompt,
    test_plan_prompt,
)
from .schemas import CodeTestState, TestCaseResult
from .workspace import copy_task_repository, safe_repo_path


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
    warnings = list(state.get("warnings") or [])
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

    diff_path = state.get("diff_path")
    if diff_path:
        try:
            changed = apply_unified_diff_to_repo(diff_path=diff_path, repo_root=dest)
            if changed:
                warnings.append(f"Applied code changes diff to test repo: {', '.join(changed)}")
        except Exception as exc:
            state.setdefault("errors", []).append(f"Failed to apply diff before tests: {exc}")
            return state

    state["task_repo_path"] = str(dest.resolve())
    state["task_workspace_dir"] = str(dest.parent)
    state["warnings"] = warnings
    return state


def detect_archetype(state: CodeTestState) -> CodeTestState:
    if state.get("errors") or not state.get("task_repo_path"):
        return state
    repo = Path(state["task_repo_path"])
    has_pkg = (repo / "package.json").is_file()
    state["repo_archetype"] = "nodejs_sp" if has_pkg else "static_html"
    state.setdefault("warnings", []).append(f"Repository archetype: {state['repo_archetype']}")
    return state


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

    # Count <input type="checkbox"> occurrences (case-insensitive, tolerant to spacing/attributes)
    pattern = re.compile(r"<input\b[^>]*\btype\s*=\s*[\"']?\s*checkbox\s*[\"']?[^>]*>", re.IGNORECASE)
    count = len(pattern.findall(html))
    if count > 0:
        state["entry_html_path"] = entry.name
        state["checkbox_count"] = int(count)
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
    checkbox_count = state.get("checkbox_count")
    entry_html = state.get("entry_html_path")
    if not checkbox_count or checkbox_count <= 0 or not entry_html:
        return
    repo = Path(state["task_repo_path"])
    # Only validate if an E2E spec was generated
    spec_paths = [p for p in (repo / "e2e").glob("*.spec.ts")] if (repo / "e2e").is_dir() else []
    if not spec_paths:
        return
    max_index = checkbox_count - 1
    hardcoded_loops = re.compile(r"for\s*\(\s*let\s+\w+\s*=\s*0\s*;\s*\w+\s*<\s*(\d+)\s*;", re.IGNORECASE)
    nth_calls = re.compile(r"\.nth\(\s*(\d+)\s*\)")

    issues: list[str] = []
    for spec in spec_paths:
        text = spec.read_text(encoding="utf-8", errors="replace")
        for m in hardcoded_loops.finditer(text):
            issues.append(f"{spec.as_posix()}: hardcoded loop upper bound {m.group(1)}; use checkboxes.count()")
        for m in nth_calls.finditer(text):
            idx = int(m.group(1))
            if idx > max_index:
                issues.append(f"{spec.as_posix()}: nth({idx}) out of range for checkbox_count={checkbox_count} (max {max_index})")

    if issues:
        warnings.append("Generated E2E tests violate static_html guardrails; attempting one automatic fix.")
        if state.get("local_only"):
            state.setdefault("errors", []).extend(issues)
            return
        from .llm import ChatLLM

        llm = ChatLLM()
        if not llm.available:
            state.setdefault("errors", []).extend(issues)
            return
        if int(state.get("llm_calls") or 0) >= int(state.get("max_llm_calls") or 0):
            state.setdefault("errors", []).extend(issues)
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


def _node_bin_dir() -> str | None:
    """Directory containing node.exe (so npm.cmd / npx.cmd resolve on Windows)."""
    raw = (os.getenv("CODETEST_NODE_BIN_DIR") or "").strip()
    if raw and Path(raw).is_dir():
        return str(Path(raw).resolve())
    node = shutil.which("node.exe") or shutil.which("node")
    if not node:
        return None
    return str(Path(node).resolve().parent)


def _subprocess_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    if extra:
        env.update(extra)
    bindir = _node_bin_dir()
    if bindir:
        sep = os.pathsep
        path = env.get("PATH", "")
        prefix = bindir + sep
        if not path.startswith(prefix):
            env["PATH"] = prefix + path
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


def _install_timeout_seconds() -> float:
    raw = os.getenv("CODETEST_INSTALL_TIMEOUT_SECONDS", "900")
    try:
        return float(raw)
    except ValueError:
        return 900.0


def _install_dependencies(repo: Path, pm: list[str], log_lines: list[str]) -> bool:
    if pm == ["pnpm", "exec"]:
        cmd = _resolve_cmd(["pnpm", "install", "--frozen-lockfile"])
    elif pm == ["yarn"]:
        cmd = _resolve_cmd(["yarn", "install", "--frozen-lockfile"])
    else:
        if (repo / "package-lock.json").is_file():
            cmd = ["npm", "ci"]
        else:
            cmd = ["npm", "install"]
    cmd = _resolve_cmd(cmd)
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
            env=_subprocess_env({}),
        )
        log_lines.append(proc.stdout or "")
        log_lines.append(proc.stderr or "")
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        log_lines.append("install timed out")
        return False
    except FileNotFoundError:
        log_lines.append("package manager not found on PATH")
        return False


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
    cmd = _resolve_cmd(["npx", "playwright", "install", "--with-deps"])
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
            env=_subprocess_env({"CI": "1"}),
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

    if not _install_dependencies(repo, pm, log_lines):
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
                env=_subprocess_env({"CI": "true"}),
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
        base_test = ["npm", "test", "--"]

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
                e2e_cmd = ["npm", "run", "test:e2e"]
        elif (repo / "playwright.config.ts").is_file() or (repo / "playwright.config.mjs").is_file() or (repo / "playwright.config.js").is_file():
            e2e_cmd = ["npx", "playwright", "test"]
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
