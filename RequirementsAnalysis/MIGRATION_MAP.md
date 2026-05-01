# TS to Python Migration Map

本文件用于 GitHub PR 审阅，说明 TypeScript 旧实现与 Python 新实现的对应关系。

| TypeScript | Python |
| --- | --- |
| `requirement-agent/types.ts` | `agent/models.py` |
| `requirement-agent/inputValidator.ts` | `agent/input_validator.py` |
| `requirement-agent/boundaryValidator.ts` | `agent/boundary_validator.py` |
| `requirement-agent/specValidator.ts` | `agent/spec_validator.py` |
| `requirement-agent/prompts.ts` | `agent/prompts.py` |
| `requirement-agent/markdownRenderer.ts` | `agent/markdown_renderer.py` |
| `requirement-agent/requirementAgent.ts` | `agent/runner.py` |
| `requirement-agent/deepseekLlmCall.ts` | `agent/providers/deepseek.py` |
| `requirement-agent/requirementAgent.test.ts` | `tests/test_requirement_agent.py` |
| `requirement-agent/example.ts` | `run.py` |

## 行为等价清单

- 输入校验错误码：`EMPTY_INPUT`、`INPUT_TOO_SHORT`、`NOT_FRONTEND_REQUIREMENT`
- 输入越界错误码：`INPUT_BOUNDARY_VIOLATION`
- 自动修复失败错误码：`AUTO_FIX_FAILED`
- Markdown 章节结构保持 `1` 到 `12` 章一致
- DeepSeek 调用模型参数保持默认值一致（`deepseek-v4-flash`，`temperature=0.2`）
