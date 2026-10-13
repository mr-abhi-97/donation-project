@echo off
title Stop Raise India Portal Servers
echo Stopping background servers listening on port 8000 and port 3000...

powershell -Command "Get-NetTCPConnection -LocalPort 8000, 3000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo Done! Both servers have been stopped.
timeout /t 2 >nul
