from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

from agents.code_testing import nodes


def _write_checkbox_html(path: Path) -> None:
    path.write_text(
        """<!doctype html>
<html>
  <body>
    <div class="inbox">
      <div class="item"><input type="checkbox"><p>one</p></div>
      <div class="item"><input type="checkbox"><p>two</p></div>
    </div>
  </body>
</html>
""",
        encoding="utf-8",
    )


def _make_case_root() -> Path:
    root = Path.cwd() / "artifacts" / "__pytest_codetest_guardrails" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_compute_static_html_facts_sets_checkbox_scenario() -> None:
    root = _make_case_root()
    try:
        _write_checkbox_html(root / "index-START.html")
        state = {
            "repo_archetype": "static_html",
            "task_repo_path": str(root),
            "warnings": [],
            "errors": [],
        }

        updated = nodes.compute_static_html_facts(state)

        assert updated.get("entry_html_path") == "index-START.html"
        assert updated.get("checkbox_count") == 2
        assert updated.get("scenario_type") == "checkbox_shift_range"
        facts = updated.get("static_html_facts") or {}
        assert facts.get("has_select") is False
        assert "inbox" in set(facts.get("classes") or [])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_post_validate_static_html_e2e_flags_selector_semantic_mismatch() -> None:
    root = _make_case_root()
    try:
        _write_checkbox_html(root / "index-START.html")
        e2e_dir = root / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        (e2e_dir / "bad.spec.ts").write_text(
        """import { test } from '@playwright/test';
test('bad', async ({ page }) => {
  await page.goto('index-START.html');
  await page.waitForSelector('.toolbar');
  await page.waitForSelector('#taskList');
  await page.selectOption('#filterStatus', 'todo');
});
""",
            encoding="utf-8",
        )
        state = {
            "repo_archetype": "static_html",
            "task_repo_path": str(root),
            "warnings": [],
            "errors": [],
            "local_only": True,
        }
        state = nodes.compute_static_html_facts(state)

        warnings = state["warnings"]
        nodes._post_validate_static_html_e2e(state, warnings)

        assert state.get("validation_error_code") == "TEST_GENERATION_MISMATCH"
        errors = state.get("errors") or []
        assert any("selector-semantic mismatch" in err for err in errors)
        assert any("checkbox_shift_range" in err for err in errors)
    finally:
        shutil.rmtree(root, ignore_errors=True)
