# Integration

`Integration` 是 DeliveraX 的交付集成阶段，阶段 ID 为 `integration`，内部包名为 `release_integration`。

## CLI

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

## 统一入口

从仓库根目录的 FastAPI / 编排层导入：

```python
from Integration.release_integration.stage import run_stage
```

如果调用进程不在仓库根目录，需要先把 `E:\DeliveraX` 加入 `PYTHONPATH`，因为 `stage.py` 依赖根目录的 `stage_contracts`。

CLI 入口 `python .\Integration\run.py ...` 不需要手动设置 `PYTHONPATH`。

入口契约见根目录 [STAGE_CONTRACT.md](../STAGE_CONTRACT.md)。
