import { useDeferredValue, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Download,
  Eye,
  FileCode2,
  FolderKanban,
  Loader2,
  Play,
  Search,
  Upload,
  WandSparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  formatFileSize,
  formatTimestamp,
  getApiUrl,
  getFileContent,
  getJob,
  getProjects,
  getStageDetail,
  runInfoCplAgent,
  runMeetingAgent,
  type FileContent,
  type Job,
  type Project,
  type ProjectFile,
  type Stage,
  type StageDetail,
  toErrorMessage,
  uploadMeetingNote,
} from "@/lib/api";

function StatusBadge({ value }: { value: string }) {
  const tone =
    value === "completed" || value === "已完成"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : value === "failed"
        ? "border-rose-200 bg-rose-50 text-rose-700"
        : value === "running" || value === "queued" || value === "进行中"
          ? "border-amber-200 bg-amber-50 text-amber-700"
          : "border-slate-200 bg-slate-50 text-slate-700";
  return <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${tone}`}>{value}</span>;
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
      <div className="font-medium text-slate-700">{title}</div>
      <p className="mt-2 leading-6">{description}</p>
    </div>
  );
}

function flattenFiles(detail: StageDetail | null) {
  if (!detail) return [];
  return [...detail.files.latex_docs, ...detail.files.draft_jsons, ...detail.files.meeting_notes];
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [selectedStageId, setSelectedStageId] = useState("");
  const [stageDetail, setStageDetail] = useState<StageDetail | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [stageLoading, setStageLoading] = useState(false);
  const [selectedUploadFile, setSelectedUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [meetingMode, setMeetingMode] = useState<"local" | "api">("local");
  const [infoMode, setInfoMode] = useState<"local" | "api">("local");
  const [selectedMeetingNoteId, setSelectedMeetingNoteId] = useState("");
  const [selectedDraftFileId, setSelectedDraftFileId] = useState("");
  const [activeJobId, setActiveJobId] = useState("");
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [runningAction, setRunningAction] = useState<"" | "meeting" | "info">("");
  const [previewFileId, setPreviewFileId] = useState("");
  const [previewContent, setPreviewContent] = useState<FileContent | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  const deferredSearch = useDeferredValue(search.trim().toLowerCase());

  useEffect(() => {
    let ignore = false;
    getProjects()
      .then((response) => {
        if (ignore) return;
        setProjects(response.items);
        setStages(response.stages);
        if (response.items[0]) {
          setSelectedProjectId((current) => current || response.items[0].id);
          setSelectedStageId((current) => current || response.items[0].current_stage_id);
        }
      })
      .catch((reason) => !ignore && setError(toErrorMessage(reason)))
      .finally(() => !ignore && setProjectsLoading(false));
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedProjectId || !selectedStageId) return;
    let ignore = false;
    setStageLoading(true);
    getStageDetail(selectedProjectId, selectedStageId)
      .then((detail) => {
        if (ignore) return;
        setStageDetail(detail);
        setError("");
      })
      .catch((reason) => !ignore && setError(toErrorMessage(reason)))
      .finally(() => !ignore && setStageLoading(false));
    return () => {
      ignore = true;
    };
  }, [selectedProjectId, selectedStageId]);

  useEffect(() => {
    if (!stageDetail) return;
    if (!stageDetail.files.meeting_notes.some((file) => file.id === selectedMeetingNoteId)) {
      setSelectedMeetingNoteId(stageDetail.files.meeting_notes[0]?.id || "");
    }
    if (!stageDetail.files.draft_jsons.some((file) => file.id === selectedDraftFileId)) {
      setSelectedDraftFileId(stageDetail.files.draft_jsons[0]?.id || "");
    }
    const candidates = flattenFiles(stageDetail);
    if (!candidates.some((file) => file.id === previewFileId)) {
      setPreviewFileId(candidates[0]?.id || "");
    }
  }, [previewFileId, selectedDraftFileId, selectedMeetingNoteId, stageDetail]);

  useEffect(() => {
    if (!previewFileId) {
      setPreviewContent(null);
      setPreviewError("");
      return;
    }
    let ignore = false;
    setPreviewLoading(true);
    getFileContent(previewFileId)
      .then((response) => {
        if (ignore) return;
        setPreviewContent(response.item);
        setPreviewError("");
      })
      .catch((reason) => !ignore && setPreviewError(toErrorMessage(reason)))
      .finally(() => !ignore && setPreviewLoading(false));
    return () => {
      ignore = true;
    };
  }, [previewFileId]);

  useEffect(() => {
    if (!activeJobId || !selectedProjectId || !selectedStageId) return;
    let cancelled = false;
    let timeoutId = 0;
    const poll = async () => {
      try {
        const response = await getJob(activeJobId);
        if (cancelled) return;
        setActiveJob(response.item);
        if (response.item.status === "completed" || response.item.status === "failed") {
          const detail = await getStageDetail(selectedProjectId, selectedStageId);
          if (cancelled) return;
          setStageDetail(detail);
          if (response.item.status === "completed") {
            if (response.item.type === "info_cpl_agent" && detail.files.latex_docs[0]) {
              setPreviewFileId(detail.files.latex_docs[0].id);
            }
            if (response.item.type === "meeting_agent" && detail.files.draft_jsons[0]) {
              setPreviewFileId(detail.files.draft_jsons[0].id);
            }
          }
          setRunningAction("");
          setActiveJobId("");
          return;
        }
        timeoutId = window.setTimeout(poll, 1500);
      } catch (reason) {
        if (!cancelled) {
          setError(toErrorMessage(reason));
          setRunningAction("");
          setActiveJobId("");
        }
      }
    };
    poll();
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [activeJobId, selectedProjectId, selectedStageId]);

  const filteredProjects = projects.filter((project) =>
    !deferredSearch ||
    `${project.name} ${project.industry} ${project.owner} ${project.tags.join(" ")}`
      .toLowerCase()
      .includes(deferredSearch),
  );

  const previewFiles = flattenFiles(stageDetail);
  const previewFile = previewFiles.find((file) => file.id === previewFileId) || null;
  const selectedProject = projects.find((project) => project.id === selectedProjectId) || null;

  async function refreshStage() {
    if (!selectedProjectId || !selectedStageId) return;
    setStageDetail(await getStageDetail(selectedProjectId, selectedStageId));
  }

  async function handleUpload() {
    if (!selectedUploadFile || !selectedProjectId || !selectedStageId) return;
    setUploading(true);
    try {
      await uploadMeetingNote(selectedProjectId, selectedStageId, selectedUploadFile);
      await refreshStage();
      setSelectedUploadFile(null);
      setError("");
    } catch (reason) {
      setError(toErrorMessage(reason));
    } finally {
      setUploading(false);
    }
  }

  async function handleRunMeetingAgent() {
    if (!selectedProjectId || !selectedMeetingNoteId) return;
    setRunningAction("meeting");
    try {
      const response = await runMeetingAgent(selectedProjectId, selectedMeetingNoteId, meetingMode);
      setActiveJob(response.item);
      setActiveJobId(response.item.id);
      setError("");
    } catch (reason) {
      setError(toErrorMessage(reason));
      setRunningAction("");
    }
  }

  async function handleRunInfoAgent() {
    if (!selectedProjectId || !selectedDraftFileId) return;
    setRunningAction("info");
    try {
      const response = await runInfoCplAgent(selectedProjectId, selectedDraftFileId, infoMode);
      setActiveJob(response.item);
      setActiveJobId(response.item.id);
      setError("");
    } catch (reason) {
      setError(toErrorMessage(reason));
      setRunningAction("");
    }
  }

  const fileSections: Array<{ title: string; files: ProjectFile[] }> = [
    { title: "会议纪要", files: stageDetail?.files.meeting_notes || [] },
    { title: "结构化需求草稿 JSON", files: stageDetail?.files.draft_jsons || [] },
    { title: "LaTeX 输出", files: stageDetail?.files.latex_docs || [] },
  ];

  return (
    <div className="min-h-screen px-4 py-6 md:px-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="rounded-[2rem] border border-slate-200 bg-white/90 p-6 shadow-sm">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl bg-slate-900 p-3 text-white">
                  <FolderKanban className="h-5 w-5" />
                </div>
                <div>
                  <h1 className="text-2xl font-semibold tracking-tight text-slate-900">DeliveraX</h1>
                  <p className="mt-1 text-sm text-slate-500">面向于需求到交付的全链路智能助手，Agent助力高效办公。</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">需求</Badge>
                <Badge variant="secondary">方案</Badge>
                <Badge variant="secondary">研发</Badge>
                <Badge variant="secondary">测试</Badge>
                <Badge variant="secondary">交付</Badge>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {selectedProject ? `当前项目：${selectedProject.name}` : "正在加载项目..."}
            </div>
          </div>
        </section>

        {error ? (
          <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.05fr_1.75fr]">
          <Card className="rounded-3xl shadow-sm">
            <CardHeader className="border-b border-slate-100">
              <CardTitle className="text-base">项目列表</CardTitle>
              <div className="relative mt-4">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索项目" className="pl-9" />
              </div>
            </CardHeader>
            <CardContent className="space-y-3 p-4">
              {projectsLoading ? (
                <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  正在加载项目...
                </div>
              ) : filteredProjects.length === 0 ? (
                <EmptyState title="没有匹配项目" description="换一个关键词试试。" />
              ) : (
                filteredProjects.map((project) => (
                  <button
                    key={project.id}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      project.id === selectedProjectId ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                    onClick={() => {
                      setSelectedProjectId(project.id);
                      setSelectedStageId(project.current_stage_id);
                    }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-base font-medium">{project.name}</div>
                        <p className={`mt-2 text-sm leading-6 ${project.id === selectedProjectId ? "text-slate-200" : "text-slate-500"}`}>
                          {project.summary}
                        </p>
                      </div>
                      <StatusBadge value={project.status} />
                    </div>
                    <div className={`mt-3 flex flex-wrap gap-2 text-xs ${project.id === selectedProjectId ? "text-slate-200" : "text-slate-500"}`}>
                      <span>{project.industry}</span>
                      <span>负责人：{project.owner}</span>
                      <span>阶段：{project.current_stage?.name || project.current_stage_id}</span>
                    </div>
                  </button>
                ))
              )}
            </CardContent>
          </Card>

          <div className="min-w-0 space-y-6">
            <Card className="rounded-3xl shadow-sm">
              <CardHeader className="border-b border-slate-100">
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <CardTitle className="text-base">阶段工作台</CardTitle>
                      <p className="mt-2 text-sm text-slate-500">上传待处理文件，系统自动建库，全流程自动化，中间文件可随时下载，便于人工审核</p>
                    </div>
                    {stageLoading ? <Loader2 className="h-4 w-4 animate-spin text-slate-500" /> : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(stageDetail?.stages || stages).map((stage) => (
                      <Button key={stage.id} size="sm" variant={selectedStageId === stage.id ? "default" : "outline"} onClick={() => setSelectedStageId(stage.id)}>
                        {stage.name}
                      </Button>
                    ))}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-6 p-4 lg:grid-cols-2">
                <div className="space-y-4 rounded-2xl border border-slate-200 p-4">
                  <div className="font-medium text-slate-900">会议纪要智能处理</div>
                  <input type="file" accept=".txt" onChange={(event) => setSelectedUploadFile(event.target.files?.[0] || null)} className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-xl file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:text-white" />
                  <Button onClick={handleUpload} disabled={!selectedUploadFile || uploading} className="w-full">
                    {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                    {uploading ? "上传中..." : "上传到当前阶段"}
                  </Button>
                  <select value={selectedMeetingNoteId} onChange={(event) => setSelectedMeetingNoteId(event.target.value)} className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900">
                    <option value="">请选择会议纪要</option>
                    {stageDetail?.files.meeting_notes.map((file) => <option key={file.id} value={file.id}>{file.original_name}</option>)}
                  </select>
                  <select value={meetingMode} onChange={(event) => setMeetingMode(event.target.value as "local" | "api")} className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900">
                    <option value="local">local: 本地规则抽取</option>
                    <option value="api">api: 调模型抽取</option>
                  </select>
                  <Button onClick={handleRunMeetingAgent} disabled={!selectedMeetingNoteId || runningAction !== ""} className="w-full">
                    {runningAction === "meeting" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                    Meeting Agent
                  </Button>
                </div>

                <div className="space-y-4 rounded-2xl border border-slate-200 p-4">
                  <div className="font-medium text-slate-900">信息补全助手</div>
                  <div className="rounded-2xl bg-slate-50 p-3 text-sm leading-6 text-slate-600">
                    优先使用项目数据库信息补全，如果数据库信息不足，则调用大模型进行补全，生成最终的 TeX 输出，供人工审核和修改。
                  </div>
                  <select value={selectedDraftFileId} onChange={(event) => setSelectedDraftFileId(event.target.value)} className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900">
                    <option value="">请选择 draft JSON</option>
                    {stageDetail?.files.draft_jsons.map((file) => <option key={file.id} value={file.id}>{file.original_name}</option>)}
                  </select>
                  <select value={infoMode} onChange={(event) => setInfoMode(event.target.value as "local" | "api")} className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900">
                    <option value="local">local: 本地生成 TeX 草稿</option>
                    <option value="api">api: 调模型生成 TeX</option>
                  </select>
                  <Button onClick={handleRunInfoAgent} disabled={!selectedDraftFileId || runningAction !== ""} className="w-full">
                    {runningAction === "info" ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
                    Info CPL Agent
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {fileSections.slice(0, 2).map((section) => (
                <Card key={section.title} className="min-w-0 rounded-3xl shadow-sm">
                  <CardHeader><CardTitle className="text-base">{section.title}</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    {section.files.length === 0 ? <EmptyState title="暂无文件" description="先运行上游步骤。" /> : section.files.map((file) => (
                      <div key={file.id} className={`rounded-2xl border p-4 ${previewFileId === file.id ? "border-slate-900 bg-slate-50" : "border-slate-200"}`}>
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="truncate font-medium text-slate-900">{file.original_name}</div>
                            <p className="mt-1 text-sm text-slate-500">{formatFileSize(file.size_bytes)} · {formatTimestamp(file.updated_at)}</p>
                          </div>
                          <StatusBadge value={file.status} />
                        </div>
                        <div className="mt-3 flex gap-2">
                          <Button size="sm" variant={previewFileId === file.id ? "default" : "outline"} onClick={() => setPreviewFileId(file.id)}>
                            <Eye className="h-4 w-4" />
                            预览
                          </Button>
                          <a href={getApiUrl(file.download_url)} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50">
                            <Download className="h-4 w-4" />
                            下载
                          </a>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="min-w-0 rounded-3xl shadow-sm">
                <CardHeader><CardTitle className="text-base">LaTeX 输出</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  {fileSections[2].files.length === 0 ? <EmptyState title="暂无输出" description="运行 Info CPL Agent 后这里会出现 TeX 文件。" /> : fileSections[2].files.map((file) => (
                    <div key={file.id} className={`rounded-2xl border p-4 ${previewFileId === file.id ? "border-slate-900 bg-slate-50" : "border-slate-200"}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="truncate font-medium text-slate-900">{file.original_name}</div>
                          <p className="mt-1 text-sm text-slate-500">{formatFileSize(file.size_bytes)} · {formatTimestamp(file.updated_at)}</p>
                        </div>
                        <StatusBadge value={file.status} />
                      </div>
                      <div className="mt-3 flex gap-2">
                        <Button size="sm" variant={previewFileId === file.id ? "default" : "outline"} onClick={() => setPreviewFileId(file.id)}>
                          <Eye className="h-4 w-4" />
                          预览
                        </Button>
                        <a href={getApiUrl(file.download_url)} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50">
                          <Download className="h-4 w-4" />
                          下载
                        </a>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="min-w-0 rounded-3xl shadow-sm">
                <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Clock3 className="h-4 w-4" />任务状态</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  {activeJob ? (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="font-medium text-slate-900">当前任务</div>
                          <p className="mt-1 text-sm text-slate-500">{activeJob.message}</p>
                        </div>
                        <StatusBadge value={activeJob.status} />
                      </div>
                    </div>
                  ) : null}
                  {stageDetail?.jobs.length ? stageDetail.jobs.map((job) => (
                    <div key={job.id} className="rounded-2xl border border-slate-200 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="font-medium text-slate-900">{job.type === "meeting_agent" ? "Meeting Agent" : "Info CPL Agent"}</div>
                          <p className="mt-1 text-sm text-slate-500">创建于 {formatTimestamp(job.created_at)} · 完成于 {formatTimestamp(job.finished_at)}</p>
                        </div>
                        <StatusBadge value={job.status} />
                      </div>
                      {"mode" in job.payload ? <p className="mt-2 text-xs text-slate-500">模式：{job.payload.mode}</p> : null}
                      {job.error ? <p className="mt-2 text-sm text-rose-600">{job.error}</p> : null}
                    </div>
                  )) : <EmptyState title="暂无任务" description="上传会议纪要后即可触发任务。" />}
                </CardContent>
              </Card>
            </div>

            <Card className="min-w-0 rounded-3xl shadow-sm">
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <FileCode2 className="h-4 w-4" />
                    文件预览
                  </CardTitle>
                  {previewFile ? <Badge variant="secondary">{previewFile.kind}</Badge> : null}
                </div>
              </CardHeader>
              <CardContent className="min-w-0 space-y-4">
                {!previewFile ? (
                  <EmptyState title="暂无可预览文件" description="跑通一次流程后，这里会直接展示会议纪要、JSON 或 TeX 内容。" />
                ) : (
                  <>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <div className="font-medium text-slate-900">{previewFile.original_name}</div>
                      <p className="mt-1 text-sm text-slate-500">更新时间 {formatTimestamp(previewFile.updated_at)}</p>
                    </div>
                    {previewLoading ? (
                      <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        正在加载文件内容...
                      </div>
                    ) : previewError ? (
                      <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{previewError}</div>
                    ) : (
                      <pre className="max-h-[30rem] max-w-full overflow-auto whitespace-pre-wrap break-all rounded-2xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">{previewContent?.content || "暂无内容"}</pre>
                    )}
                    {previewContent?.truncated ? <p className="text-xs text-slate-500">内容已截断显示，完整内容请下载查看。</p> : null}
                  </>
                )}
              </CardContent>
            </Card>

            <Card className="rounded-3xl shadow-sm">
              <CardContent className="flex items-start gap-3 p-5">
                <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-600" />
                <div className="text-sm leading-6 text-slate-600">
                  这是一个 DeliveraX 的演示版本，展示了一个面向需求到交付全链路的智能助手系统。通过上传会议纪要，系统可以自动抽取关键信息，生成结构化的需求草稿，并最终输出 TeX 格式的文档，供人工审核和修改。这个流程中的每一步都可以查看中间文件和任务状态，确保整个过程的透明和可控。
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
