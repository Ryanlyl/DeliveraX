<#
.SYNOPSIS
  DeliveraX 推荐一键：需求分析(RA) → 方案(SD) → 代码生成(CG) → **RepairLoop** → CodeReview(CR) → 交付集成(DI，门闸通过时)。

.DESCRIPTION
  - 不改变各模块内部逻辑；本脚本只做顺序编排与路径变量。
  - RepairLoop 后**无论是否绿**，仍会跑 CodeReview（符合「测试失败仍可出评审」的冻结约定）。
  - **DeliveryIntegration**：仅当 RepairLoop 测通且 CodeReview 成功（未 -SkipCodeReview）时自动执行；否则跳过并在控制台说明原因。
  - 进程退出码：若 RepairLoop 未测通 **或** CodeReview CLI 退出非 0 **或** DeliveryIntegration 非 0，则本脚本最终以非 0 结束。

.PARAMETER RepoPath
  目标业务仓库根（如 TODO4Test），将传给 SolutionDesign / CodeGen / RepairLoop。

.PARAMETER EnvFile
  可选 `.env`，加载 `DEEPSEEK_*` / `OPENAI_*` / `CODETEST_*` 等（单行 KEY=VALUE）。

.PARAMETER RequirementFile
  若提供则从文件读取需求原文；否则使用 -RequirementText。

.PARAMETER PipelinePrefix
  任务前缀（字母数字与下划线），用于 RA run-id 与各 task-id 后缀对齐。默认自动生成。

.PARAMETER MaxRepairIterations
  传给 RepairLoop --max-iterations（默认 5）。

.PARAMETER SkipCodeReview
  若指定，RepairLoop 之后不跑 CodeReview（同时不会跑 DeliveryIntegration）。

.PARAMETER SkipDeliveryIntegration
  若指定，不跑 DeliveryIntegration（即使测试与评审均已通过）。

.PARAMETER DeliveryNoLlm
  若指定，DeliveryIntegration 使用 --no-llm（不调用摘要 LLM）。

