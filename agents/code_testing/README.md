# CodeTest

从 `codegen_result.json` 拉取设计、diff 与任务仓库，执行 **test_plan（JSON）→ test_generation（JSON，含 `files[]`）→ 安装依赖 → 运行测试**，产出 `code_test_result.json`。

详见仓库根目录上层文档（`findings.md` 中的 CodeTest 章节）。

## 环境

- Python 3；依赖见 `requirements.txt`。
- **本地验收参考**：Node **v24.x**、npm **11.x**（以你机器 `node -v` / `npm -v` 为准）。
- LLM：`CODETEST_API_KEY`（或 Fallback `CODEGEN_*` / `DEEPSEEK_*` 等，见 `agent/llm.py`）。
- 单次任务默认 **最多 12 次 LLM 调用**，可用环境变量 `CODETEST_LLM_MAX_CALLS_PER_RUN` 调整。

## 运行

在 **`CodeTest/`** 目录下：

```powershell
cd DeliveraX-main\DeliveraX-main\CodeTest
python -m pip install -r requirements.txt
python run.py --codegen-result ..\CodeGen\Output\<task-id>\codegen_result.json --local-only
```

完整跑测需配置 LLM，且去掉 `--local-only`。

## 流水线顺序

**CodeTest 通过后再进入 CodeReview**（不与评审并行）。

## 首个验收仓库

**TODO4Test**（工作区内 `TODO4Test-main`）；静态 HTML 场景下由 **`test_generation.json` 的 `files[]`** 生成最小 `package.json` + Playwright 配置与用例（见 `agent/prompts.py`）。
