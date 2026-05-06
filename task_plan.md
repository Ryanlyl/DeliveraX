## 目标

用 `testdata/node_js/S04_react_admin_customers` 案例，通过**后端 API**模拟前端上传需求文件并触发 AI 交付系统，自动按 `requirement_r0_initial.txt` 修改代码，并验证产物（补丁/提交/PR/构建结果等）。

## 范围与约束

- 仅测试后端（但需要 API 调用模拟前端行为）
- 前端输入文件：`testdata/node_js/S04_react_admin_customers/requirement_r0_initial.txt`
- 目标仓库路径（待确认后端如何接收）：`testdata/node_js/S04_react_admin_customers/target`

## 阶段

### Phase A — 理解需求与前端交互（in_progress）
- [ ] 读取 r0 需求文件，提取“验收标准/期望改动文件/行为”
- [ ] 扫描 S04 前端代码，确认“前端会怎么构造请求”（字段名、文件上传、额外 metadata）

### Phase B — 定位后端 API 与任务执行流（pending）
- [ ] 找到后端服务入口（路由/控制器）
- [ ] 找到上传需求文件的 API（multipart 或 base64）
- [ ] 找到触发 pipeline/任务执行的 API（同步/异步、轮询/回调）
- [ ] 找到产物输出位置（补丁文件、git commit、artifact、日志）

### Phase C — 复现一次端到端 API 调用（pending）
- [ ] 写出 PowerShell 调用序列（上传 -> 创建任务 -> 执行 -> 查询状态 -> 获取结果）
- [ ] 跑通一次并记录关键参数与输出

### Phase D — 验证与回归（pending）
- [ ] 验证代码已按需求修改（diff）
- [ ] 运行 `npm run build`（或系统自带验证方式）

## 待用户确认（阻塞项）
- 后端 API 的 base URL、鉴权方式（token/cookie/无鉴权）
- “上传需求文件”与“触发交付”分别对应哪个 endpoint
- 期望的最终产物形式：补丁文件？直接改 repo？生成 PR？

## 错误记录
（遇到错误时在此追加：错误信息、尝试、解决方案）

