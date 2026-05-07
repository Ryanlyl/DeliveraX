from __future__ import annotations

from .llm import ChatLLM
from .markdown_io import make_output_path, parse_markdown_sections, read_markdown, read_template, write_markdown
from .format_validator import format_validation_report, validate_technical_design
from .prompts import SYSTEM_PROMPT, architecture_prompt, design_prompt, format_repair_prompt, impact_prompt, review_prompt
from .repo_context import build_repo_context, prepare_repository as fetch_repository
from .schemas import SolDesignState


def load_requirement(state: SolDesignState) -> SolDesignState:
    markdown = read_markdown(state["requirement_path"])
    state["requirement_markdown"] = markdown
    state["requirement_sections"] = parse_markdown_sections(markdown)
    return state


def prepare_repository(state: SolDesignState) -> SolDesignState:
    repo_fetch = fetch_repository(
        repo_url=state.get("repo_url"),
        repo_path=state.get("repo_path"),
        repo_ref=state.get("repo_ref"),
        workspace_dir=state.get("workspace_dir"),
        task_id=state.get("task_id"),
    )
    state["repo_fetch"] = repo_fetch
    state["repo_root"] = repo_fetch["repo_root"]
    return state


def scan_repository(state: SolDesignState) -> SolDesignState:
    context = build_repo_context(
        state["repo_root"],
        state["requirement_markdown"],
        max_context_files=state.get("max_context_files", 24),
        repo_fetch=state.get("repo_fetch"),
    )
    if state.get("repo_fetch", {}).get("resolved_ref"):
        context["repo_ref"] = state["repo_fetch"].get("resolved_ref")
    state["repo_context"] = context
    return state


def analyze_architecture(state: SolDesignState) -> SolDesignState:
    if state.get("local_only"):
        state["architecture_summary"] = _local_architecture_summary(state)
        return state

    llm = ChatLLM()
    if not llm.available:
        state["architecture_summary"] = _local_architecture_summary(state)
        state.setdefault("errors", []).append("LLM not configured; used local architecture summary fallback.")
        return state

    state["architecture_summary"] = llm.complete(
        system=SYSTEM_PROMPT,
        user=architecture_prompt(state["requirement_markdown"], state["repo_context"]),
    )
    return state


def analyze_impact(state: SolDesignState) -> SolDesignState:
    if state.get("local_only"):
        state["impact_analysis"] = _local_impact_analysis(state)
        return state

    llm = ChatLLM()
    if not llm.available:
        state["impact_analysis"] = _local_impact_analysis(state)
        state.setdefault("errors", []).append("LLM not configured; used local impact analysis fallback.")
        return state

    state["impact_analysis"] = llm.complete(
        system=SYSTEM_PROMPT,
        user=impact_prompt(
            state["requirement_markdown"],
            state["repo_context"],
            state["architecture_summary"],
        ),
    )
    return state


def plan_design(state: SolDesignState) -> SolDesignState:
    template = read_template(state["template_path"])
    if state.get("local_only"):
        state["technical_design"] = _local_design_draft(state, template)
        return state

    llm = ChatLLM()
    if not llm.available:
        state["technical_design"] = _local_design_draft(state, template)
        state.setdefault("errors", []).append("LLM not configured; used local design draft fallback.")
        return state

    state["technical_design"] = llm.complete(
        system=SYSTEM_PROMPT,
        user=design_prompt(
            requirement_markdown=state["requirement_markdown"],
            repo_context=state["repo_context"],
            architecture_summary=state["architecture_summary"],
            impact_analysis=state["impact_analysis"],
            template=template,
        ),
    )
    return state


def validate_format(state: SolDesignState) -> SolDesignState:
    result = validate_technical_design(state["technical_design"], state["repo_context"])
    state["format_validation"] = result
    state["format_repaired"] = False
    if result.get("passed"):
        return state

    if state.get("local_only"):
        state.setdefault("errors", []).append("Format validation failed in local-only mode.")
        return state

    llm = ChatLLM()
    if not llm.available:
        state.setdefault("errors", []).append("Format validation failed and LLM is not configured for repair.")
        return state

    template = read_template(state["template_path"])
    repaired_design = llm.complete(
        system=SYSTEM_PROMPT,
        user=format_repair_prompt(
            template=template,
            technical_design=state["technical_design"],
            validation_report=format_validation_report(result),
            repo_context=state["repo_context"],
        ),
    )
    if repaired_design.strip():
        state["technical_design"] = repaired_design.strip()
        state["format_repaired"] = True
        repaired_result = validate_technical_design(state["technical_design"], state["repo_context"])
        state["format_validation"] = repaired_result
        if not repaired_result.get("passed"):
            state.setdefault("errors", []).append("Format repair ran once but validation still failed.")
    return state


def review_design(state: SolDesignState) -> SolDesignState:
    if state.get("local_only"):
        state["review_notes"] = _local_review_notes()
    else:
        llm = ChatLLM()
        if llm.available:
            state["review_notes"] = llm.complete(
                system=SYSTEM_PROMPT,
                user=review_prompt(state["requirement_markdown"], state["technical_design"]),
            )
        else:
            state["review_notes"] = _local_review_notes()

    validation = state.get("format_validation")
    if validation and not validation.get("passed"):
        state.setdefault("errors", []).append(
            "Format validation did not pass. Check `format_validation` details in stage result."
        )
    return state


