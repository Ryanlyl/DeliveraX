## CodeTest 扫描进度

### 2026-05-07
- 已单独跑 `CodeTest`（CLI）复现问题：从“缺前端/端口冲突”推进到“可启动前端并执行 Playwright”。
- 已加入：前端自动启动、端口解析与清理、避免 CI 导致 webServer 再起、nodejs_sp 不覆写 package.json/playwright.config、warmup。
- 已加入：在 `CodeTest` workspace 尝试应用 `code_changes.diff`，并识别“已应用”场景；stage 默认 `local_only=false`，并支持通过 stage options 配置前端 autostart（写入 env）。
- 下一步：系统性扫 `agents/code_testing/` 全目录，补充可观测性（running 时进度日志）与错误诊断信息。

