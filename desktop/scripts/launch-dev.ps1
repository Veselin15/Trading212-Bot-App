<#
.SYNOPSIS
    Start the SwiftTrade desktop GUI for local development (no console window).

.DESCRIPTION
    End users run SwiftTrade.exe from the download page. This script is for developers only.
    Uses pyw/pythonw so only the Qt window appears — no extra terminal.
#>

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
Set-Location $repoRoot

$runDir = Join-Path $repoRoot ".run"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

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
  $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
  if (-not $pythonCmd) {
    throw "Python 3.12+ was not found."
  }
  $pythonExe = $pythonCmd.Source
}

function Resolve-DesktopLauncher {
  param(
    [string]$PythonExe,
    [string[]]$PythonModuleArgs
  )
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
  throw "Could not find pyw or pythonw. Build SwiftTrade.exe or install Python with the py launcher."
}

$launch = Resolve-DesktopLauncher -PythonExe $pythonExe -PythonModuleArgs $pythonModuleArgs
$proc = Start-Process `
  -FilePath $launch.Exe `
  -ArgumentList $launch.Args `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -PassThru

Set-Content -Path (Join-Path $runDir "desktop.pid") -Value $proc.Id -Encoding ASCII
Write-Host "SwiftTrade desktop started (pid $($proc.Id)). Close the window or run .\stop.ps1 to stop." -ForegroundColor Green
