# ReqAnalysis Migration Map

本文档记录 `ReqAnalysis` 阶段当前源码结构，方便后续追溯早期 TypeScript 实现与 Python 阶段实现的关系。

| Legacy / Concept | Current Python |
| --- | --- |
| `requirement-agent/types.ts` | `requirement_analysis/models.py` |
| `requirement-agent/inputValidator.ts` | `requirement_analysis/input_validator.py` |
| `requirement-agent/boundaryValidator.ts` | `requirement_analysis/boundary_validator.py` |
| `requirement-agent/specValidator.ts` | `requirement_analysis/spec_validator.py` |
| `requirement-agent/prompts.ts` | `requirement_analysis/prompts.py` |
| `requirement-agent/markdownRenderer.ts` | `requirement_analysis/markdown_renderer.py` |
| `requirement-agent/requirementAgent.ts` | `requirement_analysis/runner.py` |
| `requirement-agent/deepseekLlmCall.ts` | `requirement_analysis/providers/deepseek.py` |
| stage contract adapter | `requirement_analysis/stage.py` |
| CLI entry | `run.py` |

## Current Contract

- Module directory: `ReqAnalysis`
- Python package: `requirement_analysis`
- Stage ID: `requirements`
- Standard API entry: `requirement_analysis.stage.run_stage`
- CLI entry: `python .\ReqAnalysis\run.py ...`

## Behavior Parity

- Input validation error codes remain `EMPTY_INPUT`, `INPUT_TOO_SHORT`, `NOT_FRONTEND_REQUIREMENT`.
- Boundary validation still returns `INPUT_BOUNDARY_VIOLATION`.
- Auto-fix exhaustion still returns `AUTO_FIX_FAILED`.
- Human-readable output remains Markdown PRD.
- Machine-readable output remains `RequirementSpec` JSON.
