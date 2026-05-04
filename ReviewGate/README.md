# ReviewGate

ReviewGate is the deterministic human-in-the-loop code review checkpoint stage for DeliveraX.

The stage entrypoint is:

```python
review_gate.stage.run_stage(request)
```

It consumes upstream `ArtifactRef` inputs, preferring:

- `code_changes`
- `codegen_result`
- `codegen_report`
- `code_test_result`
- `code_test_report`
- `technical_design`
- `requirement_prd` / `requirement_spec`

It does not call a real LLM. It reads the diff and test result artifacts, produces a machine review result, and returns `pending_approval` by default so a human can confirm before integration.

Set `options.requires_approval=false` or `options.auto_approve=true` to return `succeeded` for local demos and tests.

## Outputs

- `review_report.md` as `review_report`, role `display`
- `review_result.json` as `review_result`, role `machine`
- `feedback_review.md` as a compatibility handoff artifact
- standard `manifest.json`, `result.json`, `input.json`, `logs.txt`, and `human_output.md` via `write_stage_artifacts()`

`review_result.json` includes `verdict`, `summary`, `risks`, `checklist`, `upstream_artifacts`, `test_status`, `diff_stats`, and `requires_human_approval`.
