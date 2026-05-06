param(
  [Parameter(Mandatory = $true)]
  [string]$RepoUrl,

  [Parameter(Mandatory = $true)]
  [string]$TargetDir,

  [int]$MaxRetries = 5,
  [int]$InitialBackoffSeconds = 1,
  [int]$MaxBackoffSeconds = 20,
  [switch]$ReuseExisting
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-GitRepo {
  param([Parameter(Mandatory = $true)][string]$Path)

  $gitPath = Join-Path $Path ".git"
  if (-not (Test-Path $gitPath)) {
    return $false
  }

  & git -C $Path rev-parse --is-inside-work-tree *> $null
  return ($LASTEXITCODE -eq 0)
}

function Invoke-GitCloneAttempt {
  param(
    [Parameter(Mandatory = $true)][string]$RepoUrl,
    [Parameter(Mandatory = $true)][string]$TargetDir
  )

  $stdoutFile = [System.IO.Path]::GetTempFileName()
  $stderrFile = [System.IO.Path]::GetTempFileName()

  try {
    $proc = Start-Process `
      -FilePath "git" `
      -ArgumentList @("clone", $RepoUrl, $TargetDir) `
      -Wait `
      -PassThru `
      -NoNewWindow `
      -RedirectStandardOutput $stdoutFile `
      -RedirectStandardError $stderrFile

    $stdout = ""
    $stderr = ""
    if (Test-Path $stdoutFile) { $stdout = [string](Get-Content $stdoutFile -Raw) }
    if (Test-Path $stderrFile) { $stderr = [string](Get-Content $stderrFile -Raw) }

    return [pscustomobject]@{
      exit_code = $proc.ExitCode
      stdout    = ([string]$stdout).Trim()
      stderr    = ([string]$stderr).Trim()
    }
  } finally {
    Remove-Item -LiteralPath $stdoutFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
  }
}

function New-Result {
  param(
    [bool]$Success,
    [int]$Attempts,
    [int]$ElapsedMs,
    [string]$TargetDir,
    [bool]$ReusedExisting,
    [int]$ExitCode,
    [string]$ErrorMessage,
    [string]$Stdout,
    [string]$Stderr
  )

  return [pscustomobject]@{
    success        = $Success
    attempts       = $Attempts
    elapsed_ms     = $ElapsedMs
    repo_url       = $RepoUrl
    target_dir     = $TargetDir
    reused_existing = $ReusedExisting
    git_dir_exists = (Test-Path (Join-Path $TargetDir ".git"))
    exit_code      = $ExitCode
    error_message  = $ErrorMessage
    stdout         = $Stdout
    stderr         = $Stderr
  }
}

$resolvedTargetDir = [System.IO.Path]::GetFullPath($TargetDir)
$parentDir = Split-Path -Parent $resolvedTargetDir
if (-not [string]::IsNullOrWhiteSpace($parentDir)) {
  New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
}

if ($ReuseExisting -and (Test-GitRepo -Path $resolvedTargetDir)) {
  $reuseResult = New-Result `
    -Success $true `
    -Attempts 0 `
    -ElapsedMs 0 `
    -TargetDir $resolvedTargetDir `
    -ReusedExisting $true `
    -ExitCode 0 `
    -ErrorMessage "" `
    -Stdout "" `
    -Stderr ""
  $reuseResult | ConvertTo-Json -Depth 6
  exit 0
}

$startAll = Get-Date
$lastError = ""
$lastStdout = ""
$lastStderr = ""
$lastExitCode = -1

for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
  if (Test-Path $resolvedTargetDir) {
    Remove-Item -LiteralPath $resolvedTargetDir -Recurse -Force -ErrorAction SilentlyContinue
  }

  $attemptResult = Invoke-GitCloneAttempt -RepoUrl $RepoUrl -TargetDir $resolvedTargetDir
  $lastExitCode = [int]$attemptResult.exit_code
  $lastStdout = [string]$attemptResult.stdout
  $lastStderr = [string]$attemptResult.stderr

  if ($lastExitCode -eq 0 -and (Test-GitRepo -Path $resolvedTargetDir)) {
    $elapsedMs = [int]((Get-Date) - $startAll).TotalMilliseconds
    $ok = New-Result `
      -Success $true `
      -Attempts $attempt `
      -ElapsedMs $elapsedMs `
      -TargetDir $resolvedTargetDir `
      -ReusedExisting $false `
      -ExitCode $lastExitCode `
      -ErrorMessage "" `
      -Stdout $lastStdout `
      -Stderr $lastStderr
    $ok | ConvertTo-Json -Depth 6
    exit 0
  }

  $lastError = if (-not [string]::IsNullOrWhiteSpace($lastStderr)) { $lastStderr } else { $lastStdout }

  if ($attempt -lt $MaxRetries) {
    $backoff = [Math]::Min($MaxBackoffSeconds, $InitialBackoffSeconds * [Math]::Pow(2, $attempt - 1))
    Start-Sleep -Seconds ([int]$backoff)
  }
}

$failElapsedMs = [int]((Get-Date) - $startAll).TotalMilliseconds
$failed = New-Result `
  -Success $false `
  -Attempts $MaxRetries `
  -ElapsedMs $failElapsedMs `
  -TargetDir $resolvedTargetDir `
  -ReusedExisting $false `
  -ExitCode $lastExitCode `
  -ErrorMessage $lastError `
  -Stdout $lastStdout `
  -Stderr $lastStderr

$failed | ConvertTo-Json -Depth 6
exit 1
