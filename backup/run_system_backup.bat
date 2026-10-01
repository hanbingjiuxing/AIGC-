@echo off
color 0A
setlocal EnableExtensions

rem ============================================================
rem  AIGC Society System - Launcher
rem  *** BACKUP COPY of run_system.bat ***
rem  Use this one if the main script is missing or has been
rem  deleted. It is identical in behaviour, and it locates the
rem  project itself, so it also works when started from another
rem  folder. To restore the main script, copy this file to
rem  run_system.bat.
rem
rem    --updated      internal: used when relaunching after an update
rem    --skip-update  skip the update check
rem
rem  Backend and frontend start with whatever setup_env.bat
rem  prepared - backend\venv, then runtime\, then a system
rem  install - so nothing has to be on PATH beforehand.
rem
rem  If the system does NOT come up (no Python, missing
rem  dependencies, no npm, port never opens ...), this script
rem  opens the offline copy of the About page instead:
rem      fallback\about.html
rem  That page needs no server, no framework and no network,
rem  and it says who to contact when nothing else works.
rem ============================================================

rem ---- locate the project root, so a copy kept elsewhere still works ----
set "ROOT=%~dp0"
if exist "%ROOT%backend\app.py" goto root_ok
if exist "%ROOT%..\backend\app.py" for %%I in ("%ROOT%..") do set "ROOT=%%~fI\"
:root_ok
cd /d "%ROOT%"

if /i "%~1"=="--updated" goto start_system
if /i "%~1"=="--skip-update" goto start_system

rem ---- locate the updater: project\tools, ..\tools, or next to this script ----
set "UPDATER="
if exist "%ROOT%tools\offline_updater.exe" set "UPDATER=%ROOT%tools\offline_updater.exe"
if not defined UPDATER if exist "%ROOT%..\tools\offline_updater.exe" set "UPDATER=%ROOT%..\tools\offline_updater.exe"
if not defined UPDATER if exist "%ROOT%offline_updater.exe" set "UPDATER=%ROOT%offline_updater.exe"
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

rem ---- pick the Python that setup_env.bat prepared ----
set "PYEXE="
if exist "%ROOT%backend\venv\Scripts\python.exe" set "PYEXE=%ROOT%backend\venv\Scripts\python.exe"
if not defined PYEXE if exist "%ROOT%runtime\python\python.exe" set "PYEXE=%ROOT%runtime\python\python.exe"
if not defined PYEXE for /f "delims=" %%I in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%I"
if not defined PYEXE for /f "delims=" %%I in ('where python 2^>nul') do if not defined PYEXE call :probe_python "%%I"
if defined PYEXE if not exist "%PYEXE%" set "PYEXE="
if not defined PYEXE goto no_python

"%PYEXE%" -c "import flask" >nul 2>&1
if errorlevel 1 goto no_flask

rem ---- use the portable Node.js when the project carries one ----
if exist "%ROOT%runtime\node\npm.cmd" set "PATH=%ROOT%runtime\node;%PATH%"

set "UP_B=0"
set "UP_F=0"

rem ---- npm is what starts the frontend; without it that window
rem ---- would only print "'npm' is not recognized"
set "HAVE_NPM="
for /f "delims=" %%I in ('where npm.cmd 2^>nul') do if not defined HAVE_NPM set "HAVE_NPM=1"
if not defined HAVE_NPM for /f "delims=" %%I in ('where npm 2^>nul') do if not defined HAVE_NPM set "HAVE_NPM=1"

rem ---- if these ports already listen, an older instance is still around:
rem ---- the new server cannot bind and the check below would pass for the
rem ---- wrong reason, so say it out loud
call :port_up 5000
if not errorlevel 1 echo [WARN] Port 5000 is already in use - an older backend may still be running.
call :port_up 5173
if not errorlevel 1 echo [WARN] Port 5173 is already in use - an older frontend may still be running.

