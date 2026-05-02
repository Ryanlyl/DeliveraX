# DeliveraX Stage Contract

本文档定义 FastAPI 编排层与各后端阶段之间的稳定契约。阶段内部可以继续演进，但对外入口、状态和产物格式应保持兼容。

## 命名体系

| 模块目录 | 内部包名 | 阶段 ID | 说明 |
| --- | --- | --- | --- |
| `ReqAnalysis` | `requirement_analysis` | `requirements` | 需求分析与 PRD 生成 |
| `SolDesign` | `solution_design` | `solution` | 技术方案设计 |
| `CodeGen` | `code_generation` | `code` | 代码生成与 diff 输出 |
| `CodeTest` | 待定 | `test` | 代码测试占位阶段 |
| `ReviewGate` | 待定 | `review` | 人工 / 自动评审门禁占位阶段 |
| `Integration` | `release_integration` | `integration` | 交付集成与 PR 物料生成 |

## 统一入口

每个可执行阶段暴露同名入口：

```python
def run_stage(request: StageRunRequest) -> StageRunResult:
    ...
```

`ReqAnalysis` 当前入口是 async：

```python
async def run_stage(request: StageRunRequest) -> StageRunResult:
    ...
```

统一请求字段：

```text
pipeline_id
stage_id
run_id
input_artifacts
output_dir
repo_path
options
```

## 统一状态

阶段状态只使用以下枚举：

```text
queued
running
succeeded
failed
pending_approval
rejected
cancelled
skipped
```

前端可以把这些状态映射为中文展示，但不要再保存另一套阶段状态语义。

## 标准产物目录

API 编排层应把 `StageRunRequest.output_dir` 指向根级 `artifacts/` 目录。每个阶段标准输出为：

```text
artifacts/<pipeline_id>/<stage_id>/
  input.json
  result.json
  manifest.json
  logs.txt
  human_output.md
```

约定：

- `input.json`：该阶段收到的标准请求或关键输入。
- `result.json`：完整 `StageRunResult`。
- `manifest.json`：API 和前端快速读取的轻量索引。
- `logs.txt`：阶段日志。
- `human_output.md`：人类可读主产物。

阶段可以额外输出专有文件，例如：

- `requirement_spec.json`
- `requirement_prd.md`
- `technical_design_*.md`
- `code_changes.diff`
- `codegen_result.json`
- `final_changes.diff`
- `github_pr_body.md`

这些额外产物必须通过 `StageRunResult.output_artifacts` 暴露，API 层不应猜文件名。

## 扩展规则

- 模块内部可以替换 LLM、修改 prompt、增加校验、拆分子步骤，只要 `run_stage()` 契约不变。
- 新增字段优先放入 `StageRunRequest.options` 或 `StageRunResult.data`，避免破坏前端和 API 的外层结构。
- 阶段之间只传 `ArtifactRef`，不要传内部临时路径或模块私有状态。
- 人工审批必须由编排层保存为 `pending_approval` / `rejected` / `succeeded`，不能只放在前端本地状态。
