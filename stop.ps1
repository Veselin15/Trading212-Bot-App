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

$BackendDevPort = 8010

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
      if (-not $p) { continue }
      $cl = [string]$p.CommandLine
      $isThisBackend = $cl -match "app\.main:app" -and (
        $cl -match "uvicorn(\.exe)?" -or $cl -match "-m\s+uvicorn"
      )
      if ($isThisBackend) {
        Write-Host "Stopping backend listener on port $Port pid=$procId" -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      }
    } catch { }
  }
}

Write-Host "Stopping dev processes..." -ForegroundColor Cyan
Stop-IfRunning "desktop"
Stop-IfRunning "backend"
Stop-UvicornListenersOnPort 8000
Stop-UvicornListenersOnPort $BackendDevPort

Write-Host "Stopping Postgres container..." -ForegroundColor Cyan
docker compose stop | Out-Null

Write-Host "Done." -ForegroundColor Green

