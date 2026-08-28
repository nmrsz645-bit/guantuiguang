@echo off
cd /d "%~dp0"
call "%~dp0tools\run_py.bat" "%~dp0tools\prepare_portable_oceanengine_only.py"
pause
