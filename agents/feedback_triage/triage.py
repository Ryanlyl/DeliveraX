from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _read_text(path: Path, max_chars: int = 200_000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(data) > max_chars:
        return data[:max_chars] + "\n...(truncated)..."
    return data


def _design_ambiguous(design_text: str) -> bool:
    if not design_text.strip():
        return False
    patterns = (
        r"待确认",
        r"未确认",
        r"请确认",
        r"选项\s*[ABCＡＢＣ]",
        r"Option\s*[ABC]\b",
        r"open\s*question",
    )
    return any(re.search(p, design_text, re.IGNORECASE) for p in patterns)


def _classify_failure(*, result: dict[str, Any], log_text: str, combined: str) -> tuple[str, str, str, list[str]]:
    """Return (failure_category, recommended_owner, recommended_action, reasons)."""
    status = str(result.get("status", "")).lower()
    summary = str(result.get("summary", ""))
    errors = list(result.get("errors") or [])

    if status in {"passed", "pass", "ok", "success", "test"}:
        return "success", "none", "none", ["CodeTest completed (including local-only smoke status 'test')."]

    reasons: list[str] = []

    # --- environment
    tests_executed = "Running " in combined and "tests" in combined
    env_markers = (
        "package manager not found",
        "Dependency install failed",
        "install timed out",
        "ERESOLVE",
        "ENOTFOUND",
        "EAI_AGAIN",
        "getaddrinfo",
        "playwright install skipped or failed",
        "command not found",
    )
    # If tests clearly executed, don't misroute as environment just because npm printed peer/ci markers earlier.
    if (not tests_executed) and any(m.lower() in (summary + log_text).lower() for m in env_markers):
        reasons.append("Matched environment/install markers in summary or log.")
        return "environment", "environment", "fix_environment", reasons
    if errors and any("copy" in e.lower() or "permission" in e.lower() for e in map(str, errors)):
        reasons.append("Framework errors suggest workspace/permission issues.")
        return "environment", "environment", "fix_environment", reasons

    # --- test design: click timed out (missing element / bad selector)—before generic expect heuristics
    if "locator.click: Test timeout" in combined or ".click(): Test timeout" in combined:
        reasons.append("Playwright click timed out waiting for a locator; element likely absent or non-interactive.")
        return "test_design", "codetest", "fix_tests", reasons

    # static HTML + Shift-range checkboxes: native toggle on Shift+same-node click is common; over-specified tests fail on toBeChecked
    if (
        result.get("repo_archetype") == "static_html"
        and "Shift" in combined
        and "toBeChecked" in combined
        and ("unexpected value" in combined or "Received: unchecked" in combined)
    ):
        reasons.append(
            "static_html Shift interaction: assertion mismatch often reflects native checkbox toggle vs test expectation."
        )
        return "test_design", "codetest", "fix_tests", reasons

    # --- test design: locator not found / missing element (more specific than generic expect mismatch)
    if "element(s) not found" in combined or "Locator: locator(" in combined and "element(s) not found" in combined:
        reasons.append("Locator could not resolve element(s); likely selector/test issue.")
        return "test_design", "codetest", "fix_tests", reasons

    # --- product code: stable Playwright assertions on state/value
    if "expect(" in combined and (
        ("toBeChecked" in combined or "not.toBeChecked" in combined)
        or ("Expected:" in combined and "Received:" in combined)
    ):
        reasons.append("Playwright expect() failed (state/value mismatch). Route to implementation fix.")
        return "product_code", "codegen", "fix_implementation", reasons

    # --- test design (navigation / locator / strict mode)
    if "ERR_FILE_NOT_FOUND" in combined or "net::ERR_FILE_NOT_FOUND" in combined:
        reasons.append("page.goto/file:// target missing; baseURL or path resolution is wrong (often __dirname vs cwd).")
        return "test_design", "codetest", "fix_tests", reasons

    if "strict mode violation" in combined:
        reasons.append("Playwright strict mode violation; tighten locators/tests.")
        return "test_design", "codetest", "fix_tests", reasons
    if "Target page, context or browser has been closed" in combined:
        reasons.append("Browser lifecycle issue; often flaky test setup.")
        return "test_design", "codetest", "fix_tests", reasons

    # --- spec ambiguous AFTER concrete failures ruled out
    design_path = result.get("design_path")
    if isinstance(design_path, str) and design_path.strip():
        dpath = Path(design_path)
        if dpath.is_file():
            dtext = _read_text(dpath, 120_000)
            if _design_ambiguous(dtext):
                reasons.append("Technical design still contains open choices / 待确认; clarify before re-gen.")
                return "spec_ambiguous", "solutiondesign", "clarify_design", reasons

    # --- generic assertion failure fallback
    if "expect(" in combined and "Error:" in combined:
        reasons.append("Test assertion failed; default route to implementation unless proven otherwise.")
        return "product_code", "codegen", "fix_implementation", reasons

    reasons.append("Heuristic fallback: route to CodeGen for human review.")
    return "unknown", "codegen", "fix_implementation", reasons


def _extract_failing_test_line(combined: str) -> str | None:
    m = re.search(r"e2e[\\/][^\s:]+\.spec\.ts:\d+:\d+", combined)
    if m:
        return m.group(0)
    m = re.search(r"\.spec\.(ts|js):\d+:\d+", combined)
    return m.group(0) if m else None


def _purge_stale_feedback_markdown(out: Path) -> None:
    for p in out.glob("feedback_to_*.md"):
        p.unlink(missing_ok=True)
    fp = out / "feedback_passed.md"
    if fp.is_file():
        fp.unlink()


def run_triage(*, result_path: Path, output_dir: Path | None = None) -> dict[str, Any]:
    result_path = result_path.resolve()
    payload: dict[str, Any] = json.loads(result_path.read_text(encoding="utf-8"))
    out = (output_dir or result_path.parent).resolve()

    log_path_str = payload.get("log_path") or str(out / "test_run.log")
    log_path = Path(log_path_str)
    log_text = _read_text(log_path) if log_path.is_file() else ""

    combined = "\n".join(
        [
            str(payload.get("summary", "")),
            str(payload.get("stdout_tail", "")),
            str(payload.get("stderr_tail", "")),
            log_text,
        ]
    )

    category, owner, action, reasons = _classify_failure(
        result=payload, log_text=log_text, combined=combined
    )

    failing_hint = _extract_failing_test_line(combined)

    triage: dict[str, Any] = {
        "schema_version": "1.0",
        "source_code_test_result": str(result_path),
        "task_id": payload.get("task_id", ""),
        "code_test_status": payload.get("status", ""),
        "failure_category": category,
        "recommended_owner": owner,
        "recommended_action": action,
        "reasons": reasons,
        "evidence_paths": _evidence_paths(payload, log_path),
        "failing_test_hint": failing_hint,
    }

    out.mkdir(parents=True, exist_ok=True)
    _purge_stale_feedback_markdown(out)

    (out / "triage_result.json").write_text(
        json.dumps(triage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Single primary feedback artifact
    if category == "success":
        (out / "feedback_passed.md").write_text(
            _markdown_passed(payload, triage), encoding="utf-8"
        )
    elif owner == "codetest":
        (out / "feedback_to_codetest.md").write_text(
            _markdown_codetest(payload, triage, combined), encoding="utf-8"
        )
    elif owner == "solutiondesign":
        (out / "feedback_to_solutiondesign.md").write_text(
            _markdown_solutiondesign(payload, triage), encoding="utf-8"
        )
    elif owner == "environment":
        (out / "feedback_to_environment.md").write_text(
            _markdown_environment(payload, triage, log_text), encoding="utf-8"
        )
    else:
        (out / "feedback_to_codegen.md").write_text(
            _markdown_codegen(payload, triage, combined), encoding="utf-8"
        )

    return triage


def _evidence_paths(payload: dict[str, Any], log_path: Path) -> list[str]:
    paths: list[str] = []
    for key in (
        "result_json_path",
        "log_path",
        "report_path",
        "design_path",
        "diff_path",
        "task_repo_path",
        "source_codegen_repo",
        "test_plan_path",
        "requirement_path",
    ):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            paths.append(v)
    if log_path.is_file():
        p = str(log_path.resolve())
        if p not in paths:
            paths.append(p)
    # de-dup preserve order
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _markdown_passed(payload: dict[str, Any], triage: dict[str, Any]) -> str:
    return f"""# Feedback: CodeTest passed

Task: `{payload.get("task_id", "")}`

No downstream fix routing required.

## Triage summary

```json
{json.dumps(triage, ensure_ascii=False, indent=2)}
```
"""


def _markdown_codegen(payload: dict[str, Any], triage: dict[str, Any], combined: str) -> str:
    excerpt = combined[-6000:] if len(combined) > 6000 else combined
    return f"""# Feedback to CodeGen (implementation fix)

## Routing
- **failure_category**: `{triage.get("failure_category")}`
- **recommended_action**: `{triage.get("recommended_action")}`
- **reasons**: {triage.get("reasons")}

## Evidence paths
{chr(10).join("- " + p for p in triage.get("evidence_paths", []))}

## Task context
- **task_id**: `{payload.get("task_id", "")}`
- **task_repo_path** (CodeTest copy): `{payload.get("task_repo_path", "")}`
- **source_codegen_repo**: `{payload.get("source_codegen_repo", "")}`
- **diff_path**: `{payload.get("diff_path", "")}`

## What to do
1. Open `diff_path` and the HTML/JS entry under `source_codegen_repo` (or regenerate diff).
2. Reproduce using the failing Playwright case (see log excerpt below).
3. Adjust implementation so runtime behavior matches the agreed UX in **design_path** / **requirement_path**.
4. Re-run CodeTest for the same `task_id` or a new task id.

## Suggested fix patterns (Shift + checkbox demos)
- If tests expect **no range selection without an anchor**, guard with `lastChecked` before applying Shift-range logic, e.g. only run when `e.shiftKey && lastChecked`.
- If product wants **option B** (range matches clicked row state), set all in-range `checked` to `this.checked` instead of always `true`.

## Log / output excerpt
```text
{excerpt}
```
"""


def _markdown_codetest(payload: dict[str, Any], triage: dict[str, Any], combined: str) -> str:
    excerpt = combined[-6000:] if len(combined) > 6000 else combined
    return f"""# Feedback to CodeTest (test generation / selectors)

## Routing
- **failure_category**: `{triage.get("failure_category")}`
- **recommended_action**: `{triage.get("recommended_action")}`
- **reasons**: {triage.get("reasons")}

## Evidence paths
{chr(10).join("- " + p for p in triage.get("evidence_paths", []))}

## What to do
1. Inspect generated spec under `task_repo_path` / `e2e/`.
2. Fix unstable selectors, wrong `nth()` indices, missing awaits, or incorrect setup (baseURL, entry HTML).
3. Prefer dynamic counts (`locator.count()`) for static HTML lists.
4. Re-run CodeTest.

## Log excerpt
```text
{excerpt}
```
"""


def _markdown_solutiondesign(payload: dict[str, Any], triage: dict[str, Any]) -> str:
    return f"""# Feedback to SolutionDesign (clarify design)

## Routing
- **failure_category**: `{triage.get("failure_category")}`
- **recommended_action**: `{triage.get("recommended_action")}`
- **reasons**: {triage.get("reasons")}

## Evidence paths
{chr(10).join("- " + p for p in triage.get("evidence_paths", []))}

## What to do
1. Open `design_path` and remove ambiguous “选项 A/B/C / 待确认” for interaction semantics.
2. Write **one** explicit UX rule set (especially Shift behavior: anchor, same-row Shift, first-click Shift).
3. Regenerate technical design artifact, then re-run CodeGen + CodeTest.
"""


def _markdown_environment(payload: dict[str, Any], triage: dict[str, Any], log_text: str) -> str:
    excerpt = log_text[-8000:] if len(log_text) > 8000 else log_text
    return f"""# Feedback: environment / toolchain

## Routing
- **failure_category**: `{triage.get("failure_category")}`
- **recommended_action**: `{triage.get("recommended_action")}`
- **reasons**: {triage.get("reasons")}

## Evidence paths
{chr(10).join("- " + p for p in triage.get("evidence_paths", []))}

## What to check
- Node/npm on PATH / `CODETEST_NODE_BIN_DIR`
- Network access for `npm install` / browser downloads (`playwright install`)
- Permissions on `CodeTest/.workspace` directories

## Log excerpt
```text
{excerpt}
```
"""
