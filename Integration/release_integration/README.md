# release_integration

This package implements the `Integration` stage. Its public stage ID is `integration`, and the root-level FastAPI/orchestration import is:

```python
from Integration.release_integration.stage import run_stage
```

If the caller is not running from the repository root, add `E:\DeliveraX` to `PYTHONPATH` first because `stage.py` depends on the root-level `stage_contracts` package.

Recommended graph:

```text
load_prevalidated_changes
  -> verify_test_and_review_results
  -> resolve_solution_workspace_repo
  -> create_integration_worktree
  -> apply_reviewed_diff
  -> verify_integrated_diff
  -> generate_delivery_summary
  -> package_merge_ready_output
```

Testing and code review are upstream stages. This agent only consumes their passed/approved results and must not rerun tests or redo review.

Deterministic nodes should own workspace resolution, Git worktree creation, patch application, and final diff generation. AI nodes should only generate delivery summaries and PR body text from already computed facts.

LLM summary generation is optional by default:

- configured API key: generate `change_summary.md` and `github_pr_body.md` with LLM
- no API key: fall back to deterministic templates
- `--require-llm`: fail instead of falling back
- `--no-llm`: force deterministic templates

Generated delivery documents are format-checked after generation. Required headings are:

- `change_summary.md`: `# Delivery Integration Summary`, `## Overview`, `## Upstream Results`, `## Integrated Files`, `## Diff Statistics`, `## Output Artifacts`
- `github_pr_body.md`: `## Change Summary`, `## Upstream Validation`, `## Changed Files`, `## Integration Metadata`

Provider-neutral OpenAI-compatible environment variables are preferred:

```text
DELIVERY_INTEGRATION_LLM_API_KEY=your_api_key
DELIVERY_INTEGRATION_LLM_BASE_URL=https://your-openai-compatible-endpoint
DELIVERY_INTEGRATION_LLM_MODEL=your-model
```

No provider URL is hardcoded. DeepSeek-compatible usage is just one configuration:

```text
DELIVERY_INTEGRATION_LLM_API_KEY=your_deepseek_api_key
DELIVERY_INTEGRATION_LLM_BASE_URL=https://api.deepseek.com
DELIVERY_INTEGRATION_LLM_MODEL=deepseek-chat
```
