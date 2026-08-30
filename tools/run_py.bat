@echo off
setlocal
chcp 65001 >nul 2>nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if "%~1"=="" (
  echo ERROR: Missing python script path.
  exit /b 1
)

set "SCRIPT=%~1"
set "SCRIPT_ARGS="
:collect_args
shift
if "%~1"=="" goto args_collected
set SCRIPT_ARGS=%SCRIPT_ARGS% "%~1"
goto collect_args
:args_collected

call :find_python
if defined PYTHON_EXE goto run_script

call :install_python
call :find_python
if defined PYTHON_EXE goto run_script

echo ERROR: Python was not found and bundled installer did not finish correctly.
echo Please run first-install BAT again, or install Python 3.12 manually with Add Python to PATH.
exit /b 1

:run_script
"%PYTHON_EXE%" "%SCRIPT%" %SCRIPT_ARGS%
exit /b %errorlevel%

:find_python
set "PYTHON_EXE="
where py >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
  if defined PYTHON_EXE exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
  if defined PYTHON_EXE exit /b 0
)

for %%P in (
  "%LocalAppData%\Programs\Python\Python312\python.exe"
  "%LocalAppData%\Programs\Python\Python313\python.exe"
  "%ProgramFiles%\Python312\python.exe"
  "%ProgramFiles%\Python313\python.exe"
) do (
  if exist "%%~P" (
    set "PYTHON_EXE=%%~P"
    exit /b 0
  )
)
exit /b 1

:install_python
set "ROOT=%~dp0.."
set "INSTALLER=%ROOT%\installers\python-3.12.10-amd64.exe"
if exist "%INSTALLER%" (
  echo Python not found. Installing bundled Python 3.12...
  "%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1
  exit /b 0
)

where winget >nul 2>nul
if not errorlevel 1 (
  echo Bundled Python installer not found. Trying Windows Package Manager...
  winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
  exit /b %errorlevel%
)

echo ERROR: Python was not found. Add installers\python-3.12.10-amd64.exe or install Python 3.12 manually with Add Python to PATH.
exit /b 1
