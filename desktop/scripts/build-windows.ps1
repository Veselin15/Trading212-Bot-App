<#
.SYNOPSIS
    Build SwiftTrade.exe using PyInstaller.

.DESCRIPTION
    Installs PyInstaller, optionally bakes a default WebSocket URL for your hosted
    signal server, then runs SwiftTrade.spec from desktop/ to produce desktop/dist/SwiftTrade.exe.

    End users only need the EXE when you ship with -DefaultExecutorWsUrl pointing at your server.

.PARAMETER DefaultExecutorWsUrl
    WebSocket URL baked into the EXE (e.g. wss://signals.example.com/ws/exec).
    Use this for production so customers only download SwiftTrade.exe; your backend runs on your server.
    Omit for local dev: the EXE defaults to ws://127.0.0.1:8010/ws/exec.

.PARAMETER NoStopRunningApp
    If set, do not stop a running SwiftTrade.exe before overwrite. Build fails with WinError 5 if the EXE is still locked.

.EXAMPLE
    .\desktop\scripts\build-windows.ps1

.EXAMPLE
    .\desktop\scripts\build-windows.ps1 -DefaultExecutorWsUrl "wss://signals.example.com/ws/exec"
#>

[CmdletBinding()]
param(
    [string] $DefaultExecutorWsUrl = "",
    [switch] $NoStopRunningApp,

    # ── Code signing (the real fix for AV false positives) ──────────────
    # Provide ONE of:
    #   -SignCertFile  path\to\cert.pfx  -SignCertPassword "pfx-password"
    #   -SignSubject   "Your Company Name"   (uses a cert already in the user cert store)
    # Leave all unset to skip signing (dev builds).
    [string] $SignCertFile = "",
    [string] $SignCertPassword = "",
    [string] $SignSubject = "",
    [string] $TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"
# Avoid Set-StrictMode: it can trigger "variable cannot be retrieved" with Get-Command on some hosts.

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopDir = Split-Path -Parent $scriptDir
$repoRoot   = Split-Path -Parent $desktopDir
$specFile   = Join-Path $desktopDir "SwiftTrade.spec"
$distDir    = Join-Path $desktopDir "dist\SwiftTrade"
$distExe    = Join-Path $distDir "SwiftTrade.exe"
$releaseDir = Join-Path $desktopDir "release"
$zipOut     = Join-Path $releaseDir "SwiftTrade-windows.zip"
$defaultsJson = Join-Path $desktopDir "executor_defaults.json"

Write-Host ""
Write-Host "SwiftTrade Desktop - Windows build" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  Repo root   : $repoRoot"
Write-Host "  Desktop dir : $desktopDir"
Write-Host "  Spec file   : $specFile"
Write-Host "  Dist dir    : $distDir"
Write-Host "  Output      : $distExe"
Write-Host ""

# Optional: bake default WS URL for release (customers only use the EXE; you host the backend)
if ($DefaultExecutorWsUrl -and $DefaultExecutorWsUrl.Trim().Length -gt 0) {
    $u = $DefaultExecutorWsUrl.Trim()
    if ($u -notmatch '^(ws|wss)://') {
        throw "DefaultExecutorWsUrl must start with ws:// or wss:// (got: $u)"
    }
    $obj = @{ default_executor_ws_url = $u } | ConvertTo-Json -Compress
    Set-Content -Path $defaultsJson -Value $obj -Encoding UTF8
    Write-Host "Wrote $defaultsJson (baked default WS for this build)." -ForegroundColor Green
} else {
    if (Test-Path $defaultsJson) {
        Remove-Item -Force $defaultsJson
        Write-Host "Removed stale $defaultsJson (dev build uses localhost default)." -ForegroundColor Gray
    } else {
        Write-Host "No -DefaultExecutorWsUrl: EXE defaults to ws://127.0.0.1:8010/ws/exec" -ForegroundColor Gray
    }
}

# Locate Python 3.12+ (PATH ``python`` is often 3.8 on Windows)
$pythonExe = $null
$pythonArgs = @()
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    & py -3.12 -c "import sys" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $pythonExe = $pyLauncher.Source
        $pythonArgs = @("-3.12")
    }
}
if (-not $pythonExe) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $ver = & $pythonCmd.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver -ge "3.12") {
            $pythonExe = $pythonCmd.Source
        }
    }
}
if (-not $pythonExe) {
    throw "Python 3.12+ was not found. Install from python.org or use the py launcher (py -3.12)."
}
Write-Host "Python: $pythonExe $($pythonArgs -join ' ')" -ForegroundColor Gray

function Invoke-Python {
    param([string[]]$ExtraArgs)
    if ($pythonArgs.Count -gt 0) {
        & $pythonExe @pythonArgs @ExtraArgs
    } else {
        & $pythonExe @ExtraArgs
    }
}

Write-Host "Installing desktop requirements..." -ForegroundColor Cyan
Invoke-Python @("-m", "pip", "install", "-r", (Join-Path $desktopDir "requirements.txt"), "--quiet")
if (-not $?) { throw "pip install desktop/requirements.txt failed." }

Write-Host "Ensuring PyInstaller is installed..." -ForegroundColor Cyan
Invoke-Python @("-m", "pip", "install", "pyinstaller", "--quiet")
if (-not $?) { throw "pip install pyinstaller failed." }

