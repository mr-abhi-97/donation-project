@echo off
title Raise India Portal Launcher
cls
echo Freeing Ports...
powershell -Command "Stop-Process -Name python, node -Force -ErrorAction SilentlyContinue"

echo Starting FastAPI Backend...
start "Backend" cmd /k "cd /d E:\new try && .\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo Starting Next.js Frontend...
start "Frontend" cmd /k "cd /d E:\new try\frontend && npm run dev"

timeout /t 5 /nobreak >nul
echo Opening Browser...
start http://localhost:3000
