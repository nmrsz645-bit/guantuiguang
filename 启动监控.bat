@echo off
cd /d "%~dp0"
call "%~dp0tools\run_py.bat" "%~dp0tools\monitor_oceanengine_supervisor.py"
pause
