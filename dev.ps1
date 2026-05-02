$ErrorActionPreference = "Stop"

Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$runDir = Join-Path $repoRoot ".run"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backendOut = Join-Path $runDir "backend.$stamp.out.log"
$backendErr = Join-Path $runDir "backend.$stamp.err.log"
$desktopOut = Join-Path $runDir "desktop.$stamp.out.log"
$desktopErr = Join-Path $runDir "desktop.$stamp.err.log"
"" | Set-Content -Path $backendOut -Encoding UTF8
"" | Set-Content -Path $backendErr -Encoding UTF8
"" | Set-Content -Path $desktopOut -Encoding UTF8
"" | Set-Content -Path $desktopErr -Encoding UTF8

@{
  backend_out = $backendOut
  backend_err = $backendErr
  desktop_out = $desktopOut
  desktop_err = $desktopErr
} | ConvertTo-Json | Set-Content -Path (Join-Path $runDir "last_logs.json") -Encoding UTF8

$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pythonCmd) {
  $pythonCmd = (Get-Command py -ErrorAction SilentlyContinue)
}
if (-not $pythonCmd) {
  throw "Python was not found on PATH in this shell."
}
$pythonExe = $pythonCmd.Source

# Avoid Windows port 8000 where unrelated or zombie listeners often collide with this app.
$BackendDevPort = 8010

function Write-PidFile([string]$name, [int]$procId) {
  Set-Content -Path (Join-Path $runDir "$name.pid") -Value $procId -Encoding ASCII
}

function Read-PidFile([string]$name) {
  $path = Join-Path $runDir "$name.pid"
  if (-not (Test-Path $path)) { return $null }
  try { return [int](Get-Content $path -Raw) } catch { return $null }
}

function Stop-IfRunning([string]$name) {
  $savedPid = Read-PidFile $name
  if ($null -eq $savedPid) { return }
  try {
    $p = Get-Process -Id $savedPid -ErrorAction Stop
    Stop-Process -Id $savedPid -Force
  } catch {
    # already stopped
  }
  Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $runDir "$name.pid")
}

function Stop-UvicornListenersOnPort([int]$Port) {
  <#
  Windows often leaves multiple LISTENING rows for the same port after repeated
  ``uvicorn --reload`` runs. Traffic then hits a stale process (404 on /health, WS 4420).
  Match ``app.main:app`` plus either ``uvicorn`` or ``python ... -m uvicorn``.
  #>
  $pids = New-Object "System.Collections.Generic.HashSet[int]"
  foreach ($line in (netstat -ano)) {
    if ($line -notmatch "LISTENING") { continue }
    if ($line -notmatch ":$Port\s") { continue }
    $parts = ($line -split "\s+") | Where-Object { $_ -ne "" }
    if ($parts.Count -lt 5) { continue }
    $last = $parts[$parts.Count - 1]
    if ($last -notmatch "^\d+$") { continue }
    [void]$pids.Add([int]$last)
  }
  foreach ($procId in $pids) {
    try {
      $p = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
      if (-not $p) { continue }
      $cl = [string]$p.CommandLine
      $isThisBackend = $cl -match "app\.main:app" -and (
        $cl -match "uvicorn(\.exe)?" -or $cl -match "-m\s+uvicorn"
      )
      if ($isThisBackend) {
        Write-Host "Stopping stale backend listener on port $Port pid=$procId" -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      }
    } catch { }
  }
}

Write-Host "Starting Trading212 Bot App (dev)..." -ForegroundColor Cyan

# Ensure Postgres is up (Docker Desktop must be running)
Write-Host "Ensuring Postgres is running..." -ForegroundColor Cyan
docker compose up -d | Out-Host

# Stop previous dev-run processes we started
Stop-IfRunning "backend"
Stop-IfRunning "desktop"
Stop-UvicornListenersOnPort 8000
Stop-UvicornListenersOnPort $BackendDevPort

# Backend (uvicorn reload) in a separate window
Write-Host "Starting backend (auto-reload) on port $BackendDevPort..." -ForegroundColor Cyan
$backendCmd = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-Command",
  "Set-Location '$repoRoot\backend'; uvicorn app.main:app --reload --reload-delay 1 --host 127.0.0.1 --port $BackendDevPort"
)
$backendProc = Start-Process -FilePath "powershell.exe" -ArgumentList $backendCmd -WindowStyle Normal -PassThru -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr
Write-PidFile "backend" $backendProc.Id

# Desktop in a separate window
Write-Host "Starting desktop..." -ForegroundColor Cyan
$desktopCmd = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-Command",
  "Set-Location '$repoRoot'; & '$pythonExe' -m desktop.app.main"
)
$desktopProc = Start-Process -FilePath "powershell.exe" -ArgumentList $desktopCmd -WindowStyle Normal -PassThru -RedirectStandardOutput $desktopOut -RedirectStandardError $desktopErr
Write-PidFile "desktop" $desktopProc.Id

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Backend:  http://127.0.0.1:$BackendDevPort" -ForegroundColor Green
Write-Host "WS:       ws://127.0.0.1:$BackendDevPort/ws/exec" -ForegroundColor Green
Write-Host "Stop:     .\\stop.ps1" -ForegroundColor Yellow
Write-Host "Logs:     .\\.run\\backend.*.log and .\\.run\\desktop.*.log" -ForegroundColor Yellow

