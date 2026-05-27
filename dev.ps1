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

$pythonExe = $null
$pythonModuleArgs = @()
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
  & py -3.12 -c "import sys" 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) {
    $pythonExe = $pyLauncher.Source
    $pythonModuleArgs = @("-3.12")
  }
}
if (-not $pythonExe) {
  $pythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
  if (-not $pythonCmd) {
    throw "Python 3.12+ was not found. Install from python.org or use the py launcher."
  }
  $pythonExe = $pythonCmd.Source
}

function Resolve-DesktopLauncher {
  param(
    [string]$PythonExe,
    [string[]]$PythonModuleArgs
  )
  # pyw / pythonw run GUI apps without attaching a console window.
  $pyw = Get-Command pyw -ErrorAction SilentlyContinue
  if ($pyw -and ($PythonModuleArgs -contains "-3.12")) {
    & pyw -3.12 -c "import sys" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
      return @{
        Exe  = $pyw.Source
        Args = @("-3.12", "-m", "desktop.app.main")
      }
    }
  }
  $pythonDir = Split-Path -Parent $PythonExe
  $pythonw = Join-Path $pythonDir "pythonw.exe"
  if (Test-Path $pythonw) {
    $args = @()
    if ($PythonModuleArgs.Count -gt 0 -and $PythonExe -notmatch "py(\.exe)?$") {
      $args += $PythonModuleArgs
    }
    $args += @("-m", "desktop.app.main")
    return @{ Exe = $pythonw; Args = $args }
  }
  throw @"
Could not find pyw or pythonw for a windowed desktop launch.
Install Python 3.12+ with the py launcher, or build SwiftTrade.exe for end-user testing:
  .\desktop\scripts\build-windows.ps1
"@
}

# Avoid Windows port 8000 where unrelated or zombie listeners often collide with this app.
$BackendDevPort = 8011

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

# Desktop GUI — pyw/pythonw only; no PowerShell host window for the app.
Write-Host "Starting desktop (GUI only, no console)..." -ForegroundColor Cyan
$desktopLaunch = Resolve-DesktopLauncher -PythonExe $pythonExe -PythonModuleArgs $pythonModuleArgs
$desktopProc = Start-Process `
  -FilePath $desktopLaunch.Exe `
  -ArgumentList $desktopLaunch.Args `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -PassThru
Write-PidFile "desktop" $desktopProc.Id

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Backend:  http://127.0.0.1:$BackendDevPort" -ForegroundColor Green
Write-Host "WS:       ws://127.0.0.1:$BackendDevPort/ws/exec" -ForegroundColor Green
Write-Host "Stop:     .\\stop.ps1" -ForegroundColor Yellow
Write-Host "Logs:     .\\.run\\backend.*.log and .\\.run\\desktop.*.log" -ForegroundColor Yellow

