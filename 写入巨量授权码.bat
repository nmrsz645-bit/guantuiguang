@echo off
cd /d "%~dp0"
set "SCRIPT="
for /r "%~dp0" %%F in (write_auth_code.py) do if not defined SCRIPT set "SCRIPT=%%~fF"
if "%SCRIPT%"=="" (
  echo ERROR: Cannot find write_auth_code.py
  pause
  exit /b 1
)
call "%~dp0tools\run_py.bat" "%SCRIPT%"
pause