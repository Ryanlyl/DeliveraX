# DeliveraX
Project for Feishu AI Competition.

## FrontEnd

`FrontEnd` 目录是项目的前端演示工程，基于 `React + Vite + TypeScript + Tailwind CSS` 搭建，当前包含 DeliveraX 的项目看板、节点工作台、文档管理和 Agent 对话演示界面。

### 入口说明

- 前端启动入口：[`FrontEnd/src/main.tsx`](./FrontEnd/src/main.tsx)
- 主页面组件：[`FrontEnd/src/App.tsx`](./FrontEnd/src/App.tsx)
- 工程配置入口：[`FrontEnd/package.json`](./FrontEnd/package.json)

### 使用方法

在项目根目录下进入 `FrontEnd` 后执行：

```bash
cd FrontEnd
npm install
npm run dev
```

默认用于本地开发预览。

如果需要生产构建，可执行：

```bash
cd FrontEnd
npm run build
```

### 提交说明

以下内容属于可再生成文件，已经写入 [`FrontEnd/.gitignore`](./FrontEnd/.gitignore)，不需要提交到 GitHub：

- `node_modules/`
- `dist/`
- `*.tsbuildinfo`
- 各类日志文件和系统缓存文件

建议提交源码、配置文件以及 `package-lock.json`，这样其他人拉取仓库后执行 `npm install` 就能恢复运行环境。
