## 目标

把 `agents/code_testing/`（CodeTest 执行器）整体扫一遍，修复已知与潜在风险，确保在 Windows 环境下：

- 能稳定运行（不会因端口/CI/webServer 冲突失败）
- 能自动启动前端（Vite/React 项目）并与 Playwright 期望端口一致
- 不会误覆盖 nodejs_sp 项目已有的 `package.json` / `playwright.config.*`
- 能正确使用 CodeGen 的工作区变更（避免“回退到 source_repo_root 后丢失 diff”）
- 出错时日志/产物可定位，避免“阶段长时间 running 但无关键日志”

## 当前现象（基于 S04 复现）

- 已能自动启动前端（dev server ready）。
- Playwright `webServer` 与手工启动冲突问题已处理（避免 CI 导致 webServer 再起一份）。
- 仍出现 E2E 超时/选择器找不到；进一步发现 CodeTest workspace 可能没反映 CodeGen 的 diff（需要确保 workspace 内容一致）。

## 风险清单与修复计划

### Phase 1 — 快速盘点（in_progress）
- [ ] 列出 `agents/code_testing/` 关键入口与数据流（inputs → workspace → generate files → run tests → outputs）
- [ ] Windows 专属风险：端口占用、进程清理、长路径、CRLF、文件锁
- [ ] 产物/日志风险：running 卡住时缺少实时日志与可观测性

### Phase 2 — 关键修复（pending）
- [ ] **workspace 对齐**：确保当 `codegen_repo_path` 不可用而回退 `source_repo_root` 时，仍把 `code_changes.diff` 正确应用到 CodeTest workspace
- [ ] **Playwright 端口一致性**：从项目 `playwright.config.*` 解析端口，启动同端口，并清理占用者
- [ ] **CI/webServer 冲突**：若已启动前端，运行 Playwright 时不要强制 `CI=true`（避免 webServer 再起/端口占用）
- [ ] **不覆盖配置**：nodejs_sp 下跳过覆写 `package.json`/`playwright.config.*`（已做，但需要再确认覆盖面）

### Phase 3 — 可靠性增强（pending）
- [ ] 前端 warmup（对 `/customers` 做预热请求）降低首屏渲染超时
- [ ] 超时与诊断：Playwright 失败时自动附加关键文件路径/端口/启动命令到 report/log
- [ ] 当 stage 超时/挂起：输出“当前正在执行哪条命令 + 已运行多久”的进度日志

### Phase 4 — 回归验证（pending）
- [ ] 用 `codegen_result.json` 单独跑 CodeTest 通过（至少做到“环境正确 + E2E 进入页面并稳定定位元素”）
- [ ] 再跑一轮 pipeline 的 test stage，确认不会长时间 running 且产物齐全

