@echo off
chcp 65001 >nul
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\oceanengine-monitor.lnk"

if exist "%LNK%" (
  del /f /q "%LNK%"
  echo OK: startup shortcut removed.
) else (
  echo OK: startup shortcut was not found.
)

pause