def write_output(state: SolDesignState) -> SolDesignState:
    output_path = make_output_path(state["output_dir"], state["requirement_path"])
    write_markdown(output_path, state["technical_design"])
    state["output_path"] = str(output_path)
    return state


def _local_architecture_summary(state: SolDesignState) -> str:
    context = state["repo_context"]
    files = "\n".join(f"- `{item['path']}`" for item in context.get("key_files", []))
    return f"""## Local Architecture Summary

- Repository: `{context.get('repo_name', '')}`
- Detected stack: `{context.get('detected_stack', {})}`
- Key files included in context:
{files}

This summary is generated in local-only or no-LLM mode. It is intended for smoke tests and API orchestration checks; production design runs should use an LLM-backed pass.
"""


def _local_impact_analysis(state: SolDesignState) -> str:
    context = state["repo_context"]
    candidates = context.get("candidate_files", [])[:40]
    files = "\n".join(f"- `{path}`" for path in candidates)
    return f"""## Local Impact Analysis

The following files may need human or LLM review:

{files}

Open questions:
- Which page or component is the exact entry point for the requirement?
- Is there an existing API/client/state pattern that should be reused?
- Which project test/build command should be used as the final validation gate?
"""


def _local_design_draft(state: SolDesignState, template: str) -> str:
    requirement_name = _infer_requirement_name(state)
    repo_name = state["repo_context"].get("repo_name", "")
    repo_ref = state["repo_context"].get("resolved_ref") or state.get("repo_ref") or "default branch / local path"
    commit_sha = state["repo_context"].get("commit_sha") or "not recorded"
    fetch_method = state["repo_context"].get("fetch_method") or "unknown"
    package_json_path = state["repo_context"].get("package_json_path") or "not found"
    repo_root = state.get("repo_root", "")
    return f"""# Technical Solution Design: {requirement_name}

> This document was generated by SolDesign local-only mode. It is suitable for smoke tests and as a placeholder draft; production runs should use the configured LLM.

---

## 0. Metadata

| Field | Value |
|---|---|
| Requirement | {requirement_name} |
| Target repository | {repo_name} |
| Repository ref | {repo_ref} |
| Commit SHA | {commit_sha} |
| Fetch method | {fetch_method} |
| package.json | {package_json_path} |
| Mode | local-only |
| Status | Draft |

---

## 1. Requirement Understanding

```markdown
{state['requirement_markdown'][:4000]}
```

---

## 2. Current Architecture

{state['architecture_summary']}

---

## 3. Impact Scope

{state['impact_analysis']}

---

## 4. Recommended Technical Approach

- Confirm the exact page, component, and data flow that map to the requirement.
- Reuse existing components, styles, state management, and request helpers.
- Keep changes scoped to the identified impact area.

---

## 5. File Change Plan

| File path | Action | Description | Confidence |
|---|---|---|---|
| TBD after LLM or human review | TBD | Local-only mode cannot reliably choose exact files | Low |

---

## 6. API Design

| API | Method | Request | Response | Notes |
|---|---|---|---|---|
| TBD | TBD | TBD | TBD | Confirm against existing API/client patterns |

---

## 7. Data And State Design

```ts
// Local-only mode cannot infer reliable project-specific types.
```

- State ownership, types, and boundary cases should be completed after reading the target files.

---

## 8. Implementation Steps

1. Read the structured requirement and this draft.
2. Locate the target page, component, API/client wrapper, and state files.
3. Implement only the scoped file changes.
4. Run the project validation command and record the result.

---

## 9. Test Plan

- Run existing type-check, lint, test, and build commands where available.
- Add checks for interaction, error, empty, and responsive states based on acceptance criteria.

---

## 10. Risks And Open Questions

- What is the exact target page or module path?
- Does the change require a new API, or can it consume existing data?
- What is the recommended validation command for this repository?

---

## 11. Implementation Contract

> **Local-only warning:** change_files is intentionally empty. In local-only mode the CodeGen stage will produce a valid empty diff and mark the stage as succeeded. For production runs with an LLM, change_files must be populated from the file change plan above.

```yaml
implementation_contract:
  objective: "{requirement_name}"
  repo_root: "{repo_root}"
  must_read_files: []
  change_files: []
  api_changes: []
  state_changes: []
  test_commands: []
  acceptance_checks: []
  constraints:
    - "Do not modify unrelated files."
    - "Prefer existing project patterns."
    - "Mark uncertainty instead of inventing missing paths."
  notes:
    - "local-only mode: change_files is empty by design"
    - "CodeGen will produce empty diff artifacts in local-only mode"
    - "For production use, configure LLM and re-run this stage"
```

---

## 12. Self Check

{_local_review_notes()}

<!-- Template reference retained for maintainers.

{template[:3000]}
-->
"""


def _local_review_notes() -> str:
    return """- Local-only mode produced a valid document skeleton.
- Deep semantic review was not performed.
- Configure LLM settings for production-grade file-level design, API design, and test planning."""


def _infer_requirement_name(state: SolDesignState) -> str:
    sections = state.get("requirement_sections", {})
    basic = sections.get("1. 基本信息") or sections.get("基本信息") or ""
    for line in basic.splitlines():
        if "需求名称" in line and "|" in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[1]:
                return cells[1]
    return "unnamed requirement"
