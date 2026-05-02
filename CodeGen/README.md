# CodeGen

`CodeGen` 是 DeliveraX 的代码生成阶段，阶段 ID 为 `code`，内部包名为 `code_generation`。

## CLI

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

## 统一入口

从仓库根目录的 FastAPI / 编排层导入：

```python
from CodeGen.code_generation.stage import run_stage
```

如果调用进程不在仓库根目录，需要先把 `E:\DeliveraX` 加入 `PYTHONPATH`，因为 `stage.py` 依赖根目录的 `stage_contracts`。

CLI 入口 `python .\CodeGen\run.py ...` 不需要手动设置 `PYTHONPATH`。

入口契约见根目录 [STAGE_CONTRACT.md](../STAGE_CONTRACT.md)。
