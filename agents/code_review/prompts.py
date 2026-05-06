from __future__ import annotations

DEFAULT_POLICY_EMBED = """\
Front-end baseline (DeliveraX CodeReview embedded policy — extend via --policy-pack):
- Prefer small, understandable changes; avoid duplicate logic without extraction.
- No secrets in repo (API keys, tokens); use env or placeholders.
- Avoid innerHTML / document.write / eval unless justified; beware XSS surfaces.
- Event handlers should match UX contracts (keyboard modifiers, accessibility).
- Prefer explicit tests for changed behavior when tests are supplied in context.

Review dimensions required in output categories:
correctness | security | convention | requirements_alignment\
"""

MERGE_FINAL_SYSTEM = """You are consolidating multiple partial code-review JSON fragments into ONE final JSON.
Output ONLY one JSON object, no markdown fences.
Rules:
- Deduplicate same finding; merge severities upward (keep higher severity).
- Preserve distinct files/locations.
- Produce valid JSON matching schema given in user message."""


def review_round_system(extra_policy: str) -> str:
    pol = DEFAULT_POLICY_EMBED
    if extra_policy.strip():
        pol = pol + "\n\nAdditional team policy:\n" + extra_policy.strip()
    return f"""You are a senior reviewer for a DeliveraX delivery pipeline.

{pol}

You MUST output ONLY one JSON object, no markdown code fences.

Schema fields (all required keys must exist — use arrays where specified):
{{
  "partial_issues": [
    {{
      "id": "string stable id CR-NNN",
      "severity": "blocker|major|minor|nit|question",
      "category": "correctness|security|convention|requirements_alignment|testability",
      "file": "path or empty",
      "line": null_or_number,
      "evidence": "short excerpt or hunk anchor",
      "fix_suggestion": "actionable suggestion"
    }}
  ],
  "partial_test_gaps": [
    {{ "summary": "string", "suggested_test": "string" }}
  ]
}}

For this round you ONLY see ONE chunk of unified diff (+ context). Populate partial_issues from THIS chunk only."""


FINAL_AGGREGATION_SYSTEM = """You are completing a DeliveraX code review. Output ONLY one JSON object, no markdown fences.

Schema:
{
  "summary": "1-6 sentences zh-CN or team language",
  "merge_recommendation": "approve|approve_with_nits|changes_requested|blocked",
  "issues": [ same shape as partial_issues but FINAL deduped list ],
  "test_gaps": [ { "summary": "", "suggested_test": "" } ]
}

Severity rules mapping to merge_recommendation (you propose; pipeline may normalize):
- any blocker → merge_recommendation should be blocked unless clearly false-positive (then downgrade with justification in evidence).
- major without blocker → changes_requested typical.
- only minor/nit/question → approve_with_nits acceptable.

IMPORTANT for DeliveryIntegration downstream:
- NEVER put approve_with_nits/changes_requested/blocked into a field named "status" inside this JSON; use merge_recommendation only.
"""


def finalize_status_note() -> str:
    return (
        "The pipeline will derive top-level `status` for gates: approved | changes_requested | rejected "
        "(`merge_recommendation` carries fine-grained agent opinion)."
    )
