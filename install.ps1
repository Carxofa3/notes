# Windows Automated Installer for Notes Workstation
# Sets up virtual environment, installs all dependencies, and creates a Desktop shortcut.

$ErrorActionPreference = "Stop"
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Notes Workstation — University Knowledge Ecosystem      " -ForegroundColor Cyan
Write-Host "  Windows Installer                                      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Check Python
Write-Host "`n[1/4] Checking Python installation..." -ForegroundColor Yellow
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py -3"
} else {
    Write-Host "Error: Python 3 is required. Please install Python 3.10+ from python.org or Microsoft Store." -ForegroundColor Red
    exit 1
}
Write-Host "Found Python: $(& $PythonCmd --version)" -ForegroundColor Green

# 2. Setup Virtual Environment
Write-Host "`n[2/4] Setting up Python virtual environment..." -ForegroundColor Yellow
$VenvDir = Join-Path $ScriptDir ".venv"
if (-not (Test-Path $VenvDir)) {
    & $PythonCmd -m venv $VenvDir
    Write-Host "Created virtual environment at $VenvDir" -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

# 3. Install Python Dependencies
Write-Host "`n[3/4] Installing application dependencies..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPip install -r (Join-Path $ScriptDir "requirements.txt") --quiet
Write-Host "Dependencies successfully installed." -ForegroundColor Green

# 4. Create Desktop Shortcut
Write-Host "`n[4/4] Creating Desktop shortcut..." -ForegroundColor Yellow
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$ShortcutPath = Join-Path $DesktopPath "Notes Workstation.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $ScriptDir "run_desktop.bat"
$Shortcut.WorkingDirectory = $ScriptDir
$IconPath = Join-Path $ScriptDir "src-tauri\icons\icon.ico"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath, 0"
}
$Shortcut.Description = "Notes — University Knowledge & Fact-Checking Workstation"
$Shortcut.Save()
Write-Host "Desktop shortcut created: $ShortcutPath" -ForegroundColor Green

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  Installation Completed Successfully!                   " -ForegroundColor Green
Write-Host "  Launch the application from your Desktop shortcut or    " -ForegroundColor Cyan
Write-Host "  double-click 'run_desktop.bat'                         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
