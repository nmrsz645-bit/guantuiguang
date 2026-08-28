@echo off
cd /d "%~dp0.."
call "%~dp0..\tools\run_py.bat" "%~dp0monitor_oceanengine_units.py"
pause
