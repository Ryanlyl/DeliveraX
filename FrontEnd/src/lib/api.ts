export type Stage = {
  id: string;
  name: string;
  description: string;
};

export type Project = {
  id: string;
  name: string;
  industry: string;
  status: string;
  progress: number;
  summary: string;
  owner: string;
  tags: string[];
  current_stage_id: string;
  current_stage?: Stage | null;
};

export type ProjectFile = {
  id: string;
  project_id: string;
  stage_id: string;
  kind: "meeting_note" | "draft_json" | "latex_doc";
  name: string;
  original_name: string;
  status: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
  source_file_id?: string | null;
  generated_by_job_id?: string | null;
  download_url: string;
  content_url: string;
};

export type Job = {
  id: string;
  project_id: string;
  stage_id: string;
  type: string;
  status: "queued" | "running" | "completed" | "failed";
  payload: Record<string, string>;
  message: string;
  error: string | null;
  output_file_ids: string[];
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type StageDetail = {
  project: Project;
  stage: Stage;
  stages: Stage[];
  files: {
    meeting_notes: ProjectFile[];
    draft_jsons: ProjectFile[];
    latex_docs: ProjectFile[];
  };
  jobs: Job[];
  can_run: {
    meeting_agent: boolean;
    info_cpl_agent: boolean;
  };
};

export type FileContent = {
  file_id: string;
  content: string;
  truncated: boolean;
  encoding: string;
};

type ProjectsResponse = {
  items: Project[];
  stages: Stage[];
};

type FileResponse = {
  item: ProjectFile;
};

type JobResponse = {
  item: Job;
};

type FileContentResponse = {
  item: FileContent;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function toErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }

  return "请求失败，请稍后重试。";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const detail =
      (payload && typeof payload === "object" && "detail" in payload && String(payload.detail)) ||
      `请求失败 (${response.status})`;
    throw new Error(detail);
  }

  return payload as T;
}

export function getApiUrl(path: string) {
  return `${API_BASE}${path}`;
}

export function formatTimestamp(value: string | null) {
  if (!value) {
    return "未开始";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }

  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }

  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

export async function getProjects() {
  return request<ProjectsResponse>("/api/projects");
}

export async function getStageDetail(projectId: string, stageId: string) {
  return request<StageDetail>(`/api/projects/${projectId}/stages/${stageId}`);
}

export async function uploadMeetingNote(projectId: string, stageId: string, file: File) {
  const formData = new FormData();
  formData.append("stage_id", stageId);
  formData.append("file", file);

  return request<FileResponse>(`/api/projects/${projectId}/meeting-notes`, {
    method: "POST",
    body: formData,
  });
}

export async function runMeetingAgent(
  projectId: string,
  sourceFileId: string,
  mode: "local" | "api",
) {
  return request<JobResponse>(`/api/projects/${projectId}/jobs/meeting-agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_file_id: sourceFileId, mode }),
  });
}

export async function runInfoCplAgent(
  projectId: string,
  draftFileId: string,
  mode: "local" | "api",
) {
  return request<JobResponse>(`/api/projects/${projectId}/jobs/info-cpl-agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft_file_id: draftFileId, mode }),
  });
}

export async function getJob(jobId: string) {
  return request<JobResponse>(`/api/jobs/${jobId}`);
}

export async function getFileContent(fileId: string) {
  return request<FileContentResponse>(`/api/files/${fileId}/content`);
}

export { toErrorMessage };
