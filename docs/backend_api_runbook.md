## DeliveraX 后端跑通手册（按 server API + testdata/static）

本手册目标：在 Windows/PowerShell 下，按 `server/` 定义的 API **跑通后端编排系统**（创建 pipeline → 运行 stage → checkpoint 审批 → 读取 artifacts 落盘）。

> 说明：本手册聚焦 **API 与编排层的闭环**。`test`/`integration` 等阶段可能需要额外运行环境（node/npm、测试框架等），建议先按“最小闭环”跑到 `requirements`/`solution` 的 checkpoint，再逐步扩展。

### 0. 你需要知道的落盘结构（用于排错）

- **pipeline 记录**：`artifacts/_pipelines/<pipeline_id>.json`
- **stage 产物目录**：`artifacts/<pipeline_id>/<stage_id>/`
  - 标准文件：`input.json`、`result.json`、`manifest.json`、`logs.txt`、`human_output.md`
- **默认 stage 顺序**：`requirements -> solution -> code -> test -> review -> integration`
  - checkpoint stages：`requirements`、`solution`、`review`

### 1. 环境准备（不运行测试，只准备）

#### 1.0 Windows/PowerShell 启动前检查清单

- **工作目录**：确认你在 `DeliveraX/` 仓库根执行命令（包含 `server/ agents/ testdata/`）。
- **Python**：`python --version` 建议 3.10+。
- **pip 解释器一致**：统一使用 `python -m pip ...`，避免装到别的 Python/venv。
- **.env 位置**：`DeliveraX/.env`（与 `.env.example` 同级），不是 `server/.env`。
- **Artifacts 目录权限**：确保 `DeliveraX/artifacts/`（或你设置的 `DELIVERAX_ARTIFACTS_ROOT`）可写。
- **端口占用**：默认 8000，如冲突可在 `.env` 里设置 `DELIVERAX_PORT`。

#### 1.1 Python 依赖（至少后端 + 默认 stages）

在仓库根 `DeliveraX/` 依次安装（示例，按你们 README 的顺序即可）：

```powershell
cd d:\DeliveraX_Teemo\DeliveraX

python -m pip install -r .\agents\solution_design\requirements.txt
python -m pip install -r .\agents\code_generation\requirements.txt
python -m pip install -r .\agents\release_integration\requirements.txt
python -m pip install -r .\server\requirements.txt

# requirement_analysis 是可编辑安装（README 示例）
python -m pip install -e ".\agents\requirement_analysis[dev]"
```

> 如果你只想先跑 `GET /health`、`GET /api/stages`、`POST /api/pipelines`（不执行 stage），可以先只装 `server/requirements.txt`。

#### 1.2 配置 `.env`（真实 LLM）

在 `DeliveraX/.env` 填 key（参考 `.env.example`）。例如二选一：

- `DEEPSEEK_API_KEY=...`（provider id：`deepseek`）
- `QWEN_API_KEY=...`（provider id：`qwen`）

> FastAPI 启动时会自动从仓库根加载 `.env`；`GET /api/providers` 会显示 configured 是否为 true。

#### 1.3 可选：用环境变量覆盖 artifacts 根目录（便于隔离跑通产物）

默认情况下 artifacts 写入 `DeliveraX/artifacts/`。如果你希望写到别的目录，可以在 `.env` 里加：

```text
DELIVERAX_ARTIFACTS_ROOT=D:\tmp\deliverax_artifacts
```

> 跑通阶段建议先保持默认，避免路径问题。

### 2. 启动后端

```powershell
cd d:\DeliveraX_Teemo\DeliveraX
python .\server\run.py
```

默认地址：
- `http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

如果你看到 “NO LLM API KEYS FOUND” 的 warning：说明 `.env` 没被加载或 key 未生效，优先用第 4 节的 `/api/providers` 来确认。

### 3. 选择一个 testdata/static 用例

以 `testdata/static/<case>/` 为单位：
- **需求文本**：`requirement_r0_initial.txt`
- **目标仓库路径 repo_path**：`target\`

当前仓库内可用的 static cases（共 5 个）：
- `OSS01_startbootstrap_resume`
- `OSS02_startbootstrap_agency`
- `OSS03_startbootstrap_freelancer`
- `OSS04_startbootstrap_landing_page`
- `OSS05_startbootstrap_creative`

建议先从 **`OSS01_startbootstrap_resume`** 开始（目录与文件更少，便于先跑通编排与产物落盘）。

```powershell
$Case = "OSS01_startbootstrap_resume"
$DxRoot = "d:\DeliveraX_Teemo\DeliveraX"
$ReqPath = Join-Path $DxRoot "testdata\static\$Case\requirement_r0_initial.txt"
$RepoPath = Join-Path $DxRoot "testdata\static\$Case\target"
$Requirement = Get-Content -LiteralPath $ReqPath -Raw -Encoding UTF8
```

> 重要：`repo_path` 建议传 **绝对路径**（如上），因为后端会把它透传给各 stage；相对路径在不同 cwd 下可能解析失败。

### 4. API “面”确认（先不跑 stage）

```powershell
$Base = "http://127.0.0.1:8000"

