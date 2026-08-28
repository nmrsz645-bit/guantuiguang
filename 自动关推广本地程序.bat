@echo off
cd /d "%~dp0"
call "%~dp0tools\run_py.bat" "%~dp0tools\local_oceanengine_app.py"
pause
