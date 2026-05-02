from __future__ import annotations

from .repo_context import format_repo_context_for_prompt
from .schemas import RepoContext


SYSTEM_PROMPT = """You are the SolDesign stage assistant for DeliveraX.
Your job is to convert a structured requirement and real repository context into an executable technical design.

Rules:
- Base every file path and architecture claim on the provided repository context.
- Do not invent files. If context is insufficient, add an explicit open question.
- Output Markdown only.
- The document must serve both human reviewers and the downstream CodeGen stage.
- Keep file changes, API design, data/state design, and test plan structured.
"""


def architecture_prompt(requirement_markdown: str, repo_context: RepoContext) -> str:
    return f"""Analyze the existing repository architecture and identify areas that may relate to the requirement.

## Structured Requirement

```markdown
{requirement_markdown}
```

## Repository Context

{format_repo_context_for_prompt(repo_context)}

Return:
1. Technology stack and project structure.
2. Key entry points for pages, components, state, API clients, and routing.
3. Existing implementations that can be reused.
4. Observations that help the later impact analysis.
"""


def impact_prompt(requirement_markdown: str, repo_context: RepoContext, architecture_summary: str) -> str:
    return f"""Analyze the likely impact scope using the requirement, architecture summary, and repository context.

## Structured Requirement

```markdown
{requirement_markdown}
```

## Architecture Summary

```markdown
{architecture_summary}
```

## Repository Context

{format_repo_context_for_prompt(repo_context)}

Return:
1. Files that may need to be added, modified, or removed.
2. Affected pages, components, state, API, routing, styles, and tests.
3. Possible behavioral regressions.
4. Open questions that require human confirmation.
"""


def design_prompt(
    *,
    requirement_markdown: str,
    repo_context: RepoContext,
    architecture_summary: str,
    impact_analysis: str,
    template: str,
) -> str:
    return f"""Generate a complete technical solution design using the template exactly.

## Output Template

```markdown
{template}
```

## Structured Requirement

```markdown
{requirement_markdown}
```

## Architecture Summary

```markdown
{architecture_summary}
```

## Impact Analysis

```markdown
{impact_analysis}
```

## Repository Context

{format_repo_context_for_prompt(repo_context)}

Return the final Markdown document directly. Do not wrap it in a code fence.
"""


def review_prompt(requirement_markdown: str, technical_design: str) -> str:
    return f"""Review whether the technical design satisfies the structured requirement and is executable.

## Structured Requirement

```markdown
{requirement_markdown}
```

## Technical Design

```markdown
{technical_design}
```

Return a concise review covering:
- Whether the requirement goal is covered.
- Whether acceptance criteria are covered.
- Whether any file, API, or test instructions are unclear.
- Open questions that should be added to the design.
"""


def format_repair_prompt(
    *,
    template: str,
    technical_design: str,
    validation_report: str,
    repo_context: RepoContext,
) -> str:
    candidate_files = "\n".join(f"- `{path}`" for path in repo_context.get("candidate_files", [])[:300])
    return f"""Repair the technical design format and return the complete corrected Markdown.

Repair rules:
- Include all level-one and level-two headings from the template.
- `## 5. File Change Plan` must contain a Markdown table.
- `## 6. API Design` must exist and state whether APIs are changed.
- `## 11. Implementation Contract` must contain a fenced YAML block with `implementation_contract:`.
- Modify/Update/Delete paths must come from the scanned repository file list.
- If a path is not in the repository list but should be new, mark the action as Add.
- Preserve valid technical content. Do not invent unsupported file paths.
- Do not wrap the output in an extra code fence.

## Output Template

```markdown
{template}
```

## Validation Report

{validation_report}

## Scanned Repository Files

{candidate_files}

## Design To Repair

```markdown
{technical_design}
```
"""
