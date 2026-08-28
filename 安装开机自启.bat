@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "%~dp0start_monitor.bat" (
  echo ERROR: Cannot find start_monitor.bat
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$startup=[Environment]::GetFolderPath('Startup'); $target=(Resolve-Path '.\start_monitor.bat').Path; $lnk=Join-Path $startup 'oceanengine-monitor.lnk'; $ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut($lnk); $s.TargetPath=$env:ComSpec; $s.Arguments='/c start \"\" /min \"' + $target + '\"'; $s.WorkingDirectory=(Get-Location).Path; $s.WindowStyle=7; $s.Description='Auto start OceanEngine close-promotion monitor'; $s.Save(); Write-Host ('OK: startup shortcut created: ' + $lnk)"

echo.
echo Done. It will auto start after this Windows user logs in.
pause
