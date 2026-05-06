# ReqAnalysis

`ReqAnalysis` 是 DeliveraX 的需求分析阶段，阶段 ID 为 `requirements`，内部包名为 `requirement_analysis`。

## CLI

```powershell
cd E:\DeliveraX
python .\ReqAnalysis\run.py `
  --input-file .\ReqAnalysis\samples\meeting_note.txt `
  --output-dir .\ReqAnalysis\outputs `
  --run-id smoke_test
```

## 统一入口

从仓库根目录的 FastAPI / 编排层导入：

```python
from ReqAnalysis.requirement_analysis.stage import run_stage
```

如果调用进程不在仓库根目录，需要先把 `E:\DeliveraX` 加入 `PYTHONPATH`，因为 `stage.py` 依赖根目录的 `stage_contracts`。

CLI 入口 `python .\ReqAnalysis\run.py ...` 不需要手动设置 `PYTHONPATH`。

入口契约见根目录 [STAGE_CONTRACT.md](../STAGE_CONTRACT.md)。
