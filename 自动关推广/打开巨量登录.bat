@echo off
cd /d "%~dp0.."
call "%~dp0..\tools\run_py.bat" "%~dp0open_main_account_logins.py"
pause
