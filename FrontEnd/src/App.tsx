import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Bot,
  ChevronRight,
  CircleCheckBig,
  Clock3,
  FileText,
  FolderKanban,
  FolderOpen,
  Inbox,
  LayoutDashboard,
  MessageSquare,
  Search,
  Upload,
  Wrench,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const pipelineStages = [
  "需求分析",
  "方案设计",
  "研发实现",
  "测试评审",
  "交付上线",
];

type ViewMode = "projects" | "docs";
type PageMode = "overview" | "node";

type Project = {
  id: string;
  name: string;
  industry: string;
  status: "进行中" | "已完成";
  progress: number;
  currentStage: string;
  summary: string;
  owner: string;
  tags: string[];
};

type TodoItem = {
  id: string;
  title: string;
  type: "表单" | "审核" | "输入" | "上传";
  due: string;
  assignee: string;
};

type OutputDoc = {
  id: string;
  name: string;
  version: string;
  updatedAt: string;
  status: "草稿" | "待审核" | "已发布";
};

type FolderGroup = {
  name: string;
  docs: { name: string; type: string; updatedAt: string }[];
};

const projects: Project[] = [
  {
    id: "p1",
    name: "RIS 地下车库信号增强原型",
    industry: "通信硬件",
    status: "进行中",
    progress: 2,
    currentStage: "方案设计",
    summary: "围绕地下停车场 RIS 部署场景，完成需求澄清、方案设计和交付准备。",
    owner: "交付团队 A",
    tags: ["RIS", "通信设备", "Demo"],
  },
  {
    id: "p2",
    name: "边缘网关批量交付流程",
    industry: "工业互联网",
    status: "进行中",
    progress: 3,
    currentStage: "研发实现",
    summary: "将需求、方案、测试和交付文档统一纳入 Agent 驱动流程。",
    owner: "平台团队",
    tags: ["通用平台", "Agent Flow"],
  },
  {
    id: "p3",
    name: "智慧园区设备上线项目",
    industry: "园区网络",
    status: "已完成",
    progress: 5,
    currentStage: "交付上线",
    summary: "已完成端到端需求交付闭环，沉淀项目模板和标准文档。",
    owner: "交付团队 B",
    tags: ["已归档", "模板项目"],
  },
];

const nodeTodoMap: Record<string, TodoItem[]> = {
  需求分析: [
    { id: "t1", title: "填写客户场景采集表", type: "表单", due: "今天", assignee: "售前" },
    { id: "t2", title: "上传地下车库平面图", type: "上传", due: "今天", assignee: "项目经理" },
    { id: "t3", title: "确认 KPI 指标与覆盖目标", type: "输入", due: "明天", assignee: "产品经理" },
  ],
  方案设计: [
    { id: "t4", title: "审核 RIS 部署点位建议", type: "审核", due: "今天", assignee: "解决方案架构师" },
    { id: "t5", title: "补充链路预算参数", type: "输入", due: "今天", assignee: "研发" },
    { id: "t6", title: "提交设备 BOM 草案", type: "表单", due: "明天", assignee: "硬件工程师" },
  ],
  研发实现: [
    { id: "t7", title: "同步接口联调清单", type: "审核", due: "今天", assignee: "前后端" },
    { id: "t8", title: "更新原型固件版本号", type: "输入", due: "今天", assignee: "嵌入式工程师" },
  ],
  测试评审: [
    { id: "t9", title: "上传测试报告", type: "上传", due: "今天", assignee: "测试" },
    { id: "t10", title: "发起里程碑评审", type: "表单", due: "明天", assignee: "项目经理" },
  ],
  交付上线: [
    { id: "t11", title: "确认交付清单", type: "审核", due: "今天", assignee: "交付经理" },
    { id: "t12", title: "归档最终文档包", type: "上传", due: "今天", assignee: "文控" },
  ],
};