# PyInstaller must overwrite desktop/dist/SwiftTrade.exe. Windows denies this if the EXE is running,
# held by Explorer preview, or scanned by AV.
function Ensure-DistExeWritable {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    if (-not $NoStopRunningApp) {
        $name = [System.IO.Path]::GetFileNameWithoutExtension($Path)
        Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "Stopping running process: $($_.ProcessName) (pid $($_.Id))" -ForegroundColor Yellow
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 600
    }
    try {
        Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
    } catch {
        # Rename aside so PyInstaller can write a fresh SwiftTrade.exe (same folder).
        $leaf = Split-Path -Leaf $Path
        $bakLeaf = "$leaf.prev-" + (Get-Date -Format "yyyyMMddHHmmss")
        try {
            Rename-Item -LiteralPath $Path -NewName $bakLeaf -Force -ErrorAction Stop
            Write-Host "Renamed locked exe to $bakLeaf (in dist folder); continuing build." -ForegroundColor Yellow
        } catch {
            throw @"
Cannot replace SwiftTrade.exe (Access denied). Fix one of:
  - Close SwiftTrade if it is running, then run this script again.
  - Close Windows Explorer windows showing desktop\dist (or disable preview pane).
  - Retry after antivirus finishes scanning the file.
Or run with -NoStopRunningApp only after closing SwiftTrade manually.
"@
        }
    }
}

Ensure-DistExeWritable -Path $distExe

# Authenticode code signing. A validly signed EXE is the only reliable way to stop
# antivirus false positives (Avast CyberCapture, Defender SmartScreen) for good.
function Find-SignTool {
    $cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    )
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $found = Get-ChildItem -Path $root -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "x64" } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

function Invoke-CodeSign {
    param([string]$Path)

    $wantSign = ($SignCertFile -and $SignCertFile.Trim()) -or ($SignSubject -and $SignSubject.Trim())
    if (-not $wantSign) {
        Write-Host "No signing cert provided (-SignCertFile / -SignSubject) - shipping UNSIGNED." -ForegroundColor Yellow
        Write-Host "  Unsigned builds may be flagged by Avast/Defender. See desktop/docs/ANTIVIRUS.md." -ForegroundColor Yellow
        return
    }

    $signtool = Find-SignTool
    if (-not $signtool) {
        throw "signtool.exe not found. Install the Windows 10/11 SDK (Signing Tools), then retry."
    }
    Write-Host "Signing with: $signtool" -ForegroundColor Cyan

    $args = @("sign", "/fd", "SHA256", "/tr", $TimestampUrl, "/td", "SHA256")
    if ($SignCertFile -and $SignCertFile.Trim()) {
        if (-not (Test-Path $SignCertFile)) { throw "SignCertFile not found: $SignCertFile" }
        $args += @("/f", $SignCertFile)
        if ($SignCertPassword -and $SignCertPassword.Trim()) { $args += @("/p", $SignCertPassword) }
    } else {
        # Use a cert already installed in the user's certificate store, matched by subject.
        $args += @("/n", $SignSubject)
    }
    $args += $Path

    & $signtool @args
    if ($LASTEXITCODE -ne 0) { throw "signtool failed (exit $LASTEXITCODE)." }

    # Verify the signature chains and is timestamped.
    & $signtool @("verify", "/pa", "/v", $Path) | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: signature verification reported issues for $Path" -ForegroundColor Yellow
    } else {
        Write-Host "Signature verified OK: $Path" -ForegroundColor Green
    }
}

Write-Host "Running PyInstaller..." -ForegroundColor Cyan
Set-Location $desktopDir
Invoke-Python @("-m", "PyInstaller", "SwiftTrade.spec", "--clean", "--noconfirm")
if (-not $?) { throw "PyInstaller build failed." }

if (Test-Path $distExe) {
    $sizeMB = [math]::Round((Get-Item $distExe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "Build complete!" -ForegroundColor Green
    Write-Host "  Output : $distExe" -ForegroundColor Green
    Write-Host "  Size   : $sizeMB MB" -ForegroundColor Green
    Write-Host ""

    # Sign the EXE (no-op if no cert provided). Must happen before zipping.
    Invoke-CodeSign -Path $distExe

    # Create a ZIP for distribution (more AV-friendly than shipping a raw .exe).
    New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
    if (Test-Path $zipOut) { Remove-Item -Force $zipOut }
    # Avast/Defender often locks the freshly-built EXE for a few seconds while it
    # scans it, which makes Compress-Archive fail. Retry until the file is free.
    $zipped = $false
    for ($attempt = 1; $attempt -le 6; $attempt++) {
        try {
            Compress-Archive -Path (Join-Path $distDir "*") -DestinationPath $zipOut -Force -ErrorAction Stop
            $zipped = $true
            break
        } catch {
            Write-Host "ZIP attempt $attempt failed (EXE likely locked by AV scan); retrying in 3s..." -ForegroundColor Yellow
            Start-Sleep -Seconds 3
        }
    }
    if (-not $zipped) {
        throw "Could not create $zipOut after several attempts (EXE stayed locked). Pause antivirus and retry."
    }

    Write-Host "Build output is one-folder. Ship the ZIP:" -ForegroundColor Green
    Write-Host "  $zipOut" -ForegroundColor Green
    if ($DefaultExecutorWsUrl) {
        Write-Host "This build uses your signal server URL by default." -ForegroundColor Green
    } else {
        Write-Host "For production: rebuild with -DefaultExecutorWsUrl 'wss://your-server/ws/exec'." -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "Build FAILED - $distExe not found." -ForegroundColor Red
    exit 1
}
