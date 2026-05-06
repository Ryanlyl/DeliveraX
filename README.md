# DeliveraX

DeliveraX 是一个面向真实研发交付链路的 AI DevFlow 原型。当前主线是一条可审阅、可回放、可扩展的流水线：

```text
原始需求 / 会议纪要
  -> ReqAnalysis
  -> SolDesign
  -> CodeGen
  -> CodeTest
  -> ReviewGate
  -> Integration
  -> 可审阅、可合并的交付产物
```

## 模块命名

| 模块路径 | 内部包名 | 阶段 ID | 状态 |
| --- | --- | --- | --- |
| `agents/requirement_analysis` | `requirement_analysis` | `requirements` | 已接入统一入口 |
| `agents/solution_design` | `solution_design` | `solution` | 已接入统一入口 |
| `agents/code_generation` | `code_generation` | `code` | 已接入统一入口 |
| `agents/code_testing` | `code_testing` | `test` | 已接入统一入口 |
| `agents/review_gate` | `review_gate` | `review` | 已接入统一入口 |
| `agents/release_integration` | `release_integration` | `integration` | 已接入统一入口 |
| `agents/code_review` | 待定 | — | 独立 Agent（队友贡献） |
| `agents/feedback_triage` | 待定 | — | 独立 Agent（队友贡献） |
| `agents/repair_loop` | 待定 | — | 独立 Agent（队友贡献） |

统一阶段契约见 [STAGE_CONTRACT.md](./STAGE_CONTRACT.md)。

## 目录结构

```text
DeliveraX/
|-- server/                # FastAPI 编排层：pipeline 状态、阶段调用、产物读取
|-- frontend/              # React/Vite DevFlow 工作台
|-- agents/                # 所有 Pipeline Agent（统一管理）
|   |-- requirement_analysis/   # 需求分析：自然语言 -> 结构化需求 / PRD
|   |-- solution_design/        # 方案设计：PRD + 仓库上下文 -> 技术方案
|   |-- code_generation/        # 代码生成：技术方案 -> git diff
|   |-- code_testing/           # 代码测试
|   |-- review_gate/            # 评审门禁
|   |-- release_integration/    # 交付集成
|   |-- code_review/            # 代码评审 Agent
|   |-- feedback_triage/        # 反馈分流 Agent
|   `-- repair_loop/            # 修复循环 Agent
|-- stage_contracts/       # 阶段请求、结果、状态和标准产物契约
|-- docker/                # Docker 部署配置
|-- testdata/              # 测试用例数据
|-- scripts/               # 流水线运行脚本
|-- docs/                  # 文档
`-- .github/workflows/
```

## 本地运行

安装 Python 阶段依赖：

```powershell
cd E:\DeliveraX
python -m pip install -e ".\agents\requirement_analysis[dev]"
python -m pip install -r .\agents\solution_design\requirements.txt
python -m pip install -r .\agents\code_generation\requirements.txt
python -m pip install -r .\agents\release_integration\requirements.txt
python -m pip install -r .\server\requirements.txt
```

安装前端依赖：

```powershell
cd E:\DeliveraX\frontend
npm ci
```

启动前端：

```powershell
cd E:\DeliveraX\frontend
npm run dev
```

启动 FastAPI 编排层：

```powershell
cd E:\DeliveraX
python .\server\run.py
```

## 阶段 CLI 示例

ReqAnalysis：

```powershell
cd E:\DeliveraX
python .\agents\requirement_analysis\run.py `
  --input-file .\agents\requirement_analysis\samples\meeting_note.txt `
  --output-dir .\agents\requirement_analysis\outputs `
  --run-id smoke_test
```

SolDesign：

```powershell
cd E:\DeliveraX
python .\agents\solution_design\run.py `
  --requirement .\agents\solution_design\Input\structured_requirement_example.md `
  --repo-path .\frontend `
  --local-only
```

CodeGen：

先运行 SolDesign，确保产出 `technical_design_*.md` 已存在。

```powershell
cd E:\DeliveraX
$design = Get-ChildItem .\agents\solution_design\Output\technical_design_*.md |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName

python .\agents\code_generation\run.py `
  --design $design `
  --repo-path .\frontend `
  --task-id codegen-demo-001 `
  --local-only
```

Integration：

```powershell
cd E:\DeliveraX
$codegenResult = Get-ChildItem .\agents\code_generation\Output\codegen-demo-001\codegen_result.json |
  Select-Object -First 1 -ExpandProperty FullName

python .\agents\release_integration\run.py `
  --codegen-result $codegenResult `
  --task-id delivery-demo-001 `
  --test-status passed `
  --review-status approved `
  --no-llm `
  --force
```

## 统一状态

后端阶段状态统一为：

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

前端已切换到这套枚举，后续 FastAPI 层可以直接复用。