Invoke-RestMethod -Method Get -Uri "$Base/health"
Invoke-RestMethod -Method Get -Uri "$Base/api/stages"
Invoke-RestMethod -Method Get -Uri "$Base/api/providers"
```

预期：
- `/health` 返回 `{"status":"ok"}`
- `/api/providers` 中你选择的 provider（如 `deepseek`/`qwen`）显示 `configured: true`

如 `/api/stages` 报 500：通常是 `default_pipeline.json` 中某个 `module` import 时依赖未安装；先按 1.1 把相关 agents 依赖装齐。

### 5. 最小闭环（推荐）：创建 pipeline → 跑 requirements → 读取 artifacts → 审批

#### 5.1 创建 pipeline

建议显式指定 `provider` 为真实 provider（`deepseek` 或 `qwen`），避免默认 `local` 导致 `local_only`：

```powershell
$PipelineCreate = @{
  name = "static-$Case"
  requirement = $Requirement
  repo_path = $RepoPath
  provider = "deepseek"   # 或 "qwen"
} | ConvertTo-Json -Depth 20

$Pipe = Invoke-RestMethod -Method Post -Uri "$Base/api/pipelines" -ContentType "application/json" -Body $PipelineCreate
$PipelineId = $Pipe.id
$PipelineId
```

你也可以先固定一个可读的 `pipeline_id`：

```powershell
$PipelineCreate = @{
  pipeline_id = "static-$Case-demo"
  name = "static-$Case"
  requirement = $Requirement
  repo_path = $RepoPath
  provider = "deepseek"
} | ConvertTo-Json -Depth 20
```

#### 5.2 运行 requirements stage（checkpoint：会进入 pending_approval）

```powershell
$StageRunBody = @{ } | ConvertTo-Json
$Pipe2 = Invoke-RestMethod -Method Post -Uri "$Base/api/pipelines/$PipelineId/stages/requirements/run" -ContentType "application/json" -Body $StageRunBody
($Pipe2.stages | Where-Object { $_.id -eq "requirements" }).status
```

预期：`requirements.status` 为 `pending_approval`（该 stage 是 checkpoint）。

#### 5.3 读取 stage artifacts（列表 + 文件）

```powershell
$Artifacts = Invoke-RestMethod -Method Get -Uri "$Base/api/pipelines/$PipelineId/stages/requirements/artifacts"
$Artifacts.standard_artifacts

# 读取 human_output（如果存在）
$HumanPath = $Artifacts.standard_artifacts.human_output
if ($HumanPath) {
  Invoke-RestMethod -Method Get -Uri "$Base/api/artifacts/file?path=$([uri]::EscapeDataString($HumanPath))"
}
```

#### 5.4 审批（两套 API 都能用）

**方式 A：legacy stage approve（推荐给前端/旧调用方）**

```powershell
$Approve = @{
  reviewer = "human"
  comment = "ok"
  continue_pipeline = $false
} | ConvertTo-Json

$Pipe3 = Invoke-RestMethod -Method Post -Uri "$Base/api/pipelines/$PipelineId/stages/requirements/approve" -ContentType "application/json" -Body $Approve
($Pipe3.stages | Where-Object { $_.id -eq "requirements" }).status
```

预期：`requirements.status` 变为 `succeeded`。

**方式 B：checkpoint approve（更“正统”的 checkpoint API）**

```powershell
$Current = Invoke-RestMethod -Method Get -Uri "$Base/api/pipelines/$PipelineId/checkpoints/current"
$CheckpointId = $Current.checkpoint.id

$Approve2 = @{
  reviewer = "human"
  comment = "ok"
  continue_pipeline = $false
} | ConvertTo-Json

