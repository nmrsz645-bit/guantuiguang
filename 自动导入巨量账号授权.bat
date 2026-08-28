@echo off
cd /d "%~dp0"
set "SCRIPT=%~dp0import_account_texts.py"
if not exist "%SCRIPT%" (
  echo ERROR: Cannot find import_account_texts.py
  pause
  exit /b 1
)
call "%~dp0tools\run_py.bat" "%SCRIPT%"
pause
