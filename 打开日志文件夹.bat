@echo off
cd /d "%~dp0"
set "LOGDIR="
for /d %%D in ("%~dp0*") do if exist "%%~fD\rizhi" set "LOGDIR=%%~fD\rizhi"
if "%LOGDIR%"=="" set "LOGDIR=%~dp0rizhi"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
start "" "%LOGDIR%"