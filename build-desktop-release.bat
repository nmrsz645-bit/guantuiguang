@echo off
setlocal
cd /d "%~dp0"
call "%~dp0tools\run_py.bat" "%~dp0tools\build_desktop_release.py"
set "result=%errorlevel%"
pause
exit /b %result%
