# S04 React 管理台样例（Customers 靶场）

- **来源基底**：[larry-xue/react-admin-dashboard](https://github.com/larry-xue/react-admin-dashboard)（MIT），复制到本包 `target/` 并独立 `git` 仓库；**不追踪**上游远端，避免与你们在 `feishuAI/react-admin-dashboard` 的探索性修改互相污染。
- **类型**：含 `package.json` 的 React 18 + TypeScript + Vite 5 + Ant Design 5 工程；CodeTest 通常按 `nodejs_sp` 对待。首次请在 **`target` 目录**执行 `npm install`。
- **包管理器**：靶场仅保留 `package-lock.json`（已移除上游自带的 `pnpm-lock.yaml`）。若二者并存，CodeTest 会选用 pnpm；未安装 pnpm 的 Windows 环境会导致 `pnpm install` 失败。
- **固定靶场**：仅 **Customers** 列表页（`/customers`）的需求与缺陷叙事；Dashboard / Team Roles 等保留为「背景壳子」。
- **缺陷设计（r0）**：`src/views/customers/index.tsx` 中 Keyword 过滤仅在 `name`、`company` 上匹配，未覆盖 `email`、`owner`，与 `requirement_r0_initial.txt` 不一致。
- **上游小修**：Modal 使用 `destroyOnClose`（已对齐全站 `tsc`/build），避免初始工程即无法 `npm run build`。

## 初始化依赖（在 target 目录）

```powershell
cd demos\scenarios\S04_react_admin_customers\target
npm install
npm run dev
```

浏览器访问控制台登录后进入 **Customers**（与上游 demo 一致）。

## 运行流水线（在 DeliveraX 根目录）

```powershell
python scripts\run_deliver_pipeline.py --env-file .env `
  --repo-path "demos\scenarios\S04_react_admin_customers\target" `
  --requirement-file "demos\scenarios\S04_react_admin_customers\requirement_r0_initial.txt" `
  --pipeline-prefix sc04_r0

python scripts\run_deliver_pipeline.py --env-file .env `
  --repo-path "demos\scenarios\S04_react_admin_customers\target" `
  --requirement-file "demos\scenarios\S04_react_admin_customers\requirement_r1_improvement.txt" `
  --pipeline-prefix sc04_r1
```

**推荐顺序**：先 r0 再 r1；若从初始缺陷仓直接跑 r1，模型可能一次性合并更多改动，叙事上仍可作为演示，但与 S01–S03 的两轮关系说明一致时建议按序执行。

元数据：`scenario.json`。
