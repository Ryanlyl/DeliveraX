# RequirementsAnalysis

`RequirementsAnalysis` 是 DeliveraX 的前端需求提炼与结构化模块。它把自然语言需求转为可校验的 `RequirementSpec`，并生成可审阅的 Markdown PRD。

## 核心架构

组件按照“输入校验 -> 语义边界检查 -> LLM 生成 -> 结果校验 -> Markdown 输出”组织：

- `agent/input_validator.py`
  - 校验原始用户输入是否为空或格式异常
- `agent/boundary_validator.py`
  - 校验需求是否泄露实现细节、是否包含框架/状态/API设计等不应在需求层出现的内容
- `agent/spec_validator.py`
  - 校验 `RequirementSpec` 是否符合 JSON schema、是否包含必要字段
- `agent/prompts.py`
  - 生成主 prompt 和修复 prompt，用于引导 LLM 输出合法 JSON
- `agent/runner.py`
  - 负责整体流程：输入解析、LLM 调用、校验、自动修复、结果封装
- `agent/markdown_renderer.py`
  - 将最终结构化需求渲染为 Markdown PRD
- `agent/providers/deepseek.py`
  - DeepSeek API 调用实现
- `run.py`
  - 本地 CLI 入口，支持 mock 模式和真实 LLM 模式

## 运行方式

### 1. 安装依赖

```bash
cd e:\DeliveraX\RequirementsAnalysis
pip install -e .[dev]
```

### 2. 本地快速测试（默认 mock 模式）

```bash
python run.py --user-input "用户希望从会议纪要生成结构化需求文档" --output-dir ./outputs
```

### 3. 使用真实 DeepSeek 接口

```bash
set DEEPSEEK_API_KEY=your_key
python run.py --input-file ./samples/meeting_note.txt --output-dir ./outputs --use-real-llm
```

### 输出结果

默认会在 `outputs/` 下写入：

- `input.txt`
- `requirement_spec.json`
- `requirement_prd.md`
- `report.json`

## 代码调用

如果你要在代码中复用：

```python
from agent import RequirementAnalysisInput, run_requirement_analysis
from agent.providers import deepseek_llm_call

result = await run_requirement_analysis(
    RequirementAnalysisInput(userInput="我想做一个任务列表页。"),
    llm_call=deepseek_llm_call,
)
```

## 测试

```bash
pytest
```

## 设计原则

- 保持可控：先校验再生成，避免直接让 LLM 产出不可用内容
- 保留可审阅中间结果：输出结构化 spec 后再渲染 Markdown
- 支持演示与真实调用两种运行模式
