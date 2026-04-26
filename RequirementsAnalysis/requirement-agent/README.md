# Requirement Agent

## 模块职责

Requirement Agent 负责把用户输入的自然语言前端需求，整理为可审阅的结构化需求产物。

处理流程：

1. 校验用户输入是否为空、过短、或明显不属于前端需求范围
2. 构建 Requirement Agent Prompt
3. 调用外部传入的 `llmCall`
4. 解析 LLM 返回的 JSON
5. 校验 JSON 是否符合 `RequirementSpec` 基本结构
6. 校验内容是否越过需求分析边界
7. 渲染 Markdown PRD
8. 返回结构化结果

Requirement Agent 不做方案设计，不读取代码库上下文，不生成代码，不决定技术方案。

## 输入是什么

对外只调用一个主函数：

```ts
runRequirementAnalysis(input)
```

输入结构：

```ts
{
  userInput: string;
  llmCall: (prompt: string) => Promise<string>;
}
```

字段说明：

- `userInput`：用户的自然语言前端需求描述
- `llmCall`：由调用方注入的模型调用函数，接收 prompt，返回 JSON 字符串

## 输出是什么

返回结构：

```ts
{
  spec: RequirementSpec | null;
  markdown: string | null;
  status: "In Review" | "Failed";
  validation: {
    valid: boolean;
    errors: {
      category: string;
      keyword: string;
      message: string;
    }[];
  };
  error?: {
    code: string;
    message: string;
  };
}
```

## 不负责什么

Requirement Agent 只负责需求分析阶段，不负责：

- 方案设计
- 代码生成
- 代码库上下文读取
- 技术方案决策
- 文件组织规划
- 接口方案设计
- 测试实现设计
- 前端页面实现

## 如何调用

```ts
import { runRequirementAnalysis } from "./requirement-agent";

const result = await runRequirementAnalysis({
  userInput: "我想做一个任务列表页，用户可以查看任务，并把任务标记为完成。移动端也要能正常看，接口异常时要有提示。",
  llmCall: async (prompt) => {
    return await callYourModel(prompt);
  },
});

if (result.status === "In Review") {
  console.log(result.spec);
  console.log(result.markdown);
} else {
  console.log(result.error);
  console.log(result.validation.errors);
}
```

`llmCall` 由接入方实现。当前模块不会直接连接真实模型。

## 返回字段说明

- `spec`：结构化需求数据。成功时为 `RequirementSpec`，失败时为 `null`
- `markdown`：可审阅 Markdown PRD。成功时为字符串，失败时为 `null`
- `status`：分析状态
- `validation.valid`：校验是否通过
- `validation.errors`：结构化校验错误列表
- `error`：失败时的错误码与可读错误信息

## 失败错误码说明

| code | message | 说明 |
| --- | --- | --- |
| `EMPTY_INPUT` | `请输入前端需求描述` | 输入为空或只包含空格 |
| `INPUT_TOO_SHORT` | `需求描述过短，请补充目标、页面或交互信息` | 去除空格后长度少于 10 个字符 |
| `NOT_FRONTEND_REQUIREMENT` | `当前需求不属于前端需求分析范围` | 未命中前端需求关键词 |
| `INVALID_LLM_JSON` | `LLM 返回内容不是合法 JSON` | LLM 返回内容无法解析为 JSON |
| `INVALID_SPEC_SCHEMA` | `LLM 返回内容不符合 RequirementSpec 结构` | JSON 缺少必要结构字段 |
| `BOUNDARY_VALIDATION_FAILED` | `需求分析结果包含越过需求分析边界的内容` | 内容包含需求分析阶段不应出现的信息 |

## 状态说明

| status | 说明 |
| --- | --- |
| `In Review` | 需求分析成功，已生成可供人工审阅的 PRD |
| `Failed` | 输入、模型返回、结构或边界校验失败 |

## 如何运行 example

```bash
npm run example
```

## 如何运行测试

```bash
npm test
```

## 样例输出

- `sample-output.json`：示例输入对应的完整 `RequirementSpec`
- `sample-output.md`：示例输入对应的 Markdown PRD
