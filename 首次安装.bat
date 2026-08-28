@echo off
cd /d "%~dp0"
call "%~dp0tools\run_py.bat" "%~dp0tools\bootstrap_oceanengine_only.py"
pause
