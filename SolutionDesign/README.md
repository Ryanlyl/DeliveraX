# SolutionDesign

`SolutionDesign` 是 DeliveraX 的“方案设计”阶段：读取结构化需求 Markdown，拉取并扫描目标前端代码库，生成可供人工 review、也可交给下一阶段代码实现 Agent 执行的技术方案 Markdown。

## Workflow

```text
structured_requirement.md + GitHub repo/local repo
  -> Requirement Loader
  -> Repository Fetcher
  -> Repo Scanner
  -> Architecture Analyzer
  -> Impact Analyzer
  -> Design Planner
  -> Format Validator
  -> Consistency Reviewer
  -> technical_design_*.md
```

## Directory

```text
SolutionDesign/
|-- agent/
|   |-- cli.py              # CLI 参数解析
|   |-- graph.py            # LangGraph workflow
|   |-- nodes.py            # 各节点实现
|   |-- repo_context.py     # GitHub 拉取、缓存、扫描、上下文筛选
|   |-- format_validator.py # 输出格式和文件路径校验
|   |-- prompts.py          # LLM prompts
|   |-- llm.py              # OpenAI-compatible LLM adapter
|   |-- markdown_io.py      # Markdown 读写
|   `-- schemas.py          # TypedDict 状态定义
|-- Input/
|   `-- structured_requirement_example.md
|-- Output/
|   `-- .gitkeep
|-- templates/
|   `-- technical_design_template.md
|-- .gitignore
|-- requirements.txt
`-- run.py
```

运行时产物不会进入 Git：

- `.workspace/`：GitHub 仓库缓存和任务级 workspace
- `Output/technical_design_*.md`：生成结果
- `Input/*.md`：本地 mock PRD，`structured_requirement_example.md` 除外
- `__pycache__/`、`.env*`、日志和临时文件

## Setup

```powershell
cd E:\DeliveraX
python -m pip install -r .\SolutionDesign\requirements.txt
```

配置 LLM，支持 DeepSeek、OpenAI 或其他 OpenAI-compatible 服务：

```powershell
$env:SOLUTION_DESIGN_API_KEY="your_api_key"
$env:SOLUTION_DESIGN_BASE_URL="https://api.deepseek.com"
$env:SOLUTION_DESIGN_MODEL="deepseek-chat"
```

私有 GitHub 仓库需要 token：

```powershell
$env:SOLUTION_DESIGN_GITHUB_TOKEN="github_token"
```

## Run

使用 GitHub 仓库：

```powershell
cd E:\DeliveraX
python .\SolutionDesign\run.py `
  --requirement .\SolutionDesign\Input\structured_requirement_example.md `
  --repo-url https://github.com/example/frontend-repo `
  --repo-ref main
```

使用本地仓库：

```powershell
python .\SolutionDesign\run.py `
  --requirement .\SolutionDesign\Input\structured_requirement_example.md `
  --repo-path E:\SomeFrontendRepo
```

无 LLM smoke test：

```powershell
python .\SolutionDesign\run.py `
  --requirement .\SolutionDesign\Input\structured_requirement_example.md `
  --repo-path E:\SomeFrontendRepo `
  --local-only
```

后续接入 FastAPI 时建议传任务 ID，避免并发任务共享同一个缓存目录：

```powershell
python .\SolutionDesign\run.py `
  --requirement .\SolutionDesign\Input\structured_requirement_example.md `
  --repo-url https://github.com/example/frontend-repo `
  --task-id task-20260426-001
```

输出写入：

```text
SolutionDesign/Output/technical_design_*.md
```

## Repository Fetching

`Repository Fetcher` 的行为集中在 `agent/repo_context.py`：

- 优先 `git clone --depth 1`
- `git clone` 失败后 fallback 到 GitHub zip archive
- `--repo-ref` 支持 branch、tag、commit SHA
- 默认网络重试 3 次，可用 `SOLUTION_DESIGN_RETRY_ATTEMPTS` 调整
- 拉取后校验仓库非空
- 检测 `package.json`，写入 `frontend_repo_valid` 和 warning
- 记录 resolved ref、commit SHA、fetch method、cache key
- zip 解压前检查路径，避免越界解压
- 默认缓存 TTL 为 7 天，可用 `SOLUTION_DESIGN_CACHE_TTL_SECONDS` 调整

默认缺少 `package.json` 只给 warning。需要严格限制为现代前端仓库时：

```powershell
$env:SOLUTION_DESIGN_REQUIRE_PACKAGE_JSON="true"
```

## Output Validation

`Format Validator` 会在写出前检查：

- 必须包含模板中的 0-12 章节
- `文件变更清单` 必须是 Markdown 表格
- `API 设计` 必须存在
- `implementation_contract` YAML 必须存在
- 表格中标为修改/删除的文件路径必须能在扫描结果中找到

校验失败时会最多触发一次 LLM 修复；如果仍失败，错误报告会写入最终方案的自检补充。
