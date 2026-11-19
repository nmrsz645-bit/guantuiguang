@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0Update-Guantuiguang.exe" (
  echo Update-Guantuiguang.exe is missing. Extract the complete ZIP again.
  pause
  exit /b 6
)
"%~dp0Update-Guantuiguang.exe" --root "%~dp0."
exit /b %errorlevel%
