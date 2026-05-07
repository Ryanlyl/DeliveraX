from __future__ import annotations

import json

TEST_PLAN_SYSTEM = """You are a senior test architect. Output ONE JSON object only, no markdown fences.
Schema:
{
  "schema_version": "1.0",
  "summary": "string",
  "layers": [
    {
      "type": "unit|component|e2e",
      "rationale": "string",
      "cases": [{"id": "string", "title": "string", "target_paths": ["rel/path"], "assertion_focus": "string"}]
    }
  ],
  "environment": {"needs_playwright": false, "playwright_project": "", "suggested_install_hooks": []},
  "notes": []
}
Choose layers based on repo: static HTML favors e2e; React+Vite favors unit/component + optional e2e."""


TEST_GEN_SYSTEM = """You are a senior frontend engineer. Output ONE JSON object only, no markdown fences.
Schema:
{"schema_version":"1.0","files":[{"path":"relative/path","content":"full source","case_ids":[],"kind":"test|config"}],"notes":[]}

For STATIC HTML repos (no package.json before tests): you MUST include a minimal package.json with devDependencies
(@playwright/test, typescript optional), scripts "test":"playwright test", and playwright.config.* plus e2e/*.spec.ts
so that `npm install` + `npm test` can run Playwright against the existing HTML entry (e.g. index-START.html).

Playwright + file:// (Windows-safe, REQUIRED for static HTML):
- `npm test` uses cwd = repo root (the folder with package.json).
- In playwright.config.ts set `use.baseURL` to the repo root file URL, for example:
  `baseURL: 'file:///' + process.cwd().replace(/\\\\/g, '/') + '/'`
  so `await page.goto('index-START.html')` resolves to `<repo>/index-START.html`.
- Do NOT use `__dirname` for file:// baseURL unless you are certain it resolves to the repo root; some runners resolve TS config `__dirname` to a parent directory and break with net::ERR_FILE_NOT_FOUND.

Vanilla checkbox / Shift-range pages (NO framework):
- SHIFT + click on the **same** checkbox that is already checked: the browser toggles it OFF before the click handler runs (`this.checked === false`). Handlers that copy `this.checked` along a range will often **uncheck** that endpoint (and may leave earlier boxes checked). Never assert the clicked index stays `toBeChecked()` after Shift+same-index; do not write tests like "does nothing". Prefer: only `pageerror` / empty error array, or assert the clicked box becomes **unchecked**, or avoid this scenario entirely.
- A second Shift+click on the **same** row that **ended** the previous range is NOT "preserve range"—the toggled-off state propagates per script; do not require inner range items to all stay checked unless you derived it from the actual script.
- "Click header / neutral area outside rows": NEVER assume `<h1>`, `<thead>`, etc. unless you see them in the entry HTML. Prefer `page.locator('.inbox').click({ position: { x: 2, y: 2 }, force: true })` or `.item p` labels that visibly exist beside checkboxes—not invented headings.

For NODE/React repos: generate Vitest + Testing Library tests as appropriate. Paths must stay inside the repo root."""


def test_plan_prompt(
    *,
    design_excerpt: str,
    diff_excerpt: str,
    repo_archetype: str,
    repo_hint: str,
    entry_html_path: str | None = None,
    checkbox_count: int | None = None,
    scenario_type: str | None = None,
) -> str:
    static_hint = ""
    if repo_archetype == "static_html" and entry_html_path and checkbox_count and checkbox_count > 0:
        static_hint = (
            "\n\nStatic HTML facts:\n"
            f"- entry_html_path: {entry_html_path}\n"
            f"- checkbox_count: {checkbox_count}\n"
            f"- scenario_type: {scenario_type or 'generic_static_html'}\n"
            "Notes: `checkbox_count` is the number of `<input type=\"checkbox\">` elements in the entry HTML. "
            "Use it only as factual context; do NOT hardcode numeric indices in test logic."
        )
    return f"""Repository archetype: {repo_archetype}
Repository root: {repo_hint}
{static_hint}

Technical design (excerpt):
{design_excerpt}

Git diff (excerpt):
{diff_excerpt}

Produce test_plan JSON. If archetype is static_html, emphasize e2e layers and set environment.needs_playwright true."""


def test_files_prompt(
    *,
    test_plan: dict,
    design_excerpt: str,
    diff_excerpt: str,
    repo_archetype: str,
    repo_hint: str,
    entry_html_path: str | None = None,
    checkbox_count: int | None = None,
    scenario_type: str | None = None,
) -> str:
    plan_blob = json.dumps(test_plan, ensure_ascii=False, indent=2)[:24000]
    static_constraints = ""
    if repo_archetype == "static_html" and entry_html_path and checkbox_count and checkbox_count > 0:
        static_constraints = f"""

Static HTML facts (MUST FOLLOW):
- entry_html_path: {entry_html_path}
- checkbox_count: {checkbox_count} (counted from the real HTML)
- scenario_type: {scenario_type or 'generic_static_html'}

E2E test authoring constraints:
- playwright.config.ts MUST use `baseURL: 'file:///' + process.cwd().replace(/\\\\/g, '/') + '/'` (or equivalent) so file:// navigation targets the repo root, not a parent folder.
- NEVER hardcode checkbox count (no `for (i < 10)` or `for (i < {checkbox_count})`).
- ALWAYS query dynamically at runtime, e.g. `const n = await checkboxes.count();` then loop `for (let i = 0; i < n; i++)`.
- Any usage of `checkboxes.nth(i)` must guarantee `i < n`; do not reference out-of-range indices like `nth({checkbox_count})`.
- SHIFT + click same checkbox / same range endpoint: expect native **toggle off**; never `toBeChecked()` on that index afterward; no test titles implying "does nothing".
- Neutral clicks outside checkboxes must use selectors that appear in `{entry_html_path}` (inspect structure); otherwise use `.inbox` positional click on padding, never blind `h1`.
- NEVER use selectors that do not exist in `{entry_html_path}` (e.g. `.toolbar`, `#taskList`, `#filterStatus`) unless they are explicitly present in the HTML.
"""
    return f"""Repository archetype: {repo_archetype}
Repository root: {repo_hint}
{static_constraints}

Approved test plan (JSON):
{plan_blob}

Design (excerpt):
{design_excerpt[:8000]}

Diff (excerpt):
{diff_excerpt[:12000]}

Generate test_generation JSON with files[] implementing the plan. For static_html + Playwright, include
package.json, playwright.config, and e2e specs that open the local HTML file via file: or a minimal static server if needed."""


# Backward compatibility
SYSTEM_PROMPT = TEST_GEN_SYSTEM


def test_generation_prompt(
    *,
    design_excerpt: str,
    diff_excerpt: str,
    repo_hint: str,
) -> str:
    return f"""Repository hint: {repo_hint}
Design: {design_excerpt[:4000]}
Diff: {diff_excerpt[:8000]}
Generate files[] JSON for tests only (legacy single-shot)."""
