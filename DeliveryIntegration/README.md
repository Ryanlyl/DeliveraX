# DeliveryIntegration

交付集成模块。它消费已经通过代码测试和代码评审的 CodeGen 变更结果，把 diff 集成到 `SolutionDesign/.workspace` 中对应仓库的独立 worktree，生成可合并交付物。

本模块不重新拉仓库、不重新测试、不重新评审、不自动 push GitHub。

## 逻辑流程

```text
codegen_result.json
  -> 校验上游测试/评审状态
  -> 定位 SolutionDesign workspace repo
  -> 基于 source_commit_sha 创建 delivery worktree
  -> 应用已评审 diff
  -> 生成本地集成 commit
  -> 生成 final diff / 中文摘要 / PR 描述 / result JSON
```

核心输入来自 `CodeGen`：

- `source_repo_root`：`SolutionDesign/.workspace/repos/<repo>`
- `source_commit_sha`：CodeGen 生成 diff 时的基线 commit
- `diff_path`：待集成的 `code_changes.diff`
- `changed_files`：计划变更文件

上游代码测试和代码评审尚未落库时，默认按阶段契约假定：

- 测试状态：`passed`
- 评审状态：`approved`

如果已经有上游结果文件，可通过 CLI 显式传入。

## 输出产物

```text
DeliveryIntegration/Output/<task-id>/
|-- final_changes.diff
|-- change_summary.md
|-- github_pr_body.md
`-- delivery_integration_result.json
```

运行时 worktree 位于：

```text
DeliveryIntegration/.workspace/tasks/<task-id>/repo
```

这些运行时产物默认被 `.gitignore` 忽略，仓库只保留模块代码、模板、示例输入和占位文件。

## LLM 配置

摘要和 PR 描述支持 OpenAI-compatible LLM。代码不内置任何 provider URL，必须显式配置。

```powershell
$env:DELIVERY_INTEGRATION_LLM_API_KEY="your_api_key"
$env:DELIVERY_INTEGRATION_LLM_BASE_URL="https://your-openai-compatible-endpoint"
$env:DELIVERY_INTEGRATION_LLM_MODEL="your-model"
```

DeepSeek 示例：

```powershell
$env:DELIVERY_INTEGRATION_LLM_API_KEY="your_deepseek_api_key"
$env:DELIVERY_INTEGRATION_LLM_BASE_URL="https://api.deepseek.com"
$env:DELIVERY_INTEGRATION_LLM_MODEL="deepseek-chat"
```

可选模式：

- `--require-llm`：必须使用 LLM，配置缺失或输出格式不合格会失败
- `--no-llm`：禁用 LLM，使用中文模板生成摘要

LLM 输出会做格式检查：

- `change_summary.md` 必须包含中文章节：`# 交付集成摘要`、`## 概览`、`## 上游结果`、`## 集成文件`、`## Diff 统计`、`## 输出产物`
- `github_pr_body.md` 必须包含中文章节：`## 变更摘要`、`## 上游验证`、`## 变更文件`、`## 集成元数据`

## 使用方法

安装依赖：

```powershell
cd E:\DeliveraX
python -m pip install -r .\DeliveryIntegration\requirements.txt
```

标准运行：

```powershell
python .\DeliveryIntegration\run.py `
  --codegen-result .\CodeGen\Output\todolist-manual-test-2\codegen_result.json `
  --task-id delivery-todolist-manual-test-2 `
  --require-llm
```

重复运行同一个任务时覆盖旧 workspace：

```powershell
python .\DeliveryIntegration\run.py `
  --codegen-result .\CodeGen\Output\todolist-manual-test-2\codegen_result.json `
  --task-id delivery-todolist-manual-test-2 `
  --require-llm `
  --force
```

离线验证：

```powershell
python .\DeliveryIntegration\run.py `
  --codegen-result .\CodeGen\Output\todolist-manual-test-2\codegen_result.json `
  --task-id delivery-todolist-manual-test-2 `
  --force `
  --no-llm
```

显式传入上游测试/评审结果：

```powershell
python .\DeliveryIntegration\run.py `
  --codegen-result .\CodeGen\Output\task-001\codegen_result.json `
  --test-result .\CodeTest\Output\task-001\code_test_result.json `
  --review-result .\CodeReview\Output\task-001\code_review_result.json `
  --task-id delivery-001
```

结果字段中：

- `merge_ready: true` 表示本地交付集成产物已生成
- `pushed: false` 表示本模块尚未自动推送 GitHub
- `summary_mode` 表示摘要来源：`llm`、`template`、`template_no_llm_config`、`template_llm_failed`