$Pipe4 = Invoke-RestMethod -Method Post -Uri "$Base/api/checkpoints/$CheckpointId/approve" -ContentType "application/json" -Body $Approve2
```

### 6. 扩展到 solution checkpoint（同样的闭环）

`solution` 也是 checkpoint，步骤与 `requirements` 相同：
- `POST /api/pipelines/{id}/stages/solution/run`
- `GET /api/pipelines/{id}/stages/solution/artifacts`
- approve（stage approve 或 checkpoint approve）

### 7. Runner（后台线程）模式：/start → /runs/{run_id} → approve → 自动继续

当你确认单 stage 没问题后，再启用 runner 模式验证“自动推进 + 停在 checkpoint + resume”：

```powershell
$Run = Invoke-RestMethod -Method Post -Uri "$Base/api/pipelines/$PipelineId/start" -ContentType "application/json" -Body (@{} | ConvertTo-Json)
$RunId = $Run.id

# 观察 run 状态
Invoke-RestMethod -Method Get -Uri "$Base/api/pipelines/$PipelineId/runs/$RunId"
```

预期：
- 初始 `status=running`
- 遇到 checkpoint 后进入 `pending_approval` 并停住（run 的 `current_stage_id` 对应该 stage）
- approve 后 runner 会继续跑下一个 stage

#### 7.1 推荐观察字段（/runs/{run_id} 返回）

- **status**：`queued/running/pending_approval/paused/succeeded/failed/rejected/terminated`
- **current_stage_id**：当前正在执行或阻塞在 checkpoint 的 stage
- **next_stage_id**：runner 规划的下一 stage
- **completed_stage_ids**：runner 认为已完成的 stages（与 pipeline record 互相镜像）
- **pause_requested / terminate_requested**：对应 `/pause` `/terminate`

#### 7.2 runner 被 checkpoint 卡住时的“继续”方式

runner 卡在 `pending_approval` 时，有两条路继续，二选一即可：

- **方式 A：stage approve（legacy）**：`POST /api/pipelines/{pipeline_id}/stages/{stage_id}/approve`\n  - 如果请求体里 `continue_pipeline=true`，服务会调用 `pipeline_runner.resume_run(...)` 继续后台执行。
- **方式 B：checkpoint approve**：\n  - 先 `GET /api/pipelines/{pipeline_id}/checkpoints/current` 取 `checkpoint.id`\n  - 再 `POST /api/checkpoints/{checkpoint_id}/approve`，请求体同样支持 `continue_pipeline=true`\n
示例（以 solution 为例，批准后继续）：

```powershell
$Current = Invoke-RestMethod -Method Get -Uri "$Base/api/pipelines/$PipelineId/checkpoints/current"
$CheckpointId = $Current.checkpoint.id
$StageId = $Current.checkpoint.stage_id

$ApproveAndContinue = @{
  reviewer = "human"
  comment = "approve and continue"
  continue_pipeline = $true
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "$Base/api/checkpoints/$CheckpointId/approve" -ContentType "application/json" -Body $ApproveAndContinue

# 继续观察 run
Invoke-RestMethod -Method Get -Uri "$Base/api/pipelines/$PipelineId/runs/$RunId"
```

#### 7.3 review 被 reject 后的预期（会触发 rerun_required）

当 `review` stage 被驳回时（`POST /api/pipelines/{id}/stages/review/reject` 或 checkpoint reject）：\n+- `review.status` 变为 `rejected`\n+- 上游 `test` stage 会被重置为 `queued`，并在 `test.data` 标记 `rerun_required=true`，同时追加一条 `rerun_input_artifacts`（包含 reject_reason）。\n+\n+这用于让 runner/人手后续重新跑测试并带上驳回原因。

### 8. 常见问题快速定位

- **/api/providers configured=false**：`.env` 未被加载或 key 名不对。确认 `.env` 在 `DeliveraX/` 根目录，变量名为 `DEEPSEEK_API_KEY` 或 `QWEN_API_KEY`。
- **stage 执行报 409：Stage is not connected yet**：对应 stage 在 registry 中 `module` 为空或 import 失败。检查 `default_pipeline.json` 的 `module`，以及该模块在 `agents/` 下是否可 import（依赖是否已安装）。
- **看产物但列表为空**：先看 `artifacts/<pipeline_id>/<stage_id>/manifest.json` 是否存在；若无，说明 stage 可能未落盘成功或未写 manifest。
- **路径读取 400：UNSAFE_ARTIFACT_PATH**：`/api/artifacts/file?path=` 只能读 `DELIVERAX_ARTIFACTS_ROOT`（默认 `DeliveraX/artifacts`）之下的绝对路径。

