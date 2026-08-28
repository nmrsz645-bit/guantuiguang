@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$lock='data\\monitor.lock'; if(Test-Path $lock){$j=Get-Content $lock -Raw | ConvertFrom-Json; if($j.pid){try{Stop-Process -Id ([int]$j.pid) -Force -ErrorAction Stop; Write-Host ('Stopped monitor PID '+$j.pid)}catch{Write-Host ('Stop failed: '+$_.Exception.Message)}}; Remove-Item $lock -Force -ErrorAction SilentlyContinue}else{Write-Host 'No monitor lock file.'}"
pause