const nodeOutputMap: Record<string, OutputDoc[]> = {
  需求分析: [
    { id: "o1", name: "需求澄清纪要", version: "v1.2", updatedAt: "2 小时前", status: "已发布" },
    { id: "o2", name: "现场勘测记录", version: "v0.9", updatedAt: "4 小时前", status: "待审核" },
  ],
  方案设计: [
    { id: "o3", name: "RIS 方案设计书", version: "v0.8", updatedAt: "30 分钟前", status: "待审核" },
    { id: "o4", name: "部署拓扑图", version: "v0.7", updatedAt: "1 小时前", status: "草稿" },
    { id: "o5", name: "BOM 清单", version: "v0.5", updatedAt: "今天", status: "草稿" },
  ],
  研发实现: [
    { id: "o6", name: "接口设计文档", version: "v1.0", updatedAt: "今天", status: "已发布" },
    { id: "o7", name: "固件变更说明", version: "v0.6", updatedAt: "昨天", status: "待审核" },
  ],
  测试评审: [
    { id: "o8", name: "测试用例集", version: "v0.9", updatedAt: "今天", status: "待审核" },
    { id: "o9", name: "评审问题单", version: "v0.3", updatedAt: "今天", status: "草稿" },
  ],
  交付上线: [
    { id: "o10", name: "交付验收文档", version: "v1.0", updatedAt: "今天", status: "已发布" },
    { id: "o11", name: "运维手册", version: "v1.0", updatedAt: "今天", status: "已发布" },
  ],
};

const docGroups: FolderGroup[] = [
  {
    name: "工程文件夹",
    docs: [
      { name: "RIS 方案设计书.docx", type: "设计文档", updatedAt: "今天 14:20" },
      { name: "部署拓扑图.vsdx", type: "图纸", updatedAt: "今天 12:10" },
      { name: "BOM 清单.xlsx", type: "清单", updatedAt: "昨天" },
    ],
  },
  {
    name: "甲方文件夹",
    docs: [
      { name: "客户原始需求.pdf", type: "需求输入", updatedAt: "昨天" },
      { name: "现场照片.zip", type: "附件", updatedAt: "2 天前" },
    ],
  },
  {
    name: "交付归档",
    docs: [
      { name: "验收文档包.zip", type: "归档", updatedAt: "上周" },
      { name: "运维手册.docx", type: "说明书", updatedAt: "上周" },
    ],
  },
];

const chatHistory = [
  {
    role: "agent",
    text: "你好，我是 DeliveraX Agent 管理员。你可以让我检索项目状态、生成节点文档草案，或者检查待办。",
  },
  { role: "user", text: "帮我看看 RIS 项目的设计节点缺什么输入。" },
  {
    role: "agent",
    text: "当前缺少链路预算参数和最终 BOM 草案，建议先发起参数补录并提醒架构师审核。",
  },
] as const;

