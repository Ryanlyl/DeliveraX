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

| 模块目录 | 内部包名 | 阶段 ID | 状态 |
| --- | --- | --- | --- |
| `ReqAnalysis` | `requirement_analysis` | `requirements` | 已接入统一入口 |
| `SolDesign` | `solution_design` | `solution` | 已接入统一入口 |
| `CodeGen` | `code_generation` | `code` | 已接入统一入口 |
| `CodeTest` | 待定 | `test` | 占位 |
| `ReviewGate` | 待定 | `review` | 占位 |
| `Integration` | `release_integration` | `integration` | 已接入统一入口 |

统一阶段契约见 [STAGE_CONTRACT.md](./STAGE_CONTRACT.md)。

## 目录结构

```text
DeliveraX/
|-- FrontEnd/              # React/Vite DevFlow 工作台
|-- ReqAnalysis/           # 需求分析：自然语言 -> 结构化需求 / PRD
|-- SolDesign/             # 方案设计：PRD + 仓库上下文 -> 技术方案
|-- CodeGen/               # 代码生成：技术方案 -> git diff
|-- CodeTest/              # 代码测试占位模块
|-- ReviewGate/            # 评审门禁占位模块
|-- Integration/           # 交付集成：CodeGen 结果 -> 最终交付物
|-- stage_contracts/       # 阶段请求、结果、状态和标准产物契约
|-- artifacts/             # API / 编排层运行时标准产物目录
`-- .github/workflows/
```

## 本地运行

安装 Python 阶段依赖：

```powershell
cd E:\DeliveraX
python -m pip install -e ".\ReqAnalysis[dev]"
python -m pip install -r .\SolDesign\requirements.txt
python -m pip install -r .\CodeGen\requirements.txt
python -m pip install -r .\Integration\requirements.txt
```

安装前端依赖：

```powershell
cd E:\DeliveraX\FrontEnd
npm ci
```

启动前端：

```powershell
cd E:\DeliveraX\FrontEnd
npm run dev
```

## 阶段 CLI 示例

ReqAnalysis：

```powershell
cd E:\DeliveraX
python .\ReqAnalysis\run.py `
  --input-file .\ReqAnalysis\samples\meeting_note.txt `
  --output-dir .\ReqAnalysis\outputs `
  --run-id smoke_test
```

SolDesign：

```powershell
cd E:\DeliveraX
python .\SolDesign\run.py `
  --requirement .\SolDesign\Input\structured_requirement_example.md `
  --repo-path .\FrontEnd `
  --local-only
```

CodeGen：

先运行 `SolDesign`，确保 `SolDesign/Output/technical_design_*.md` 已存在。

```powershell
cd E:\DeliveraX
$design = Get-ChildItem .\SolDesign\Output\technical_design_*.md |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName

python .\CodeGen\run.py `
  --design $design `
  --repo-path .\FrontEnd `
  --task-id codegen-demo-001 `
  --local-only
```

Integration：

该命令需要一个真实的 `CodeGen` 结果。`CodeGen --local-only` 适合冒烟测试，但通常不会产生可集成的非空 diff。

```powershell
cd E:\DeliveraX
$codegenResult = Get-ChildItem .\CodeGen\Output\codegen-demo-001\codegen_result.json |
  Select-Object -First 1 -ExpandProperty FullName

python .\Integration\run.py `
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
