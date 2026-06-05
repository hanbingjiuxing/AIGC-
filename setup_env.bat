@echo off
setlocal enabledelayedexpansion

echo ======================================================
echo    AIGC Society Information System - Environment Setup
echo ======================================================
echo.

:: 1. Check Python
echo [+] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)
echo [OK] Python detected.

:: 2. Setup Backend Environment
echo.
echo [+] Setting up Backend (Python)...
cd backend

if not exist venv (
    echo [^] Creating virtual environment...
    python -m venv venv
)

echo [^] Installing backend dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [!] Error: Failed to install backend dependencies.
    pause
    exit /b 1
)
echo [OK] Backend setup complete.
cd ..

:: 3. Check Node.js/NPM
echo.
echo [+] Checking Node.js/NPM...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Error: Node.js/NPM is not installed or not in PATH.
    pause
    exit /b 1
)
echo [OK] Node.js/NPM detected.

:: 4. Setup Frontend Environment
echo.
echo [+] Setting up Frontend (Node.js)...
cd frontend

echo [^] Installing frontend dependencies...
call npm install
if %errorlevel% neq 0 (
    echo [!] Error: Failed to install frontend dependencies.
    pause
    exit /b 1
)
echo [OK] Frontend setup complete.
cd ..

echo.
echo ======================================================
echo    Setup Successful! You can now use run_system.bat
echo ======================================================
echo.
pause
