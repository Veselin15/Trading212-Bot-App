$ErrorActionPreference = "Continue"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$runDir = Join-Path $repoRoot ".run"

function Read-PidFile([string]$name) {
  $path = Join-Path $runDir "$name.pid"
  if (-not (Test-Path $path)) { return $null }
  try { return [int](Get-Content $path -Raw) } catch { return $null }
}

function Stop-IfRunning([string]$name) {
  $savedPid = Read-PidFile $name
  if ($null -eq $savedPid) { return }
  try {
    Stop-Process -Id $savedPid -Force -ErrorAction Stop
  } catch { }
  Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $runDir "$name.pid")
}

Write-Host "Stopping dev processes..." -ForegroundColor Cyan
Stop-IfRunning "desktop"
Stop-IfRunning "backend"

Write-Host "Stopping Postgres container..." -ForegroundColor Cyan
docker compose stop | Out-Null

Write-Host "Done." -ForegroundColor Green

