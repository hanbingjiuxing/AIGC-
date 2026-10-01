@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================
rem  AIGC Society Information System - Environment Setup
rem  *** BACKUP COPY of setup_env.bat ***
rem  Use this one if the main script is missing or has been
rem  deleted. It is identical in behaviour, and it locates the
rem  project itself, so it also works when started from another
rem  folder. To restore the main script, copy this file to
rem  setup_env.bat.
rem
rem  Nothing has to be prepared in advance:
rem    Python  : reused when already present, otherwise installed
rem              for the current user - winget first, then the
rem              official python.org installer. No admin needed.
rem    Node.js : reused when already present, otherwise installed
rem              by winget, or unpacked from the official portable
rem              zip into runtime\node. No admin needed.
rem    Offline : drop a portable Python into runtime\python and it
rem              is used as-is, with no network access at all.
rem
rem  Re-running is safe - everything already in place is skipped.
rem ============================================================

title AIGC Society Information System - Environment Setup

rem ---- locate the project root, so this script also works when it ----
rem ---- is kept one folder away from the project (e.g. in scripts\) ----
set "ROOT=%~dp0"
if exist "%ROOT%backend\requirements.txt" goto root_ok
if exist "%ROOT%..\backend\requirements.txt" for %%I in ("%ROOT%..") do set "ROOT=%%~fI\"
:root_ok
if not exist "%ROOT%backend\requirements.txt" goto no_root

set "RUNTIME=%ROOT%runtime"
set "PYVER=3.12.10"
set "PYID=Python.Python.3.12"
set "NODEVER=20.18.1"
set "NODEID=OpenJS.NodeJS.LTS"
set "PYEXE="
set "VPY="
set "NODE_HOME="
set "NODEV="

echo ======================================================
echo    AIGC Society Information System - Environment Setup
echo ======================================================
echo.
echo   Project : %ROOT%
echo   Mode    : automatic - no Python or Node.js needed up front
echo.

rem ============================================================
rem  1/3  Python
rem ============================================================
echo [+] 1/3  Python
call :find_python
if defined PYEXE goto python_ready

echo      Not found on this machine - obtaining it automatically...
call :install_python
if defined PYEXE goto python_ready

goto python_failed

:python_ready
echo [OK] Python   %PYEXE%
"%PYEXE%" -c "import sys;print('     version',sys.version.split()[0])"
"%PYEXE%" -c "import sys;raise SystemExit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if errorlevel 1 echo [warn] Python 3.10 or newer is recommended for this project.

rem ============================================================
rem  2/3  Node.js
rem ============================================================
echo.
echo [+] 2/3  Node.js
call :find_node
if defined NODE_HOME set "PATH=%NODE_HOME%;%PATH%"
where node >nul 2>&1
if errorlevel 1 goto node_failed
where npm >nul 2>&1
if errorlevel 1 goto node_failed
for /f "delims=" %%V in ('node --version 2^>nul') do set "NODEV=%%V"
echo [OK] Node.js  %NODEV%

rem ============================================================
rem  3/3  Backend and frontend dependencies
rem ============================================================
echo.
echo [+] 3/3  Backend and frontend dependencies
pushd "%ROOT%backend"

rem A Python that can already import every backend dependency needs
rem no further work - this is what makes an offline runtime usable.
"%PYEXE%" -c "import flask,flask_cors,flask_sqlalchemy,jwt,werkzeug,requests" >nul 2>&1
if not errorlevel 1 goto deps_present

if exist "%ROOT%backend\venv\Scripts\python.exe" set "VPY=%ROOT%backend\venv\Scripts\python.exe"
if defined VPY goto have_venv

echo      Creating the virtual environment in backend\venv ...
"%PYEXE%" -m venv venv >nul 2>&1
if exist "%ROOT%backend\venv\Scripts\python.exe" set "VPY=%ROOT%backend\venv\Scripts\python.exe"
if defined VPY goto have_venv

echo [warn] This Python cannot create a virtual environment, so the
echo        dependencies go straight into it instead.
set "VPY=%PYEXE%"

:have_venv
echo      Installing backend dependencies ...
"%VPY%" -m pip install --upgrade pip --disable-pip-version-check >nul 2>&1
"%VPY%" -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 goto pip_failed
"%VPY%" -c "import flask,flask_cors,flask_sqlalchemy,jwt,werkzeug,requests" >nul 2>&1
if errorlevel 1 goto pip_failed
echo [OK] Backend ready  %VPY%
goto frontend

