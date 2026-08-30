@echo off
setlocal
cd /d "%~dp0"
py -3 -m unittest discover -s tests -v
set "result=%errorlevel%"
if not "%result%"=="0" (
  echo.
  echo Tests failed with exit code %result%.
) else (
  echo.
  echo All offline tests passed.
)
pause
exit /b %result%
