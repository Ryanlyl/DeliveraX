# DeliveraX Server

`server/` 是 DeliveraX 的 FastAPI 编排层。它负责创建 pipeline、调用各阶段统一 `run_stage()` 入口、保存阶段状态，并读取 `artifacts/` 下的标准产物。

## 目录定位

```text
server/
|-- run.py
|-- requirements.txt
`-- api_server/
    |-- main.py
    |-- config.py
    |-- stage_registry.py
    |-- routers/
    |-- services/
    `-- storage/
```

阶段内部逻辑留在 `agents/` 下的各模块里。API 层只依赖 `stage_contracts` 和各阶段暴露的 `run_stage(request)`。

## 安装与启动

```powershell
cd E:\DeliveraX
python -m pip install -r .\server\requirements.txt
python .\server\run.py
```

默认服务地址：

```text
http://127.0.0.1:8000
```

交互式 API 文档：

```text
http://127.0.0.1:8000/docs
```

## 核心接口

```text
GET  /health
GET  /api/stages
POST /api/pipelines
GET  /api/pipelines
GET  /api/pipelines/{pipeline_id}
GET  /api/pipelines/{pipeline_id}/stages/{stage_id}
POST /api/pipelines/{pipeline_id}/run
POST /api/pipelines/{pipeline_id}/stages/{stage_id}/run
POST /api/pipelines/{pipeline_id}/stages/{stage_id}/approve
POST /api/pipelines/{pipeline_id}/stages/{stage_id}/reject
GET  /api/pipelines/{pipeline_id}/stages/{stage_id}/artifacts
GET  /api/artifacts/file?path=<artifact_path>
```

## 快速请求示例

创建 pipeline：

```powershell
$body = @{
  name = "AI DevFlow Pipeline"
  requirement = "将任务列表页中的完成按钮调整为更醒目的主按钮样式。"
  repo_path = "E:\DeliveraX\frontend"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/pipelines `
  -ContentType "application/json" `
  -Body $body
```

运行需求分析阶段：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/pipelines/<pipeline_id>/stages/requirements/run `
  -ContentType "application/json" `
  -Body "{}"
```

默认情况下，需求分析阶段会返回 `pending_approval`。如果需要本地冒烟时直接通过审批，可在创建或运行阶段时传入：

```json
{
  "options": {
    "requires_approval": false
  }
}
```

审批后继续执行后续阶段：

```powershell
$approval = @{
  reviewer = "human"
  comment = "需求范围确认通过"
  continue_pipeline = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/pipelines/<pipeline_id>/stages/requirements/approve `
  -ContentType "application/json" `
  -Body $approval
```
