# CodeGen

`CodeGen` 是 DeliveraX 的代码生成阶段：输入 `SolutionDesign` 产出的技术方案 Markdown，复用上一阶段缓存仓库，创建任务级代码副本，在副本中落地代码修改，并输出 GitHub 标准 `git diff`。

## Architecture

```text
technical_design_*.md
  -> load_design
  -> parse implementation_contract
  -> resolve SolutionDesign cached repo
  -> verify base commit
  -> create CodeGen task repo
  -> load file context
  -> generate file changes with LLM
  -> apply changes to task repo
  -> git diff --no-ext-diff --unified=3
  -> write diff / report / result.json
```

关键约束：

- 不重新拉取仓库，默认复用 `SolutionDesign/.workspace/repos/...`
- 不直接修改 SolutionDesign 缓存仓库
- 所有代码修改发生在 `CodeGen/.workspace/tasks/<task-id>/repo`
- 下游阶段读取 `codegen_result.json` 中的 `codegen_repo_path`

## Workspace Model

输入缓存仓库：

```text
SolutionDesign/.workspace/repos/<repo-cache-name>
```

CodeGen 任务仓库：

```text
CodeGen/.workspace/tasks/<task-id>/repo
```

如果缓存仓库是 Git 仓库，使用 detached worktree：

```text
git worktree add --detach <task-repo> <base-commit>
```

如果不是 Git 仓库，降级为 copy + synthetic Git base commit。

## Main Files

```text
CodeGen/
|-- agent/
|   |-- graph.py          # LangGraph 编排
|   |-- nodes.py          # pipeline 节点
|   |-- design_parser.py  # 解析 technical_design / implementation_contract
|   |-- repo_context.py   # 仓库定位、文件上下文、路径安全检查
|   |-- task_workspace.py # task-id、commit 校验、worktree/copy
|   |-- diff_utils.py     # git diff
|   |-- llm.py            # OpenAI-compatible LLM adapter
|   |-- prompts.py        # 代码生成 prompt
|   `-- schemas.py        # 状态结构
|-- Output/               # 输出产物
|-- .workspace/           # 运行时 task repo，不入 Git
`-- run.py
```

## Input

必须提供：

```text
SolutionDesign/Output/technical_design_*.md
```

技术方案中应包含：

```yaml
implementation_contract:
  objective: ""
  repo_root: ""
  must_read_files: []
  change_files: []
  constraints: []
```

`repo_root` 可以是缓存仓库目录名，例如：

```text
Ryanlyl_TODO4Test_main_112b612b
```

CodeGen 会解析到：

```text
SolutionDesign/.workspace/repos/Ryanlyl_TODO4Test_main_112b612b
```

## Output

```text
CodeGen/Output/<task-id>/code_changes.diff
CodeGen/Output/<task-id>/codegen_report.md
CodeGen/Output/<task-id>/codegen_result.json
```

`codegen_result.json` 给下游阶段使用，核心字段：

```json
{
  "task_id": "",
  "source_repo_root": "",
  "codegen_repo_path": "",
  "diff_path": "",
  "report_path": "",
  "changed_files": [],
  "smoke_checks": []
}
```

## Setup

```powershell
cd E:\DeliveraX
python -m pip install -r .\CodeGen\requirements.txt
```

DeepSeek：

```powershell
$env:CODEGEN_API_KEY="your_api_key"
$env:CODEGEN_BASE_URL="https://api.deepseek.com"
$env:CODEGEN_MODEL="deepseek-chat"
```

OpenAI：

```powershell
$env:CODEGEN_API_KEY="your_api_key"
Remove-Item Env:CODEGEN_BASE_URL -ErrorAction SilentlyContinue
$env:CODEGEN_MODEL="gpt-4o-mini"
```

也可以写入根目录 `.env`：

```text
CODEGEN_API_KEY=your_api_key
CODEGEN_BASE_URL=https://api.deepseek.com
CODEGEN_MODEL=deepseek-chat
```

## Run

标准运行：

```powershell
cd E:\DeliveraX
python .\CodeGen\run.py `
  --design .\SolutionDesign\Output\technical_design_todolist_20260426163156.md `
  --task-id todolist-codegen-001
```

显式指定仓库路径：

```powershell
python .\CodeGen\run.py `
  --design .\SolutionDesign\Output\technical_design_todolist_20260426163156.md `
  --repo-path .\SolutionDesign\.workspace\repos\Ryanlyl_TODO4Test_main_112b612b `
  --task-id todolist-codegen-001
```

只跑链路冒烟，不调用 LLM、不写代码：

```powershell
python .\CodeGen\run.py `
  --design .\SolutionDesign\Output\technical_design_todolist_20260426163156.md `
  --task-id todolist-smoke `
  --local-only
```

## CLI Options

```text
--design              技术方案 Markdown，必填
--repo-path           显式指定源仓库路径，可覆盖 implementation_contract.repo_root
--workspace-dir       SolutionDesign workspace，默认 SolutionDesign/.workspace
--task-id             本次 CodeGen 任务 ID
--output-dir          输出目录，默认 CodeGen/Output
--local-only          只跑解析、workspace、diff/report/result 链路
--max-context-files   传给 LLM 的最大文件数
--max-file-chars      单文件最大上下文字符数
```

## Runtime Controls

```powershell
$env:CODEGEN_LLM_TIMEOUT_SECONDS="180"
$env:CODEGEN_LLM_MAX_RETRIES="0"
```

默认关闭 SDK 自动重试，LLM 请求 180 秒超时。Ctrl+C 会在 CLI 层转成 `CodeGen interrupted by user.`；如果中断发生在底层网络阻塞中，可能要等当前系统调用返回或超时。

## Smoke Checks

- 技术方案可解析
- 源缓存仓库可定位
- task repo 可创建
- 技术方案 commit 与缓存仓库 commit 对齐
- 变更路径不越过仓库根目录
- 非 `local-only` 模式产生非空 git diff

## Common Errors

401 鉴权失败：

```text
LLM authentication failed (401)
```

检查 `CODEGEN_API_KEY` 与 `CODEGEN_BASE_URL` 是否匹配。DeepSeek 使用 `https://api.deepseek.com`，OpenAI 官方通常不设置 `CODEGEN_BASE_URL`。

LLM 超时：

```text
LLM request timed out
```

代码生成响应较长时可以提高超时，或减少上下文：

```powershell
$env:CODEGEN_LLM_TIMEOUT_SECONDS="300"
python .\CodeGen\run.py `
  --design .\SolutionDesign\Output\technical_design_todolist_20260426163156.md `
  --task-id todolist-codegen-001 `
  --max-context-files 16 `
  --max-file-chars 16000
```
