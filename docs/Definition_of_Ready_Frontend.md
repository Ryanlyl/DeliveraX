# Frontend 接入标准（Definition of Ready）

目标：让 DeliveraX 在 **static_html** 与 **nodejs_sp（npm SPA）** 两类项目上做到“高概率一键跑通”，把不可避免的问题前置为可解释、可修复的检查项。

---

## 1) static_html（纯静态页面）

### 必备条件
- **入口文件明确**
  - 优先约定 `index-START.html`；否则至少有 `index.html`
- **页面无需登录/无需后端依赖**
- **资源相对路径可用**
  - `styles.css`、`assets/*` 以相对路径可被静态 server 正常加载

### 推荐条件（强烈建议）
- 关键交互元素有稳定锚点（`id` 或 `data-testid`）
- 若需要对“信息块数量/结构”做验收，优先用稳定 `id` / 标题文本，而不是依赖 DOM 标签类型与 class 计数

---

## 2) nodejs_sp（npm 单体 SPA，例如 Vite/React）

### 必备条件
- 仓库根目录存在 `package.json`
- 能在无交互环境执行安装与测试：
  - `npm ci` 或 `npm install`
  - `npm test`（或提供 `playwright test` 能跑）
- **dev server 可指定端口**
  - 推荐支持：`npm run dev -- --host 127.0.0.1 --port <port>`

### 推荐条件（强烈建议）
- **可自动化登录**
  - 推荐提供 `autologin` 或测试账号/无验证码路径
- **稳定选择器**
  - 登录表单、Search/Reset、关键表格/列表建议使用 `data-testid` 或固定 `id`
- **可预测种子数据（mock/seed）**
  - E2E 断言基于稳定 seed，避免“猜数据”

---

## 3) Pin（固定 E2E 测试资产）

若仓库存在 `e2e/.deliverax_pin`：
- 系统不会覆盖：
  - `e2e/*.spec.*`
  - `playwright.config.*`
- 允许（可选）仅新增到：`e2e/generated/`

目的：避免 LLM 生成测试时“幻觉数据/幻觉选择器”导致不稳定回归。