function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "已完成" || status === "已发布"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : status === "进行中" || status === "待审核"
        ? "bg-amber-50 text-amber-700 border-amber-200"
        : "bg-slate-50 text-slate-700 border-slate-200";

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs ${tone}`}>
      {status}
    </span>
  );
}

function PipelineBar({
  activeIndex,
  onNodeClick,
}: {
  activeIndex: number;
  onNodeClick?: (stage: string, index: number) => void;
}) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto py-2">
      {pipelineStages.map((stage, index) => {
        const complete = index < activeIndex;
        const current = index === activeIndex;

        return (
          <React.Fragment key={stage}>
            <button
              onClick={() => onNodeClick?.(stage, index)}
              className={`flex min-w-fit items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition hover:scale-[1.02] ${
                complete
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : current
                    ? "border-slate-300 bg-slate-900 text-white"
                    : "border-slate-200 bg-white text-slate-500"
              }`}
            >
              {complete ? (
                <CircleCheckBig className="h-3.5 w-3.5" />
              ) : (
                <span className="flex h-4 w-4 items-center justify-center rounded-full border text-[10px]">
                  {index + 1}
                </span>
              )}
              <span>{stage}</span>
            </button>
            {index < pipelineStages.length - 1 && <div className="h-px min-w-6 flex-1 bg-slate-200" />}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function AgentPane() {
  return (
    <Card className="h-[calc(100vh-9rem)] rounded-2xl border-slate-200 shadow-soft">
      <CardHeader className="border-b border-slate-100">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Bot className="h-4 w-4" /> Agent 管理员
            </CardTitle>
            <p className="mt-1 text-sm text-slate-500">对话、检索、生成、提醒统一入口</p>
          </div>
          <Badge variant="secondary" className="rounded-full">
            在线
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex h-[calc(100%-5rem)] flex-col p-4">
        <div className="flex-1 space-y-3 overflow-auto">
          {chatHistory.map((item, idx) => (
            <motion.div
              key={`${item.role}-${idx}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: idx * 0.06 }}
              className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm ${
                item.role === "agent"
                  ? "bg-slate-100 text-slate-700"
                  : "ml-auto bg-slate-900 text-white"
              }`}
            >
              {item.text}
            </motion.div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-2 border-t border-slate-100 pt-4">
          <Input placeholder="向 Agent 管理员提问，例如：生成 RIS 方案设计书摘要" />
          <Button className="rounded-xl">发送</Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function App() {
  const [viewMode, setViewMode] = useState<ViewMode>("projects");
  const [pageMode, setPageMode] = useState<PageMode>("overview");
  const [selectedProjectId, setSelectedProjectId] = useState<string>(projects[0].id);
  const [selectedStage, setSelectedStage] = useState<string>(projects[0].currentStage);
  const [search, setSearch] = useState("");
  const [selectedFolder, setSelectedFolder] = useState<string>(docGroups[0].name);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? projects[0],
    [selectedProjectId],
  );

  const filteredProjects = useMemo(() => {
    return projects.filter((project) =>
      project.name.toLowerCase().includes(search.toLowerCase()),
    );
  }, [search]);

  const selectedDocs = docGroups.find((group) => group.name === selectedFolder)?.docs ?? [];

  const openNode = (projectId: string, stage: string) => {
    setSelectedProjectId(projectId);
    setSelectedStage(stage);
    setPageMode("node");
  };

  return (
    <div className="min-h-screen bg-slate-50/80 p-4 text-slate-900 md:p-6">
      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <div className="flex flex-col gap-4 rounded-3xl border border-slate-200/80 bg-white/90 p-5 shadow-soft backdrop-blur lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <div className="rounded-2xl bg-slate-900 p-2 text-white">
                  <FolderKanban className="h-5 w-5" />
                </div>
                <div>
                  <h1 className="text-2xl font-semibold tracking-tight">DeliveraX</h1>
                  <p className="text-sm text-slate-500">从需求 → 设计 → 交付的 AI Agent 驱动流程平台</p>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant={viewMode === "projects" ? "default" : "outline"}
                className="rounded-xl"
                onClick={() => {
                  setViewMode("projects");
                  setPageMode("overview");
                }}
              >
                <LayoutDashboard className="mr-2 h-4 w-4" /> 项目界面
              </Button>
              <Button
                variant={viewMode === "docs" ? "default" : "outline"}
                className="rounded-xl"
                onClick={() => {
                  setViewMode("docs");
                  setPageMode("overview");
                }}
              >
                <FolderOpen className="mr-2 h-4 w-4" /> 文档管理
              </Button>
              <div className="ml-0 flex items-center gap-2 rounded-2xl border border-slate-200 px-3 py-2 text-sm text-slate-500 lg:ml-3">
                <Clock3 className="h-4 w-4" /> Demo / 通用平台外观
              </div>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.6fr_0.9fr]">
          <div>
            {viewMode === "projects" ? (
              pageMode === "overview" ? (
                <Card className="rounded-3xl border-slate-200 shadow-soft">
                  <CardHeader className="border-b border-slate-100">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                        <CardTitle className="text-base">项目列表</CardTitle>
                        <p className="mt-1 text-sm text-slate-500">展示进行中的项目、已完成项目及其 Pipeline 进度</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="relative w-full lg:w-72">
                          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                          <Input
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                            placeholder="搜索项目，如 RIS"
                            className="pl-9"
                          />
                        </div>
                        <Button variant="outline" className="rounded-xl">
                          新建项目
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4 p-4">
                    {filteredProjects.map((project) => (
                      <motion.div
                        key={project.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="rounded-2xl border border-slate-200 bg-white p-4 transition hover:shadow-sm"
                      >
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                          <div className="space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="text-lg font-medium">{project.name}</h3>
                              <StatusBadge status={project.status} />
                              <Badge variant="secondary" className="rounded-full">
                                {project.industry}
                              </Badge>
                            </div>
                            <p className="max-w-3xl text-sm text-slate-600">{project.summary}</p>
                            <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                              <span>负责人：{project.owner}</span>
                              {project.tags.map((tag) => (
                                <span key={tag} className="rounded-full bg-slate-100 px-2 py-1">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                          <Button
                            variant="outline"
                            className="rounded-xl"
                            onClick={() => openNode(project.id, project.currentStage)}
                          >
                            进入当前节点 <ChevronRight className="ml-1 h-4 w-4" />
                          </Button>
                        </div>

                        <div className="mt-4 rounded-2xl bg-slate-50 px-3 py-2">
                          <PipelineBar
                            activeIndex={project.progress - 1}
                            onNodeClick={(stage) => openNode(project.id, stage)}
                          />
                        </div>
                      </motion.div>
                    ))}
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
                    <button className="hover:text-slate-900" onClick={() => setPageMode("overview")}>
                      项目列表
                    </button>
                    <ChevronRight className="h-4 w-4" />
                    <span>{selectedProject.name}</span>
                    <ChevronRight className="h-4 w-4" />
                    <span className="text-slate-900">{selectedStage}</span>
                  </div>

                  <Card className="rounded-3xl border-slate-200 shadow-soft">
                    <CardHeader className="border-b border-slate-100">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                          <CardTitle className="text-base">节点子页面：{selectedStage}</CardTitle>
                          <p className="mt-1 text-sm text-slate-500">统一采用 输入 → AI Agent 处理 → 输出 的节点工作台</p>
                        </div>
                        <div className="rounded-2xl bg-slate-50 px-3 py-2 text-sm text-slate-600">
                          当前项目：{selectedProject.name}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="p-4">
                      <div className="mb-4 rounded-2xl bg-slate-50 px-3 py-2">
                        <PipelineBar
                          activeIndex={Math.max(pipelineStages.indexOf(selectedStage), 0)}
                          onNodeClick={(stage) => setSelectedStage(stage)}
                        />
                      </div>

                      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <Card className="rounded-2xl border-slate-200 shadow-none">
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-base">
                              <Inbox className="h-4 w-4" /> TODO / 输入区
                            </CardTitle>
                            <p className="text-sm text-slate-500">表单提交链接、待审核文件、需要补录的数据</p>
                          </CardHeader>
                          <CardContent className="space-y-3">
                            {(nodeTodoMap[selectedStage] ?? []).map((todo) => (
                              <div key={todo.id} className="rounded-2xl border border-slate-200 p-3">
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <div className="font-medium">{todo.title}</div>
                                    <div className="mt-1 text-sm text-slate-500">负责人：{todo.assignee} · 截止：{todo.due}</div>
                                  </div>
                                  <Badge variant="outline" className="rounded-full">
                                    {todo.type}
                                  </Badge>
                                </div>
                                <div className="mt-3 flex gap-2">
                                  <Button size="sm" className="rounded-xl">
                                    处理
                                  </Button>
                                  <Button size="sm" variant="outline" className="rounded-xl">
                                    指派 Agent
                                  </Button>
                                </div>
                              </div>
                            ))}
                            <Button variant="outline" className="w-full rounded-xl">
                              <Upload className="mr-2 h-4 w-4" /> 新增输入项
                            </Button>
                          </CardContent>
                        </Card>

                        <Card className="rounded-2xl border-slate-200 shadow-none">
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-base">
                              <FileText className="h-4 w-4" /> 输出文档区
                            </CardTitle>
                            <p className="text-sm text-slate-500">该节点经 Agent 处理后生成的文档、报告和产物</p>
                          </CardHeader>
                          <CardContent className="space-y-3">
                            {(nodeOutputMap[selectedStage] ?? []).map((doc) => (
                              <div key={doc.id} className="rounded-2xl border border-slate-200 p-3">
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <div className="font-medium">{doc.name}</div>
                                    <div className="mt-1 text-sm text-slate-500">版本：{doc.version} · 更新：{doc.updatedAt}</div>
                                  </div>
                                  <StatusBadge status={doc.status} />
                                </div>
                                <div className="mt-3 flex gap-2">
                                  <Button size="sm" className="rounded-xl">
                                    查看
                                  </Button>
                                  <Button size="sm" variant="outline" className="rounded-xl">
                                    导出
                                  </Button>
                                </div>
                              </div>
                            ))}
                            <div className="rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                              这里后续可以接入：文档预览、版本对比、人工审核通过/驳回、Agent 自动生成摘要。
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )
            ) : (
              <Card className="rounded-3xl border-slate-200 shadow-soft">
                <CardHeader className="border-b border-slate-100">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <CardTitle className="text-base">文档管理</CardTitle>
                      <p className="mt-1 text-sm text-slate-500">左侧文件夹分类，右侧展示文件列表，Agent 对话区保持不变</p>
                    </div>
                    <Button className="rounded-xl">上传文档</Button>
                  </div>
                </CardHeader>
                <CardContent className="p-4">
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-[0.9fr_1.4fr]">
                    <Card className="rounded-2xl border-slate-200 shadow-none">
                      <CardHeader>
                        <CardTitle className="text-base">文件夹</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {docGroups.map((group) => (
                          <button
                            key={group.name}
                            onClick={() => setSelectedFolder(group.name)}
                            className={`flex w-full items-center justify-between rounded-2xl border px-3 py-3 text-left transition ${
                              selectedFolder === group.name
                                ? "border-slate-900 bg-slate-900 text-white"
                                : "border-slate-200 bg-white hover:bg-slate-50"
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <FolderOpen className="h-4 w-4" />
                              <span>{group.name}</span>
                            </div>
                            <span className="text-xs opacity-80">{group.docs.length}</span>
                          </button>
                        ))}
                      </CardContent>
                    </Card>

                    <Card className="rounded-2xl border-slate-200 shadow-none">
                      <CardHeader>
                        <CardTitle className="text-base">{selectedFolder}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {selectedDocs.map((doc) => (
                          <div
                            key={doc.name}
                            className="flex flex-col gap-3 rounded-2xl border border-slate-200 p-4 lg:flex-row lg:items-center lg:justify-between"
                          >
                            <div className="flex items-start gap-3">
                              <div className="rounded-xl bg-slate-100 p-2">
                                <FileText className="h-4 w-4" />
                              </div>
                              <div>
                                <div className="font-medium">{doc.name}</div>
                                <div className="mt-1 text-sm text-slate-500">类型：{doc.type} · 更新时间：{doc.updatedAt}</div>
                              </div>
                            </div>
                            <div className="flex gap-2">
                              <Button size="sm" className="rounded-xl">
                                查看
                              </Button>
                              <Button size="sm" variant="outline" className="rounded-xl">
                                下载
                              </Button>
                            </div>
                          </div>
                        ))}
                        <div className="rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                          这里后续建议接：文档搜索、版本树、标签筛选、权限控制、AI 摘要与智能归档。
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          <AgentPane />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
          {[
            {
              title: "模块映射",
              icon: Wrench,
              text: "主界面、节点子页面、文档管理三块已经按你的草图拆成可演示结构。",
            },
            {
              title: "平台通用化",
              icon: MessageSquare,
              text: "样例数据用了 RIS，但视觉与信息架构保留成通用项目交付平台。",
            },
            {
              title: "下一步可扩展",
              icon: Bot,
              text: "后续可以把 Agent、文档服务、工作流引擎和权限系统逐步接到真实后端。",
            },
          ].map((item) => (
            <Card key={item.title} className="rounded-2xl border-slate-200 shadow-soft">
              <CardContent className="flex items-start gap-3 p-4">
                <div className="rounded-2xl bg-slate-100 p-2">
                  <item.icon className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="font-medium">{item.title}</h3>
                  <p className="mt-1 text-sm text-slate-500">{item.text}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
