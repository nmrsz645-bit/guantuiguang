@echo off
cd /d "%~dp0.."
call "%~dp0..\tools\run_py.bat" "%~dp0import_account_texts.py"
pause
