@echo off
color 0A
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
