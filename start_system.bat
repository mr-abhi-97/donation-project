@echo off
setlocal enabledelayedexpansion
title Raise India Portal - Unified System Launcher

:: Determine absolute script root directory without trailing backslash
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

cls
echo ==============================================================================
echo              RAISE INDIA FOUNDATION - UNIFIED SYSTEM ORCHESTRATOR             
echo ==============================================================================
echo [INFO] Project Directory: "%ROOT_DIR%"
echo [INFO] Target Ports: FastAPI (8000) ^| Next.js (3000)
echo ==============================================================================
echo.

:: Step 1: Release stale port bindings using taskkill tree kill
echo [1/4] Releasing any stale process bindings on 8000 and 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    if %%a gtr 4 taskkill /F /T /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING 2^>nul') do (
    if %%a gtr 4 taskkill /F /T /PID %%a >nul 2>&1
)
echo [OK] Port verification complete.
echo.

:: Step 2: Launch FastAPI Backend in a dedicated titled window
echo [2/4] Spawning FastAPI Backend Server on port 8000...
start "Raise India - FastAPI Backend (Port 8000)" powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%\run_backend.ps1"

:: Step 3: Wait and poll backend health endpoint until verified online
echo [3/4] Awaiting Backend health verification at http://127.0.0.1:8000/api/health...
set /a ATTEMPTS=0
set /a MAX_ATTEMPTS=25

:HEALTH_POLL
set /a ATTEMPTS+=1
timeout /t 1 /nobreak >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$r = try { Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 1 -ErrorAction Stop } catch { $null }; if ($r -and $r.status -eq 'healthy') { exit 0 } else { exit 1 }"

if %ERRORLEVEL% EQU 0 (
    echo [OK] FastAPI Backend is ONLINE and HEALTHY ^(Verified in %ATTEMPTS%s^)!
    goto BOOT_FRONTEND
)

if %ATTEMPTS% GEQ %MAX_ATTEMPTS% (
    echo [ERROR] Backend did not respond within %MAX_ATTEMPTS% seconds.
    echo Please inspect the "Raise India - FastAPI Backend" terminal window for traceback details.
    pause
    exit /b 1
)

echo        Polling backend service (Attempt %ATTEMPTS%/%MAX_ATTEMPTS%)...
goto HEALTH_POLL

:BOOT_FRONTEND
echo.
:: Step 4: Launch Next.js Frontend
echo [4/4] Spawning Next.js Frontend on port 3000...
start "Raise India - Next.js Frontend (Port 3000)" cmd /k "cd /d "%ROOT_DIR%\frontend" && npm run dev"

:: Step 5: Await Frontend initialization and open browser
echo.
echo [INFO] Waiting for Next.js dev server on http://localhost:3000...
set /a FRONTEND_WAIT=0

:FRONTEND_POLL
set /a FRONTEND_WAIT+=1
timeout /t 1 /nobreak >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$c = try { Test-NetConnection -ComputerName 127.0.0.1 -Port 3000 -WarningAction SilentlyContinue } catch { $null }; if ($c -and $c.TcpTestSucceeded) { exit 0 } else { exit 1 }"

if %ERRORLEVEL% EQU 0 (
    echo [OK] Next.js Frontend is ONLINE!
    goto LAUNCH_SUCCESS
)

if %FRONTEND_WAIT% GEQ 15 (
    echo [NOTE] Next.js is still compiling, proceeding to open browser...
    goto LAUNCH_SUCCESS
)

goto FRONTEND_POLL

:LAUNCH_SUCCESS
echo.
echo ==============================================================================
echo                     SYSTEM BOOT COMPLETE - ALL SERVICES READY                 
echo ==============================================================================
echo  - Frontend Portal    : http://localhost:3000
echo  - Backend API Health : http://127.0.0.1:8000/api/health
echo  - Interactive Swagger: http://127.0.0.1:8000/docs
echo  - ReDoc Schema       : http://127.0.0.1:8000/redoc
echo ==============================================================================
echo.
echo Opening Portal in default browser...
start http://localhost:3000

echo [INFO] Both servers are running in separate dedicated terminal windows.
echo [INFO] To stop all servers, run stop_app.bat or close their terminal windows.
echo.
pause
