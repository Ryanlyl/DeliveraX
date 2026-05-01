# DeliveraX

DeliveraX 是一个面向真实研发交付链路的 AI DevFlow 原型。它不再是旧版的「前端 + 后端 + 文档生成」结构，而是围绕一条更接近工程交付的流水线组织：

```text
原始需求 / 会议记录
  -> RequirementsAnalysis
  -> SolutionDesign
  -> CodeGen
  -> DeliveryIntegration
  -> 可评审、可合并的交付产物
```

核心目标是把自然语言需求逐步转成结构化需求、技术方案、代码变更 diff、交付摘要和 PR 描述，并在关键节点保留人工检查空间。

## 当前状态

- 旧的 `BackEnd` 服务已不再作为主线使用。
- 前端工作台位于 `FrontEnd/`，用于展示和体验 DevFlow 流程。
- 后端能力当前拆成多个 CLI-first 模块，每个阶段都可以独立运行、独立验证产物。
- GitHub Pages 部署 workflow 已暂时停用，提交到仓库后不会自动部署。

## 流水线模块

### 1. RequirementsAnalysis

需求分析阶段。输入自然语言需求、会议记录或产品想法，输出结构化需求和 Markdown PRD。

主要产物：

```text
RequirementsAnalysis/outputs/<run-id>/
|-- input.txt
|-- requirement_spec.json
|-- requirement_prd.md
`-- report.json
```

本地 mock 运行：

```powershell
cd E:\DeliveraX
python .\RequirementsAnalysis\run.py `
  --input-file .\RequirementsAnalysis\samples\meeting_note.txt `
  --output-dir .\RequirementsAnalysis\outputs `
  --run-id smoke_test
```

启用真实 LLM：

```powershell
$env:DEEPSEEK_API_KEY="your_api_key"
python .\RequirementsAnalysis\run.py `
  --input-file .\RequirementsAnalysis\samples\meeting_note.txt `
  --output-dir .\RequirementsAnalysis\outputs `
  --use-real-llm
```

### 2. SolutionDesign

方案设计阶段。输入结构化 PRD 和目标代码仓库，拉取或读取仓库上下文，生成可交给代码生成阶段执行的技术方案。

主要产物：

```text
SolutionDesign/Output/technical_design_*.md
SolutionDesign/.workspace/repos/<repo-cache-name>/
```

示例：

```powershell
cd E:\DeliveraX
python .\SolutionDesign\run.py `
  --requirement .\SolutionDesign\Input\structured_requirement_example.md `
  --repo-path E:\SomeFrontendRepo `
  --local-only
```

真实 LLM 配置示例：

```powershell
$env:SOLUTION_DESIGN_API_KEY="your_api_key"
$env:SOLUTION_DESIGN_BASE_URL="https://api.deepseek.com"
$env:SOLUTION_DESIGN_MODEL="deepseek-chat"
```

### 3. CodeGen

代码生成阶段。输入 `SolutionDesign` 产出的技术方案，复用方案设计阶段缓存的目标仓库，在任务级副本里落地代码修改，并输出标准 git diff。

主要产物：

```text
CodeGen/Output/<task-id>/
|-- code_changes.diff
|-- codegen_report.md
`-- codegen_result.json
```

示例：

```powershell
cd E:\DeliveraX
python .\CodeGen\run.py `
  --design .\SolutionDesign\Output\technical_design_example.md `
  --task-id codegen-demo-001 `
  --local-only
```

真实 LLM 配置示例：

```powershell
$env:CODEGEN_API_KEY="your_api_key"
$env:CODEGEN_BASE_URL="https://api.deepseek.com"
$env:CODEGEN_MODEL="deepseek-chat"
```

### 4. DeliveryIntegration

交付集成阶段。输入经过上游测试和评审的 `CodeGen` 结果，把 diff 集成到独立 worktree，生成最终 diff、中文变更摘要和 GitHub PR 描述。

这个模块不会自动 push GitHub，也不会重新拉仓库、重新测试或重新评审。

主要产物：

```text
DeliveryIntegration/Output/<task-id>/
|-- final_changes.diff
|-- change_summary.md
|-- github_pr_body.md
`-- delivery_integration_result.json
```

离线运行示例：

```powershell
cd E:\DeliveraX
python .\DeliveryIntegration\run.py `
  --codegen-result .\CodeGen\Output\codegen-demo-001\codegen_result.json `
  --task-id delivery-demo-001 `
  --no-llm `
  --force
```

如果要用 LLM 生成摘要和 PR 描述：

```powershell
$env:DELIVERY_INTEGRATION_LLM_API_KEY="your_api_key"
$env:DELIVERY_INTEGRATION_LLM_BASE_URL="https://api.deepseek.com"
$env:DELIVERY_INTEGRATION_LLM_MODEL="deepseek-chat"
```

## FrontEnd

前端工作台位于 `FrontEnd/`，基于 React + Vite + TypeScript。当前主要用于展示 DevFlow 首页、流程列表、阶段详情和节点状态。

启动方式：

```powershell
cd E:\DeliveraX\FrontEnd
npm ci
npm run dev
```

构建：

```powershell
cd E:\DeliveraX\FrontEnd
npm run build
```

## 仓库结构

```text
DeliveraX/
|-- FrontEnd/                 # React/Vite DevFlow 工作台
|-- RequirementsAnalysis/     # 自然语言需求 -> 结构化需求 / PRD
|-- SolutionDesign/           # PRD + 仓库上下文 -> 技术方案
|-- CodeGen/                  # 技术方案 -> 代码变更 diff
|-- DeliveryIntegration/      # CodeGen 结果 -> 本地交付集成产物
|-- .github/workflows/        # CI/CD workflow；Pages 部署当前已停用
`-- README.md
```

运行时目录说明：

- `*/Output/`：各阶段输出产物。
- `*/outputs/`：RequirementsAnalysis 的本地调试输出。
- `*/.workspace/`：阶段内部缓存、任务副本和 worktree。
- 这些运行时产物默认不作为长期源码维护对象。

## 环境准备

Python 模块：

```powershell
cd E:\DeliveraX
python -m pip install -e ".\RequirementsAnalysis[dev]"
python -m pip install -r .\SolutionDesign\requirements.txt
python -m pip install -r .\CodeGen\requirements.txt
python -m pip install -r .\DeliveryIntegration\requirements.txt
```

前端模块：

```powershell
cd E:\DeliveraX\FrontEnd
npm ci
```

## CI / Deployment

`.github/workflows/deploy-frontend-pages.yml` 当前处于停用状态：

- 不监听 `push`。
- 不执行 `npm ci` 或 `npm run build`。
- 不上传 GitHub Pages artifact。
- 不调用 `actions/deploy-pages`。

保留这个 workflow 只是为了占位和后续恢复；当前提交不会触发自动部署，也不会因为 Pages 部署链路报错阻塞仓库。

## 设计原则

- 每个阶段产物都可落盘、可检查、可复用。
- 代码生成不直接污染源仓库，只在任务级副本中产生 diff。
- 交付集成只处理已经通过上游约束的变更，不隐式 push。
- LLM 调用保持可配置，默认支持 OpenAI-compatible 服务。
- 人工审核是流水线的一部分，不把所有风险都交给一次性自动化。