:deps_present
set "VPY=%PYEXE%"
echo [OK] Backend dependencies already present in this Python

:frontend
popd
pushd "%ROOT%frontend"

if not exist "node_modules\.bin\vite.cmd" goto npm_install
echo [OK] Frontend dependencies already installed
echo      delete frontend\node_modules to force a reinstall
goto done

:npm_install
echo      Running npm install ...
call npm install
if errorlevel 1 goto npm_failed
if not exist "node_modules\.bin\vite.cmd" goto npm_failed
echo [OK] Frontend dependencies ready

:done
popd
echo.
echo ======================================================
echo    Setup complete
echo ======================================================
echo.
echo   Python : %VPY%
echo   Node   : %NODEV%
echo.
echo   Start the system by running:  run_system.bat
echo   Keep run_system_backup.bat around as the spare launcher.
echo.
pause
exit /b 0

rem ============================================================
rem  Failure paths
rem ============================================================

:no_root
echo [ERR] Cannot find the project root.
echo       Expected backend\requirements.txt next to this script.
echo       Put the script back into the project folder and run it again.
pause
exit /b 1

:node_failed
echo [ERR] Node.js is still unavailable, so the frontend cannot be prepared.
echo       Install the LTS build from https://nodejs.org/en/download
echo       or unpack a portable Node.js build into runtime\node, then re-run
echo       this script.
pause
exit /b 1

:pip_failed
popd
echo [ERR] Failed to install the backend dependencies.
echo       Without internet access, put a portable Python that already has
echo       the packages installed into runtime\python and re-run this script.
pause
exit /b 1

:npm_failed
popd
echo [ERR] Failed to run npm install.
echo       Without internet access, copy frontend\node_modules from a machine
echo       that has it, then re-run this script.
pause
exit /b 1

rem ============================================================
rem  Subroutines
rem ============================================================

:find_python
rem -- a portable Python placed with the project wins: it is the one --
rem -- that is guaranteed to work without any network access        --
set "PYEXE="
if exist "%RUNTIME%\python\python.exe" set "PYEXE=%RUNTIME%\python\python.exe"
if defined PYEXE exit /b 0
rem -- the py launcher also works right after a fresh install, --
rem -- when this console still has a stale PATH                --
for /f "delims=" %%I in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%I"
if defined PYEXE if exist "!PYEXE!" exit /b 0
set "PYEXE="
rem -- python on PATH; the Microsoft Store placeholder alias is --
rem -- skipped so that probing never opens the Store app        --
for /f "delims=" %%I in ('where python 2^>nul') do if not defined PYEXE call :probe_python "%%I"
if defined PYEXE exit /b 0
rem -- standard per-user and machine-wide install locations --
for %%V in (314 313 312 311 310) do if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
if defined PYEXE exit /b 0
for %%V in (314 313 312 311 310) do if not defined PYEXE if exist "%ProgramFiles%\Python%%V\python.exe" set "PYEXE=%ProgramFiles%\Python%%V\python.exe"
exit /b 0

:probe_python
rem  %1 = candidate interpreter; entered from the where-python loop
set "CAND=%~1"
if not exist "%CAND%" exit /b 0
for %%D in ("%CAND%") do if /i "%%~dpD"=="%LOCALAPPDATA%\Microsoft\WindowsApps\" exit /b 0
set "PYEXE=%CAND%"
exit /b 0

:install_python
rem -- 1) winget, built into Windows 10 1809+ and Windows 11 --
where winget >nul 2>&1
if errorlevel 1 goto py_from_installer
echo      Using winget to install %PYID% for the current user...
winget install --id %PYID% -e --source winget --silent --accept-package-agreements --accept-source-agreements
call :find_python
if defined PYEXE exit /b 0

:py_from_installer
echo      Downloading the official Python %PYVER% installer...
set "PYSETUP=%TEMP%\aigc-python-%PYVER%-amd64.exe"
call :download "https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe" "%PYSETUP%"
if errorlevel 1 exit /b 1
echo      Installing Python %PYVER% for the current user...
"%PYSETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 Include_test=0 SimpleInstall=1 Shortcuts=0 AssociateFiles=0
call :find_python
exit /b 0