.EXAMPLE
  .\scripts\run_deliver_pipeline.ps1 -RepoPath 'D:\work\TODO4Test-main\TODO4Test-main' `
    -EnvFile 'D:\secrets\deepseek.env'
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string] $DxRoot = "",

    [Parameter(Mandatory = $true)]
    [string] $RepoPath,

    [Parameter(Mandatory = $false)]
    [string] $EnvFile = "",

    [Parameter(Mandatory = $false)]
    [string] $RequirementFile = "",

    [Parameter(Mandatory = $false)]
    [string] $RequirementText = "",

    [Parameter(Mandatory = $false)]
    [string] $PipelinePrefix = "",

    [Parameter(Mandatory = $false)]
    [int] $MaxRepairIterations = 5,

    [Parameter(Mandatory = $false)]
    [switch] $SkipCodeReview,

    [Parameter(Mandatory = $false)]
    [switch] $SkipDeliveryIntegration,

    [Parameter(Mandatory = $false)]
    [switch] $DeliveryNoLlm
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RequirementText)) {
    $defReq = Join-Path $PSScriptRoot "default_requirement_cn.txt"
    if (-not (Test-Path -LiteralPath $defReq)) { throw "Missing default requirement file: $defReq" }
    $RequirementText = Get-Content -LiteralPath $defReq -Raw -Encoding UTF8
}

function Import-DotEnvFile {
    param([string] $Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return }
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -match '^\s*#' -or $line -eq "") { return }
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            Set-Item -Path ("Env:{0}" -f $Matches[1]) -Value $Matches[2].Trim()
        }
    }
}

if (-not $DxRoot) {
    $DxRoot = Split-Path -Parent $PSScriptRoot
}
$DxRoot = (Resolve-Path -LiteralPath $DxRoot).Path
if (-not (Test-Path -LiteralPath $RepoPath)) {
    throw "RepoPath not found: $RepoPath"
}
$RepoPathResolved = (Resolve-Path -LiteralPath $RepoPath).Path
$RepoPathForward = $RepoPathResolved -replace '\\', '/'

Import-DotEnvFile -Path $EnvFile
if (-not $env:DEEPSEEK_BASE_URL) {
    $env:DEEPSEEK_BASE_URL = "https://api.deepseek.com"
}
if (-not $env:CODETEST_NODE_BIN_DIR -and (Test-Path -LiteralPath "D:\feishu_AI\Node.js")) {
    $env:CODETEST_NODE_BIN_DIR = "D:\feishu_AI\Node.js"
}

if (-not $PipelinePrefix) {
    $PipelinePrefix = "pipe_{0}" -f (Get-Date -Format "yyyyMMddHHmmss")
}
$PipelinePrefix = $PipelinePrefix -replace '[^a-zA-Z0-9_]', '_'
$RunIdRa = "{0}_ra" -f $PipelinePrefix
$TaskCg = "{0}_cg" -f $PipelinePrefix
$TaskCt = "{0}_ct" -f $PipelinePrefix
$TaskCr = "{0}_cr" -f $PipelinePrefix
$TaskDi = "{0}_di" -f $PipelinePrefix

$reqBody = $RequirementText
if ($RequirementFile) {
    if (-not (Test-Path -LiteralPath $RequirementFile)) { throw "RequirementFile not found: $RequirementFile" }
    $reqBody = Get-Content -LiteralPath $RequirementFile -Raw -Encoding UTF8
}

Write-Host "=== Delivera pipeline === DxRoot=$DxRoot Prefix=$PipelinePrefix Repo=$RepoPathResolved"

$tmpReq = Join-Path ([System.IO.Path]::GetTempPath()) ("deliver_req_{0}.txt" -f $PipelinePrefix)
[System.IO.File]::WriteAllText($tmpReq, $reqBody, [System.Text.UTF8Encoding]::new($false))

Push-Location (Join-Path $DxRoot "RequirementsAnalysis")
try {
    & python .\run.py --use-real-llm --output-dir outputs --run-id $RunIdRa --input-file $tmpReq
    if ($LASTEXITCODE -ne 0) { throw "RequirementsAnalysis failed exit $LASTEXITCODE" }
} finally {
    Pop-Location
}
Remove-Item -LiteralPath $tmpReq -Force -ErrorAction SilentlyContinue

$prd = Join-Path $DxRoot ("RequirementsAnalysis\outputs\{0}\requirement_prd.md" -f $RunIdRa)
$spec = Join-Path $DxRoot ("RequirementsAnalysis\outputs\{0}\requirement_spec.json" -f $RunIdRa)
if (-not (Test-Path -LiteralPath $prd)) { throw "Missing PRD: $prd (RA validation may have rejected input)" }

Push-Location (Join-Path $DxRoot "SolutionDesign")
try {
    & python .\run.py --requirement $prd --repo-path $RepoPathResolved --task-id $TaskCg --max-context-files 32
    if ($LASTEXITCODE -ne 0) { throw "SolutionDesign failed exit $LASTEXITCODE" }
} finally {
    Pop-Location
}

$designGlob = Join-Path $DxRoot "SolutionDesign\Output\technical_design_*.md"
$designFile = Get-ChildItem -Path $designGlob | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $designFile) { throw "No technical_design_*.md under SolutionDesign\Output" }
$designPath = $designFile.FullName
Write-Host "DESIGN=$designPath"

Push-Location (Join-Path $DxRoot "CodeGen")
try {
    & python .\run.py --design $designPath --repo-path $RepoPathResolved --task-id $TaskCg --workspace-dir (Join-Path $DxRoot "SolutionDesign\.workspace")
    if ($LASTEXITCODE -ne 0) { throw "CodeGen failed exit $LASTEXITCODE" }
} finally {
    Pop-Location
}

$codegenJson = Join-Path $DxRoot ("CodeGen\Output\{0}\codegen_result.json" -f $TaskCg)
if (-not (Test-Path -LiteralPath $codegenJson)) { throw "Missing $codegenJson" }

Push-Location (Join-Path $DxRoot "RepairLoop")
try {
    $ws = Join-Path $DxRoot "SolutionDesign\.workspace"
    & python .\run.py `
        --dx-root $DxRoot `
        --max-iterations $MaxRepairIterations `
        --codegen-task-id $TaskCg `
        --codetest-task-id $TaskCt `
        --design $designPath `
        --repo-path $RepoPathForward `
        --workspace-dir $ws `
        --requirement-path $spec `
        --initial-codegen-result $codegenJson
    $repairExit = $LASTEXITCODE
} finally {
    Pop-Location
}
Write-Host "RepairLoop exit code: $repairExit"