echo [1/3] Starting Backend Server...
start "AIGC Backend (Do Not Close)" /d "%ROOT%backend" cmd /k ""%PYEXE%" -m flask run --host=0.0.0.0 --port=5000"

if defined HAVE_NPM goto start_frontend
echo [2/3] Skipped: npm was not found, the frontend cannot start.
echo       Run setup_env.bat once - it installs Node.js and npm too.
goto wait_servers

:start_frontend
echo [2/3] Starting Frontend Server...
start "AIGC Frontend (Do Not Close)" /d "%ROOT%frontend" cmd /k "npm run dev:lan"

rem ---- do not send the browser to a page that is not up yet: wait for
rem ---- both ports (they start in parallel, so 60s is plenty), then open it
:wait_servers
echo [3/3] Waiting for the servers (up to 60 seconds)...
call :wait_ports 60

if not "%UP_B%"=="1" goto start_failed
if not "%UP_F%"=="1" goto start_failed

echo Opening http://localhost:5173 ...
start http://localhost:5173

echo.
echo ==============================================
echo System is running!
echo - Local:   http://localhost:5173
echo - LAN:     Check the Frontend window for IP
echo ==============================================
echo.
pause
exit /b 0

rem ============================================================
rem  Startup failed -> hand the user the offline About page
rem  (contacts live there; it needs no server at all)
rem ============================================================
:start_failed
echo.
echo ==============================================
echo   [ERR] The system did not start
echo ==============================================
if not "%UP_B%"=="1" echo   - Backend  (port 5000) is not running
if not "%UP_F%"=="1" echo   - Frontend (port 5173) is not running
echo.
echo   What to try first:
echo     1) close every AIGC window, run setup_env.bat once,
echo        then double-click this script again
echo     2) read the error in the backend / frontend window above
echo.
echo   Opening the offline "About this system" page now - it needs no
echo   server, and it lists who to contact:
call :open_fallback
echo.
pause
exit /b 1

rem ---- open the offline copy of the About page (fallback\about.html) ----
:open_fallback
set "FALLBACK=%ROOT%fallback\about.html"
if not exist "%FALLBACK%" (
  echo   [ERR] Offline page not found: %FALLBACK%
  echo         The project folder looks incomplete - re-unpack it and retry.
  exit /b 1
)
echo   %FALLBACK%
start "" "%FALLBACK%"
exit /b 0

rem ---- %1 = port; errorlevel 0 when something listens on it ----
:port_up
netstat -an | findstr /r /c:":%~1 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0

rem ---- %1 = seconds; polls 5000 + 5173 in parallel, sets UP_B / UP_F ----
:wait_ports
set /a "TRIES=%~1"
:wait_ports_loop
set "UP_B=0"
set "UP_F=0"
call :port_up 5000
if not errorlevel 1 set "UP_B=1"
call :port_up 5173
if not errorlevel 1 set "UP_F=1"
if "%UP_B%%UP_F%"=="11" exit /b 0
set /a TRIES-=1
if %TRIES% leq 0 exit /b 1
rem ping, not timeout: timeout fails when stdin is redirected
ping -n 2 127.0.0.1 >nul
goto wait_ports_loop

rem ---- store placeholder aliases must never be started: doing so
rem ---- would pop the Microsoft Store open instead of a console
:probe_python
set "CAND=%~1"
if not exist "%CAND%" exit /b 0
for %%D in ("%CAND%") do if /i "%%~dpD"=="%LOCALAPPDATA%\Microsoft\WindowsApps\" exit /b 0
set "PYEXE=%CAND%"
exit /b 0

:no_python
echo [ERR] No usable Python was found.
echo       Run setup_env.bat once - it installs everything this system
echo       needs, Python and Node.js included, without any preparation.
goto start_failed

:no_flask
echo [ERR] The backend dependencies are missing for this Python:
echo       %PYEXE%
echo       Run setup_env.bat once to install them.
goto start_failed
