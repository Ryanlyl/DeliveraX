## CodeTest 扫描发现（滚动追加）

### 复现与根因链路（S04）
- Playwright 项目自身 `playwright.config.ts` 使用固定端口（例如 `5179`）并配置了 `webServer.command`。
- CodeTest 自动启动前端若用其它端口，会导致 Playwright 再起 webServer 或报端口占用。
- 运行 Playwright 时若强制 `CI=true`，会使 `reuseExistingServer: !process.env.CI` 变成 false，进一步触发“再起 webServer”的冲突。
- 当 `codegen_repo_path` 指向短生命周期目录不可用时，CodeTest 回退到 `source_repo_root` 复制；若不再应用 `code_changes.diff`，workspace 将不包含 CodeGen 的改动，导致“测试与目标代码不一致”。

### 已做的修复点（本次会话）
- `generate_test_files`：nodejs_sp 下跳过覆写已有 `package.json`/`playwright.config.*`。
- `resolve_inputs`：更健壮地回退 `source_repo_root`（避免引用已不存在的 codegen workspace）。
- `_maybe_start_frontend_dev_server`：
  - 启动 Vite/React 前端 dev server
  - 写入 `index-START.html` 跳转页（兼容历史测试入口）
  - 解析 Playwright config port + 清理端口监听者（Windows）
  - warmup `/customers`（降低首屏超时概率）
- `run_tests`：当已由 CodeTest 自己启动了 dev server 时，不强制 `CI=true`（避免 Playwright webServer 再起）
- `workspace.copy_task_repository`：Windows 下 `rmtree` 对只读/锁文件更稳健

### 仍待修复/确认的风险
- `git apply` 对 diff 文件的兼容：需要确保 diff 能稳定应用（避免 “corrupt patch”）
- test stage 长时间 running 的可观测性：应输出实时进度或阶段性日志（至少包含当前命令）