$codetestJson = Join-Path $DxRoot ("CodeTest\Output\{0}\code_test_result.json" -f $TaskCt)

if (-not $SkipCodeReview) {
    if (-not (Test-Path -LiteralPath $codetestJson)) { throw "Missing CodeTest result: $codetestJson" }
    $diffPath = Join-Path $DxRoot ("CodeGen\Output\{0}\code_changes.diff" -f $TaskCg)
    Push-Location (Join-Path $DxRoot "CodeReview")
    try {
        # RepairLoop may refresh codegen_result path in-process; reuse same json path on disk (updated each repair round).
        & python .\run.py `
            --test-result $codetestJson `
            --design $designPath `
            --diff $diffPath `
            --codegen-result $codegenJson `
            --requirement $spec `
            --task-id $TaskCr `
            --max-llm-calls 28
        $crExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    Write-Host "CodeReview exit code: $crExit"
} else {
    $crExit = 0
}

$diExit = 0
if (-not $SkipDeliveryIntegration) {
    if ($SkipCodeReview) {
        Write-Host "Skipping DeliveryIntegration: SkipCodeReview is set."
    } elseif ($repairExit -ne 0) {
        Write-Host "Skipping DeliveryIntegration: RepairLoop did not pass tests."
    } elseif ($crExit -ne 0) {
        Write-Host "Skipping DeliveryIntegration: CodeReview did not succeed."
    } else {
        $reviewJson = Join-Path $DxRoot ("CodeReview\Output\{0}\code_review_result.json" -f $TaskCr)
        if (-not (Test-Path -LiteralPath $reviewJson)) { throw "Missing CodeReview result: $reviewJson" }
        Push-Location (Join-Path $DxRoot "DeliveryIntegration")
        try {
            $diArgs = @(
                ".\run.py",
                "--codegen-result", $codegenJson,
                "--test-result", $codetestJson,
                "--review-result", $reviewJson,
                "--task-id", $TaskDi,
                "--force"
            )
            if ($DeliveryNoLlm) { $diArgs += "--no-llm" }
            & python @diArgs
            $diExit = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        Write-Host "DeliveryIntegration exit code: $diExit"
    }
} else {
    Write-Host "Skipped DeliveryIntegration (-SkipDeliveryIntegration)."
}

Write-Host "--- Summary ---"
Write-Host "RA outputs: $($DxRoot)\RequirementsAnalysis\outputs\$RunIdRa"
Write-Host "Design: $designPath"
Write-Host "CodeGen: $codegenJson"
Write-Host "RepairLoop summary: $($DxRoot)\CodeTest\Output\$TaskCt\pipeline_loop_summary.json"
Write-Host "CodeTest result: $codetestJson"
if (-not $SkipCodeReview) {
    Write-Host "CodeReview: $($DxRoot)\CodeReview\Output\$TaskCr\code_review_result.json"
}
if (-not $SkipDeliveryIntegration -and -not $SkipCodeReview -and $repairExit -eq 0 -and $crExit -eq 0) {
    Write-Host "DeliveryIntegration: $($DxRoot)\DeliveryIntegration\Output\$TaskDi"
}

$exit = 0
if ($repairExit -ne 0) { $exit = [Math]::Max($exit, 2) }
if (-not $SkipCodeReview -and $crExit -ne 0) { $exit = [Math]::Max($exit, $crExit) }
if (-not $SkipDeliveryIntegration -and -not $SkipCodeReview -and $repairExit -eq 0 -and $crExit -eq 0 -and $diExit -ne 0) {
    $exit = [Math]::Max($exit, $diExit)
}
exit $exit
