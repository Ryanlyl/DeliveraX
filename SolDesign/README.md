# SolDesign

`SolDesign` 是 DeliveraX 的方案设计阶段，阶段 ID 为 `solution`，内部包名为 `solution_design`。

## CLI

```powershell
cd E:\DeliveraX
python .\SolDesign\run.py `
  --requirement .\SolDesign\Input\structured_requirement_example.md `
  --repo-path .\FrontEnd `
  --local-only
```

## 统一入口

从仓库根目录的 FastAPI / 编排层导入：

```python
from SolDesign.solution_design.stage import run_stage
```

如果调用进程不在仓库根目录，需要先把 `E:\DeliveraX` 加入 `PYTHONPATH`，因为 `stage.py` 依赖根目录的 `stage_contracts`。

CLI 入口 `python .\SolDesign\run.py ...` 不需要手动设置 `PYTHONPATH`。

入口契约见根目录 [STAGE_CONTRACT.md](../STAGE_CONTRACT.md)。
