@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call "%~dp0..\启动监控.bat"
exit /b %errorlevel%