:python_failed
echo [ERR] Python could not be obtained.
echo       - check the internet connection and run this script again, or
echo       - install Python 3.10+ manually from https://www.python.org/downloads/
echo         and tick "Add python.exe to PATH", or
echo       - unpack a portable Python into runtime\python and re-run this script.
pause
exit /b 1

:find_node
rem -- a portable Node.js kept with the project comes first --
set "NODE_HOME="
if exist "%RUNTIME%\node\npm.cmd" set "NODE_HOME=%RUNTIME%\node"
if defined NODE_HOME exit /b 0
rem -- already usable in this console --
where node >nul 2>&1
if errorlevel 1 goto node_locate
where npm >nul 2>&1
if errorlevel 1 goto node_locate
exit /b 0

:node_locate
rem -- installed, but this console still has a stale PATH --
if exist "%ProgramFiles%\nodejs\npm.cmd" set "NODE_HOME=%ProgramFiles%\nodejs"
if defined NODE_HOME exit /b 0
if exist "%LOCALAPPDATA%\Programs\nodejs\npm.cmd" set "NODE_HOME=%LOCALAPPDATA%\Programs\nodejs"
if defined NODE_HOME exit /b 0
rem -- 1) winget --
where winget >nul 2>&1
if errorlevel 1 goto node_from_zip
echo      Using winget to install %NODEID%...
winget install --id %NODEID% -e --source winget --silent --accept-package-agreements --accept-source-agreements
if exist "%ProgramFiles%\nodejs\npm.cmd" set "NODE_HOME=%ProgramFiles%\nodejs"
if defined NODE_HOME exit /b 0
if exist "%LOCALAPPDATA%\Programs\nodejs\npm.cmd" set "NODE_HOME=%LOCALAPPDATA%\Programs\nodejs"
if defined NODE_HOME exit /b 0

:node_from_zip
rem -- 2) the official portable zip: no admin rights, no PATH edits --
echo      Downloading portable Node.js v%NODEVER% ...
set "NODEZIP=%TEMP%\aigc-node-v%NODEVER%-win-x64.zip"
call :download "https://nodejs.org/dist/v%NODEVER%/node-v%NODEVER%-win-x64.zip" "%NODEZIP%"
if errorlevel 1 exit /b 1
set "NODEUNPACK=%TEMP%\aigc-node-unpack"
if exist "%NODEUNPACK%" rd /s /q "%NODEUNPACK%"
call :unzip "%NODEZIP%" "%NODEUNPACK%"
if errorlevel 1 exit /b 1
if not exist "%NODEUNPACK%\node-v%NODEVER%-win-x64\node.exe" exit /b 1
if not exist "%RUNTIME%" mkdir "%RUNTIME%"
if exist "%RUNTIME%\node" rd /s /q "%RUNTIME%\node"
move "%NODEUNPACK%\node-v%NODEVER%-win-x64" "%RUNTIME%\node" >nul
if exist "%RUNTIME%\node\npm.cmd" set "NODE_HOME=%RUNTIME%\node"
exit /b 0

:download
rem  %1 = url, %2 = destination file
rem  -C - resumes a partly downloaded file, so a dropped connection on a
rem  slow link continues where it stopped instead of starting over.
where curl >nul 2>&1
if errorlevel 1 goto download_ps
curl.exe -L --fail -C - --retry 5 --retry-delay 3 --connect-timeout 20 -o "%~2" "%~1"
if not errorlevel 1 if exist "%~2" exit /b 0
echo      [warn] curl could not fetch the file, falling back to PowerShell...
:download_ps
call :powershell
"%PS%" -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri '%~1' -OutFile '%~2' -UseBasicParsing } catch { exit 1 }"
if errorlevel 1 exit /b 1
if not exist "%~2" exit /b 1
exit /b 0

:powershell
rem  the absolute path is used because PATH is not always complete
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell"
exit /b 0

:unzip
rem  %1 = archive, %2 = destination folder
if not exist "%~2" mkdir "%~2"
where tar >nul 2>&1
if errorlevel 1 goto unzip_ps
tar.exe -xf "%~1" -C "%~2"
if not errorlevel 1 exit /b 0
echo      [warn] tar could not unpack the archive, falling back to PowerShell...
:unzip_ps
call :powershell
"%PS%" -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; try { Expand-Archive -LiteralPath '%~1' -DestinationPath '%~2' -Force } catch { exit 1 }"
if errorlevel 1 exit /b 1
exit /b 0

