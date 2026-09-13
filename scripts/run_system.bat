@echo off
color 0A
setlocal
cd /d "%~dp0"

rem ============================================================
rem  AIGC Society System - Launcher
rem    --updated      internal: used when relaunching after an update
rem    --skip-update  skip the update check
rem ============================================================
if /i "%~1"=="--updated" goto start_system
if /i "%~1"=="--skip-update" goto start_system

rem ---- locate the updater: project\tools, ..\tools, or next to this script ----
set "UPDATER="
if exist "%~dp0tools\offline_updater.exe" set "UPDATER=%~dp0tools\offline_updater.exe"
if not defined UPDATER if exist "%~dp0..\tools\offline_updater.exe" set "UPDATER=%~dp0..\tools\offline_updater.exe"
if not defined UPDATER if exist "%~dp0offline_updater.exe" set "UPDATER=%~dp0offline_updater.exe"
if not defined UPDATER goto start_system

rem ---- update check + prompt (the updater does all of it) ----
rem    --ask : no package -> 10, user skipped -> 11, updated -> 0, else failure
"%UPDATER%" --ask --restart "%~f0"
set "RC=%ERRORLEVEL%"

if "%RC%"=="0"  goto updated_ok
if "%RC%"=="10" goto start_system
if "%RC%"=="11" goto start_system

echo.
echo [Update not applied] Starting the current version...
timeout /t 3 >nul
goto start_system

:updated_ok
rem Updated: the updater already relaunched this script with the new version.
rem This file may have just been replaced, so cmd.exe cannot reliably keep
rem reading it -- exit here instead of falling through.
exit /b 0

:start_system
echo ==============================================
echo       AIGC Society System - One-Click Start
echo ==============================================
echo.

echo [1/3] Starting Backend Server...
start "AIGC Backend (Do Not Close)" cmd /k "cd backend && flask run --host=0.0.0.0 --port=5000"

echo [2/3] Starting Frontend Server...
start "AIGC Frontend (Do Not Close)" cmd /k "cd frontend && npm run dev:lan"

echo [3/3] Opening Browser...
timeout /t 5 >nul
start http://localhost:5173

echo.
echo ==============================================
echo System is running!
echo - Local:   http://localhost:5173
echo - LAN:     Check the Frontend window for IP
echo ==============================================
echo.
pause
