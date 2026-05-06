# CodeReview

LLM-assisted code review stage: consumes **technical design**, **code diff**, and **`code_test_result.json`**, emits **`CodeReview/Output/<task-id>/code_review_result.json`** (plus optional Markdown reports).

Aligned with DeliveraX `findings.md` CodeReview Agent v1 freeze.

## Prerequisites

```bash
python -m pip install -r requirements.txt
```

## Environment (same family as CodeTest / CodeGen)

Lookup order **`CODEREVIEW_*` → `CODETEST_*` → `CODEGEN_*` → `DEEPSEEK_*` / `OPENAI_API_KEY`** (see `agent/llm.py`).

- `CODEREVIEW_LLM_MAX_CALLS` — rounds budget (chunks + final merge each count as **1**). Default inherits `CODETEST_LLM_MAX_CALLS` rounded to **≥12** chunks default.
- `CODEREVIEW_DIFF_CHUNK_LINES` — max diff lines per LLM chunk (default **350**).

## CLI

Required: **`--test-result`**. Provide **`--design` + `--diff`**, **or** only **`--codegen-result`** to resolve missing paths.

```bash
cd CodeReview
python run.py --test-result ..\CodeTest\Output\<task>\code_test_result.json ^
  --design ..\SolutionDesign\Output\technical_design_*.md ^
  --diff ..\CodeGen\Output\<task>\code_changes.diff
```

Optional:

- `--requirement …\requirement_spec.json`
- `--codegen-result` — fill paths + mismatch **warnings**
- `--policy-pack policy.md`
- `--local-only` — no LLM, `status: "test"`
- `--max-llm-calls N`
- `--output-dir …` — default `./Output`

Exit code: **`2`** if any issue has **`severity: blocker`**; otherwise **`0`**. **`merge_recommendation: blocked`** without a blocker issue does **not** force exit **2**.

## Outputs

| File | Purpose |
|------|---------|
| `code_review_result.json` | Machine source; **`status`** is DI-compatible (`approved` / `changes_requested` / `rejected`). Fine-grained agent opinion → **`merge_recommendation`** |
| `code_review_report.md` | Human-readable |
| `feedback_review.md` | Feed into `--repair-feedback` style loops |
