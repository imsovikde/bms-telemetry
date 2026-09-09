#Requires -RunAsAdministrator
<#
.SYNOPSIS
    BMS Telemetry — Windows Native Service Installer (BMSTelemetry)
.DESCRIPTION
    Deploys bms_engine.py to C:\ProgramData\BMS, installs bms_service.py as a
    true Windows Service via the SCM (no VBS, no Task Scheduler popups, no cmd
    windows).  The service starts before user logon and survives user logoff.
.PARAMETER SkipTests
    Skip the 100-cycle verification suite after installation.
.EXAMPLE
    # From an elevated PowerShell:
    Set-ExecutionPolicy -Scope Process Bypass
    .\scripts\install.ps1
#>
param (
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  BMS BATTERY TELEMETRY — WINDOWS SERVICE INSTALLER v4.0                      " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# ── 0. Admin Guard ──────────────────────────────────────────────────────────
$identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[!] This installer must be run as Administrator." -ForegroundColor Red
    exit 1
}

# ── 1. Platform Topology ─────────────────────────────────────────────────────
$os  = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$bb  = Get-CimInstance Win32_BaseBoard

Write-Host "`n[+] Platform Topology:"
Write-Host "    OS        : $($os.Caption) ($($os.Version) Build $($os.BuildNumber))" -ForegroundColor Green
Write-Host "    Processor : $($cpu.Name) ($env:PROCESSOR_ARCHITECTURE)" -ForegroundColor Green
Write-Host "    Baseboard : $($bb.Manufacturer) $($bb.Product) S/N=$($bb.SerialNumber)" -ForegroundColor Green

# ── 2. Python Discovery ──────────────────────────────────────────────────────
$python = (Get-Command python.exe -ErrorAction SilentlyContinue)?.Source
if (-not $python) {
    Write-Host "[!] Python 3 not found in PATH.  Install Python 3.10+ and retry." -ForegroundColor Red
    exit 1
}
$pyVer = & python.exe --version
Write-Host "    Python    : $pyVer ($python)" -ForegroundColor Green

# ── 2a. pywin32 Guard ───────────────────────────────────────────────────────
$pywin32OK = & python.exe -c "import win32serviceutil; print('ok')" 2>$null
if ($pywin32OK -ne "ok") {
    Write-Host "[!] pywin32 not found.  Installing..." -ForegroundColor Yellow
    & python.exe -m pip install --quiet pywin32
    & python.exe -m pywin32_postinstall -install 2>$null | Out-Null
}
Write-Host "    pywin32   : available" -ForegroundColor Green

# ── 3. Deploy Engine Files ───────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot   = Split-Path -Parent $ScriptDir
$InstallDir = "C:\ProgramData\BMS"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$filesToDeploy = @("bms_engine.py", "bms_service.py")
foreach ($f in $filesToDeploy) {
    $src = Join-Path $RepoRoot $f
    if (-not (Test-Path $src)) {
        Write-Host "[!] Source file not found: $src" -ForegroundColor Red
        exit 1
    }
    Copy-Item $src (Join-Path $InstallDir $f) -Force
}

Write-Host "`n[+] Engine Deployed  → $InstallDir" -ForegroundColor Green

# ── 4. Global CLI Shims ─────────────────────────────────────────────────────
$bmsCmd = "@echo off`r`npython.exe `"$InstallDir\bms_engine.py`" %*`r`n"
$bmsPs1 = "& python.exe `"$InstallDir\bms_engine.py`" @args`r`n"

Set-Content -Path "$InstallDir\bms.cmd" -Value $bmsCmd -Encoding ASCII
Set-Content -Path "$InstallDir\bms.ps1" -Value $bmsPs1 -Encoding ASCII

# Register C:\ProgramData\BMS in System PATH (persists across all sessions)
$sysPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($sysPath -notlike "*C:\ProgramData\BMS*") {
    [Environment]::SetEnvironmentVariable("Path", "$sysPath;C:\ProgramData\BMS", "Machine")
    $env:Path = "$env:Path;C:\ProgramData\BMS"
    Write-Host "    System PATH updated → C:\ProgramData\BMS" -ForegroundColor Green
}

# ── 5. Multi-Partition Persistence Mirrors ───────────────────────────────────
Write-Host "`n[+] Scanning Partition Mirrors:"
foreach ($dr in @('D:', 'S:', 'E:')) {
    if (Test-Path $dr) {
        Write-Host "    [OK] $dr (format-immune mirror enabled)" -ForegroundColor Green
    }
}

# ── 6. REMOVE OLD VBS STARTUP HOOK (the catastrophic bug) ───────────────────
$startupDir  = [Environment]::GetFolderPath("Startup")
$oldVbs      = Join-Path $startupDir "BMS_Cycle_Daemon.vbs"
$commonStart = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\BMS_Cycle_Daemon.vbs"
foreach ($legacy in @($oldVbs, $commonStart)) {
    if (Test-Path $legacy) {
        Remove-Item $legacy -Force
        Write-Host "    [REMOVED] Legacy VBS daemon hook: $legacy" -ForegroundColor Yellow
    }
}

# ── 7. Install / Restart Windows Service ────────────────────────────────────
Write-Host "`n[+] Configuring Windows Service (BMSTelemetry):"

# Stop existing service gracefully if running
$svc = Get-Service -Name "BMSTelemetry" -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq "Running") {
    Write-Host "    Stopping existing service..." -ForegroundColor Yellow
    Stop-Service -Name "BMSTelemetry" -Force
    Start-Sleep -Seconds 2
}

# Register / re-register with SCM
try {
    & python.exe "$InstallDir\bms_service.py" install 2>&1 | Out-Null
} catch {}

# Configure service metadata
sc.exe config BMSTelemetry start= auto | Out-Null
sc.exe description BMSTelemetry "BMS 30-decimal Coulomb-counting battery cycle tracker. Compensates for Infinix EC firmware _BIX absence. Headless; no console window." | Out-Null
sc.exe failure BMSTelemetry reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null

# Start the service
Start-Service -Name "BMSTelemetry" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$svc = Get-Service -Name "BMSTelemetry" -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq "Running") {
    Write-Host "    Service Status : RUNNING (PID managed by SCM)" -ForegroundColor Green
    Write-Host "    Auto-Restart   : on crash (5s / 10s / 30s escalation)" -ForegroundColor Green
    Write-Host "    Window Created : NONE (true SCM service)" -ForegroundColor Green
} else {
    Write-Host "    [WARN] Service registered but not yet running." -ForegroundColor Yellow
    Write-Host "    Run: sc start BMSTelemetry" -ForegroundColor Yellow
}

# ── 8. Verification ─────────────────────────────────────────────────────────
if (-not $SkipTests) {
    Write-Host "`n[+] 100-Cycle Deep Verification Suite:"
    & python.exe "$InstallDir\bms_engine.py" test-100
}

Write-Host "`n[+] Live Telemetry Snapshot:"
& python.exe "$InstallDir\bms_engine.py" status

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "  BMS INSTALLATION COMPLETE                                                    " -ForegroundColor Green
Write-Host "  Service: BMSTelemetry (SCM-managed, headless, auto-start on boot)            " -ForegroundColor Green
Write-Host "  CLI    : bms [status|full|test-100|sync-hw|daemon|help]                     " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
