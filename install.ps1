# Universal BMS Installer & System Autostart Setup (Windows)
$ErrorActionPreference = "Continue"

$targetDir = "C:\ProgramData\BMS"
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Installing BMS Telemetry & Hardware Engine ===" -ForegroundColor Cyan

# 1. Copy files
Copy-Item (Join-Path $scriptDir "bms_engine.py") (Join-Path $targetDir "bms_engine.py") -Force
Copy-Item (Join-Path $scriptDir "bms_ui.py") (Join-Path $targetDir "bms_ui.py") -Force
Copy-Item (Join-Path $scriptDir "bms_service.py") (Join-Path $targetDir "bms_service.py") -Force
Copy-Item (Join-Path $scriptDir "bms.cmd") (Join-Path $targetDir "bms.cmd") -Force
Write-Host "[+] Files provisioned to $targetDir" -ForegroundColor Green

# 2. Add C:\ProgramData\BMS to User PATH
$userPath = [Environment]::GetEnvironmentVariable("PATH", [EnvironmentVariableTarget]::User)
if ($userPath -notlike "*$targetDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$targetDir", [EnvironmentVariableTarget]::User)
    $env:PATH = "$env:PATH;$targetDir"
    Write-Host "[+] Added $targetDir to User PATH" -ForegroundColor Green
}

# 3. Configure Autostart upon Reboot (shell:startup hidden VBS launcher)
$startupDir = [System.Environment]::GetFolderPath('Startup')
$targetScript = Join-Path $targetDir "bms_ui.py"
$line1 = 'Set WshShell = CreateObject("WScript.Shell")'
$line2 = 'WshShell.Run "pythonw.exe """' + $targetScript + '""" --no-browser", 0, False'
$vbsLines = @($line1, $line2)
$vbsPath = Join-Path $startupDir "bms_ui_startup.vbs"
Set-Content -Path $vbsPath -Value $vbsLines -Encoding ASCII
Write-Host "[+] Configured Windows Boot Autostart in Startup directory" -ForegroundColor Green

# 4. Start background server if not already running
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $pythonw = "pythonw.exe"
}
Start-Process -FilePath $pythonw -ArgumentList $targetScript, "--no-browser" -WorkingDirectory $targetDir -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# 5. Launch dashboard in default browser
Write-Host "[+] Opening real-time dashboard at http://127.0.0.1:8989..." -ForegroundColor Cyan
Start-Process "http://127.0.0.1:8989"
Write-Host "[+] Installation complete! Server auto-starts on boot." -ForegroundColor Green
