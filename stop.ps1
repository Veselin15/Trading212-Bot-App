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

$BackendDevPort = 8011

function Stop-UvicornListenersOnPort([int]$Port) {
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
      $cl = if ($p) { [string]$p.CommandLine } else { "" }
      $isThisBackend = $cl -match "app\.main:app" -and (
        $cl -match "uvicorn(\.exe)?" -or $cl -match "-m\s+uvicorn"
      )
      if ($isThisBackend -or $cl -eq "") {
        Write-Host "Stopping listener on port $Port pid=$procId" -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        taskkill /F /PID $procId 2>$null | Out-Null
      }
    } catch {
      taskkill /F /PID $procId 2>$null | Out-Null
    }
  }
}

Write-Host "Stopping dev processes..." -ForegroundColor Cyan
Stop-IfRunning "desktop"
Stop-IfRunning "backend"
Stop-UvicornListenersOnPort 8000
Stop-UvicornListenersOnPort $BackendDevPort

Write-Host "Stopping Docker services (Postgres, Stripe CLI if running)..." -ForegroundColor Cyan
docker compose --profile stripe stop 2>$null | Out-Null
docker compose stop | Out-Null

Write-Host "Done." -ForegroundColor Green

