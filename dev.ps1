$ErrorActionPreference = "Stop"

Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$runDir = Join-Path $repoRoot ".run"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

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

Write-Host "Starting Trading212 Bot App (dev)..." -ForegroundColor Cyan

# Ensure Postgres is up (Docker Desktop must be running)
Write-Host "Ensuring Postgres is running..." -ForegroundColor Cyan
docker compose up -d | Out-Host

# Stop previous dev-run processes we started
Stop-IfRunning "backend"
Stop-IfRunning "desktop"

# Backend (uvicorn reload) in a separate window
Write-Host "Starting backend (auto-reload)..." -ForegroundColor Cyan
$backendCmd = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-Command",
  "Set-Location '$repoRoot'; `$env:PYTHONPATH='backend'; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)
$backendProc = Start-Process -FilePath "powershell.exe" -ArgumentList $backendCmd -WindowStyle Normal -PassThru
Write-PidFile "backend" $backendProc.Id

# Desktop in a separate window
Write-Host "Starting desktop..." -ForegroundColor Cyan
$desktopCmd = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-Command",
  "Set-Location '$repoRoot'; python -m desktop.app.main"
)
$desktopProc = Start-Process -FilePath "powershell.exe" -ArgumentList $desktopCmd -WindowStyle Normal -PassThru
Write-PidFile "desktop" $desktopProc.Id

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "WS:       ws://127.0.0.1:8000/ws/exec" -ForegroundColor Green
Write-Host "Stop:     .\\stop.ps1" -ForegroundColor Yellow

