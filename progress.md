## 进度日志

### 2026-05-07
- 初始化 S04：已在 `target` 下 `npm install` 并启动 `npm run dev`（仅供目视验证 UI，不作为后端测试必要条件）
- 完成：按用户要求将 Customers 页关键词输入框 label/placeholder/过滤逻辑改为仅匹配 name
- 暂停：为测试 AI 交付系统，已将 `target/src/views/customers/index.tsx` 故意改成不满足 r0（Customer + 仅 name 匹配），并启动过后端 API（FastAPI/uvicorn 8000）；调用 `POST /api/pipelines` 创建 pipeline 时出现请求卡住，尚未定位原因（已停止后台进程，待下次继续排查）。

