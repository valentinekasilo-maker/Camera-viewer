# ANDRO-Vision — Build EXE Script
# Run this from the project root:
#   powershell -ExecutionPolicy Bypass -File installer\build_exe.ps1

param(
    [switch]$Clean   # Pass -Clean to remove previous build artifacts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$InstallerDir = $PSScriptRoot
$DistDir = Join-Path $ProjectRoot "dist"
$BuildDir = Join-Path $ProjectRoot "build"
$ExeDist = Join-Path $DistDir "CameraApp.exe"
$ExeRoot = Join-Path $ProjectRoot "CameraApp.exe"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  ANDRO-Vision EXE Builder" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project root  : $ProjectRoot" -ForegroundColor DarkGray
Write-Host "  Installer dir : $InstallerDir" -ForegroundColor DarkGray
Write-Host "  Final EXE     : $ExeRoot" -ForegroundColor DarkGray
Write-Host ""

# --- Clean previous artifacts if requested ---
if ($Clean) {
    Write-Host "  [→] Cleaning previous build artifacts..." -ForegroundColor Cyan
    if (Test-Path $DistDir)  { Remove-Item -Recurse -Force $DistDir }
    if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
    if (Test-Path $ExeRoot)  { Remove-Item -Force $ExeRoot }
    Write-Host "  [✓] Cleaned" -ForegroundColor Green
    Write-Host ""
}

# --- Verify Python ---
Write-Host "  [→] Checking Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  [✓] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  [✗] Python not found in PATH" -ForegroundColor Red
    Write-Host "      Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# --- Install / upgrade PyInstaller ---
Write-Host ""
Write-Host "  [→] Installing/upgrading PyInstaller..." -ForegroundColor Cyan
python -m pip install --quiet --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [✗] Failed to install PyInstaller" -ForegroundColor Red
    exit 1
}

$piVersion = python -m PyInstaller --version 2>&1
Write-Host "  [✓] PyInstaller $piVersion ready" -ForegroundColor Green

# --- Build EXE ---
Write-Host ""
Write-Host "  [→] Building CameraApp.exe..." -ForegroundColor Cyan
Write-Host "      This may take 1-3 minutes on first build." -ForegroundColor DarkGray
Write-Host ""

$specFile = Join-Path $InstallerDir "launcher.spec"

python -m PyInstaller `
    --distpath "$DistDir" `
    --workpath "$BuildDir" `
    --noconfirm `
    "$specFile"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  [✗] Build FAILED. Check the output above for errors." -ForegroundColor Red
    exit 1
}

# --- Promote EXE to project root ---
if (-not (Test-Path $ExeDist)) {
    Write-Host "  [✗] EXE not found at: $ExeDist" -ForegroundColor Red
    exit 1
}

Copy-Item -Path $ExeDist -Destination $ExeRoot -Force
$exeSize = [math]::Round((Get-Item $ExeRoot).Length / 1MB, 1)

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "  BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  EXE Location : $ExeRoot" -ForegroundColor White
Write-Host "  EXE Size     : ${exeSize} MB" -ForegroundColor White
Write-Host ""
Write-Host "  Usage:" -ForegroundColor Yellow
Write-Host "    1. Double-click CameraApp.exe in the project root." -ForegroundColor DarkGray
Write-Host "    2. The launcher checks deps, starts backend and" -ForegroundColor DarkGray
Write-Host "       frontend, then opens the browser automatically." -ForegroundColor DarkGray
Write-Host ""
Write-Host "  NOTE: Python and Node.js must be installed on the" -ForegroundColor Yellow
Write-Host "  target PC. The EXE is NOT fully self-contained." -ForegroundColor Yellow
Write-Host ""
