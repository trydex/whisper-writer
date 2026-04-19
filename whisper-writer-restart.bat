@echo off
setlocal
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"

echo [ww-restart] Stopping any running WhisperWriter instance...
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'whisper-writer' }; if ($p) { $p | ForEach-Object { Write-Host ('Killing PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } } else { Write-Host 'No running WhisperWriter process found.' }"

echo [ww-restart] Waiting for release...
powershell -NoProfile -Command "Start-Sleep -Milliseconds 1500"

if not exist "%HERE%\whisper-writer-hidden.vbs" (
  echo [ww-restart] ERROR: %HERE%\whisper-writer-hidden.vbs not found.
  pause
  exit /b 1
)

echo [ww-restart] Launching WhisperWriter hidden...
wscript.exe "%HERE%\whisper-writer-hidden.vbs"

echo [ww-restart] Verifying (8s)...
powershell -NoProfile -Command "Start-Sleep -Seconds 8; $p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'whisper-writer' }; if ($p) { $p | ForEach-Object { Write-Host ('OK: WhisperWriter running, PID ' + $_.ProcessId) } } else { Write-Host 'WARNING: WhisperWriter process not detected.'; exit 1 }"

if errorlevel 1 (
  echo.
  echo [ww-restart] WhisperWriter did not start. Run whisper-writer.bat directly to see full error.
  pause
  exit /b 1
)

echo [ww-restart] Done.
endlocal
