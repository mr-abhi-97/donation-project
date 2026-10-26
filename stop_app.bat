@echo off
title Stop Raise India Portal Servers
echo Stopping background servers listening on port 8000 and port 3000...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    if %%a gtr 4 taskkill /F /T /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING 2^>nul') do (
    if %%a gtr 4 taskkill /F /T /PID %%a >nul 2>&1
)

echo Done! Both servers have been stopped.
timeout /t 2 /nobreak >nul 2>&1
